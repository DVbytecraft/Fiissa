"""
PaymentService — Paiement Mobile Money manuel V1.
Protections critiques :
1. transaction_ref unique par (company_id, operator) → contrainte DB
2. Idempotency check avant toute modification de statut
3. Un paiement confirmé ne peut JAMAIS être re-confirmé
4. Tout log est créé AVANT le commit final
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.notifications.service import AuditService, NotificationCenterService
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.users.models import User
from core.exceptions import (
    DuplicatePaymentRef,
    NotFoundError,
    PaymentAlreadyConfirmed,
    TenantAccessDenied,
    BadRequestError,
)
from core.permissions import Role


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------ #
    #  INITIALISER LE PAIEMENT                                             #
    # ------------------------------------------------------------------ #

    async def create_payment(
        self,
        order_id: UUID,
        company_id: UUID,
        customer_id: UUID,
        method: str,
        operator: str,
    ) -> Payment:
        """
        Crée un paiement en statut 'pending'.
        Retourne les instructions Mobile Money du magasin.
        """
        order = await self._get_order_or_fail(order_id, company_id)

        if order.customer_id != customer_id:
            raise TenantAccessDenied()

        if order.status not in ("pending", "awaiting_payment"):
            raise BadRequestError(
                f"Impossible de créer un paiement pour une commande en statut '{order.status}'"
            )

        # Vérifier s'il n'existe pas déjà un paiement pending pour cette commande
        result = await self.db.execute(
            select(Payment).where(
                Payment.order_id == order_id,
                Payment.status.in_(["pending", "pending_verification"]),
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing  # Idempotent : retourner le paiement existant

        from core.sequences import next_document_number
        payment_number = await next_document_number(self.db, company_id, "payment")

        payment = Payment(
            company_id=company_id,
            store_id=order.store_id,
            order_id=order_id,
            customer_id=customer_id,
            payment_number=payment_number,
            method=method,
            operator=operator,
            amount_xof=order.total_xof,
            status="pending",
        )
        self.db.add(payment)

        # Passer la commande en awaiting_payment
        order.status = "awaiting_payment"

        await self._log(
            action="payment.created",
            company_id=company_id,
            user_id=customer_id,
            resource_type="payment",
            resource_id=None,
            new_data={
                "order_id": str(order_id),
                "amount": order.total_xof,
                "method": method,
                "operator": operator,
            },
        )

        return payment

    # ------------------------------------------------------------------ #
    #  SOUMETTRE LA PREUVE DE PAIEMENT (client)                            #
    # ------------------------------------------------------------------ #

    async def submit_payment_proof(
        self,
        payment_id: UUID,
        company_id: UUID,
        customer_id: UUID,
        transaction_ref: str,
        sender_phone: str,
    ) -> Payment:
        """
        Le client soumet sa référence de transaction.
        Passe le paiement en 'pending_verification'.
        Vérifie l'unicité de la référence (anti-doublon).
        """
        payment = await self._get_payment_or_fail(payment_id, company_id)

        if payment.customer_id != customer_id:
            raise TenantAccessDenied()

        if payment.status not in ("pending",):
            if payment.status == "pending_verification":
                return payment  # Idempotent
            raise BadRequestError(
                f"Ce paiement est en statut '{payment.status}' et ne peut pas être modifié"
            )

        # Vérifier l'unicité de la référence pour cette entreprise + opérateur
        result = await self.db.execute(
            select(Payment).where(
                Payment.company_id == company_id,
                Payment.operator == payment.operator,
                Payment.transaction_ref == transaction_ref,
                Payment.id != payment_id,
                Payment.status != "failed",
            )
        )
        duplicate = result.scalar_one_or_none()
        if duplicate:
            raise DuplicatePaymentRef()

        payment.transaction_ref = transaction_ref.strip()
        payment.sender_phone = sender_phone.strip()
        payment.status = "pending_verification"
        payment.submitted_at = datetime.now(timezone.utc)

        # Commande en payment_submitted
        order = await self._get_order_or_fail(payment.order_id, company_id)
        order.status = "payment_submitted"

        await self._log(
            action="payment.proof_submitted",
            company_id=company_id,
            user_id=customer_id,
            resource_type="payment",
            resource_id=payment.id,
            new_data={
                "transaction_ref": transaction_ref,
                "sender_phone": sender_phone,
                "operator": payment.operator,
            },
        )

        # Notifier le marchand (async via Celery)
        from workers.tasks import notify_merchant_payment_received

        try:
            notify_merchant_payment_received.delay(str(payment.id))
        except Exception:
            pass

        return payment

    # ------------------------------------------------------------------ #
    #  CONFIRMER LE PAIEMENT (marchand)                                    #
    # ------------------------------------------------------------------ #

    async def confirm_payment(
        self,
        payment_id: UUID,
        company_id: UUID,
        confirmed_by: User,
    ) -> Payment:
        """
        Le marchand confirme la réception du paiement.
        - Vérifie que le paiement n'est pas déjà confirmé
        - Confirme le paiement + passe la commande en 'confirmed'
        - Déclenche la génération du reçu (async)
        """
        payment = await self._get_payment_or_fail(payment_id, company_id)

        if payment.status == "confirmed":
            raise PaymentAlreadyConfirmed()

        if payment.status != "pending_verification":
            raise BadRequestError(
                f"Ce paiement ne peut pas être confirmé (statut : '{payment.status}')"
            )

        now = datetime.now(timezone.utc)
        payment.status = "confirmed"
        payment.confirmed_by_id = confirmed_by.id
        payment.confirmed_at = now

        # Passer la commande en 'confirmed'
        order = await self._get_order_or_fail(payment.order_id, company_id)
        order.status = "confirmed"

        await self._log(
            action="payment.confirmed",
            company_id=company_id,
            user_id=confirmed_by.id,
            resource_type="payment",
            resource_id=payment.id,
            new_data={
                "payment_number": payment.payment_number,
                "transaction_ref": payment.transaction_ref,
                "amount": payment.amount_xof,
                "confirmed_by": str(confirmed_by.id),
            },
        )
        await NotificationCenterService(self.db).emit_event(
            event_key="payment.confirmed",
            company_id=company_id,
            resource_type="payment",
            resource_id=payment.id,
            payload={
                "payment_number": payment.payment_number,
                "order_number": order.order_number,
                "amount_xof": payment.amount_xof,
            },
            target_user_id=payment.customer_id,
        )

        # Flush pour garantir que le paiement est persisté avant le Celery task
        await self.db.flush()

        # Génération du reçu uniquement via Celery (idempotent, retry auto)
        # On ne génère PAS en synchrone ici pour éviter la race condition
        from workers.tasks import generate_receipt_pdf

        try:
            generate_receipt_pdf.delay(str(payment.id))
        except Exception:
            pass

        # Notifier le client
        from workers.tasks import notify_customer_payment_confirmed
        try:
            notify_customer_payment_confirmed.delay(str(payment.id))
        except Exception:
            pass

        return payment

    # ------------------------------------------------------------------ #
    #  REJETER LE PAIEMENT (marchand)                                      #
    # ------------------------------------------------------------------ #

    async def reject_payment(
        self,
        payment_id: UUID,
        company_id: UUID,
        rejected_by: User,
        reason: str,
    ) -> Payment:
        """
        Le marchand rejette le paiement.
        La raison est obligatoire.
        La commande retourne en awaiting_payment.
        """
        if not reason or not reason.strip():
            raise BadRequestError("La raison du rejet est obligatoire")

        payment = await self._get_payment_or_fail(payment_id, company_id)

        if payment.status not in ("pending_verification",):
            raise BadRequestError(
                f"Ce paiement ne peut pas être rejeté (statut : '{payment.status}')"
            )

        now = datetime.now(timezone.utc)
        payment.status = "failed"
        payment.rejected_by_id = rejected_by.id
        payment.rejected_at = now
        payment.rejection_reason = reason.strip()

        # La commande retourne en awaiting_payment pour permettre un nouveau paiement
        order = await self._get_order_or_fail(payment.order_id, company_id)
        order.status = "awaiting_payment"

        await self._log(
            action="payment.rejected",
            company_id=company_id,
            user_id=rejected_by.id,
            resource_type="payment",
            resource_id=payment.id,
            old_data={"status": "pending_verification"},
            new_data={
                "status": "failed",
                "reason": reason,
                "rejected_by": str(rejected_by.id),
            },
        )
        await NotificationCenterService(self.db).emit_event(
            event_key="payment.rejected",
            company_id=company_id,
            resource_type="payment",
            resource_id=payment.id,
            payload={
                "payment_number": payment.payment_number,
                "order_number": order.order_number,
                "reason": reason,
            },
            target_user_id=payment.customer_id,
        )

        # Notifier le client du rejet
        from workers.tasks import notify_customer_payment_rejected

        try:
            notify_customer_payment_rejected.delay(str(payment.id))
        except Exception:
            pass

        return payment

    # ------------------------------------------------------------------ #
    #  HELPERS                                                              #
    # ------------------------------------------------------------------ #

    async def _get_payment_or_fail(self, payment_id: UUID, company_id: UUID) -> Payment:
        result = await self.db.execute(
            select(Payment).where(
                Payment.id == payment_id,
                Payment.company_id == company_id,
            )
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Paiement")
        return payment

    async def _get_order_or_fail(self, order_id: UUID, company_id: UUID) -> Order:
        result = await self.db.execute(
            select(Order).where(Order.id == order_id, Order.company_id == company_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundError("Commande")
        return order

    async def _log(
        self,
        action: str,
        company_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        old_data: Optional[dict] = None,
        new_data: Optional[dict] = None,
    ) -> None:
        await AuditService(self.db).log(
            company_id=company_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_data=old_data,
            new_data=new_data,
        )
