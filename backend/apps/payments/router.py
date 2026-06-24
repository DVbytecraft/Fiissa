from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.payments.models import Payment
from apps.payments.service import PaymentService
from core.database import get_db
from core.dependencies import get_current_user, get_tenant_context, TenantContext, require_permission
from core.exceptions import NotFoundError, TenantAccessDenied
from pydantic import BaseModel, model_validator


class CreatePaymentRequest(BaseModel):
    order_id: UUID
    company_id: Optional[UUID] = None
    method: str = "mobile_money"
    operator: str


class SubmitProofRequest(BaseModel):
    transaction_ref: str
    sender_phone: str


class ConfirmPaymentRequest(BaseModel):
    confirmed: bool
    reason: Optional[str] = None  # obligatoire si confirmed=False

    @model_validator(mode="after")
    def validate_reason(self):
        if not self.confirmed and not (self.reason and self.reason.strip()):
            raise ValueError("La raison du rejet est obligatoire")
        return self


router = APIRouter(prefix="/payments", tags=["Paiements"])


@router.post("/")
async def create_payment(
    data: CreatePaymentRequest,
    current_user=Depends(require_permission("payments.create")),
    db: AsyncSession = Depends(get_db),
):
    """Initialise un paiement. Retourne les instructions Mobile Money."""
    company_id = data.company_id
    if company_id is None:
        from apps.orders.models import Order

        order_result = await db.execute(select(Order).where(Order.id == data.order_id))
        order = order_result.scalar_one_or_none()
        if not order:
            raise NotFoundError("Commande")
        company_id = order.company_id

    service = PaymentService(db)
    payment = await service.create_payment(
        order_id=data.order_id,
        company_id=company_id,
        customer_id=current_user.id,
        method=data.method,
        operator=data.operator,
    )

    # Récupérer les infos Mobile Money du magasin
    from apps.stores.models import Store
    store_result = await db.execute(select(Store).where(Store.id == payment.store_id))
    store = store_result.scalar_one()

    mm_info = store.mobile_money_info or {}

    return {
        "id": str(payment.id),
        "payment_id": str(payment.id),
        "payment_number": payment.payment_number,
        "amount_xof": payment.amount_xof,
        "status": "pending_proof" if payment.status == "pending" else payment.status,
        "operator": payment.operator,
        "instructions": {
            "operator": mm_info.get("operator", data.operator),
            "number": mm_info.get("number", ""),
            "account_name": mm_info.get("account_name", store.name),
            "reference_to_include": payment.payment_number,
            "message": f"Envoyez {payment.amount_xof:,} FCFA au {mm_info.get('number', '')} avec la référence {payment.payment_number}",
        },
    }


@router.post("/{payment_id}/submit-proof")
async def submit_payment_proof(
    payment_id: UUID,
    data: SubmitProofRequest,
    current_user=Depends(require_permission("payments.submit_proof")),
    db: AsyncSession = Depends(get_db),
):
    """Le client soumet sa référence de transaction."""
    # Récupérer le company_id depuis le paiement
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise NotFoundError("Paiement")

    if payment.customer_id != current_user.id:
        raise TenantAccessDenied()

    service = PaymentService(db)
    payment = await service.submit_payment_proof(
        payment_id=payment_id,
        company_id=payment.company_id,
        customer_id=current_user.id,
        transaction_ref=data.transaction_ref,
        sender_phone=data.sender_phone,
    )
    return {
        "id": str(payment.id),
        "payment_id": str(payment.id),
        "status": payment.status,
        "message": "Votre paiement est en cours de vérification par le magasin.",
    }


@router.post("/{payment_id}/confirm")
async def confirm_or_reject_payment(
    payment_id: UUID,
    data: ConfirmPaymentRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("payments.confirm")),
    db: AsyncSession = Depends(get_db),
):
    """
    Le marchand confirme ou rejette un paiement.
    La raison est obligatoire en cas de rejet.
    """
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise NotFoundError("Paiement")

    if str(payment.company_id) != str(ctx.company_id):
        raise TenantAccessDenied()

    service = PaymentService(db)

    if data.confirmed:
        payment = await service.confirm_payment(
            payment_id=payment_id,
            company_id=payment.company_id,
            confirmed_by=current_user,
        )
        return {
            "id": str(payment.id),
            "payment_id": str(payment.id),
            "status": payment.status,
            "message": "Paiement confirmé. Reçu en cours de génération.",
        }
    else:
        payment = await service.reject_payment(
            payment_id=payment_id,
            company_id=payment.company_id,
            rejected_by=current_user,
            reason=data.reason,
        )
        return {
            "id": str(payment.id),
            "payment_id": str(payment.id),
            "status": "rejected" if payment.status == "failed" else payment.status,
            "message": "Paiement rejeté. Le client a été notifié.",
        }


@router.get("/pending")
async def get_pending_payments(
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("payments.read")),
    db: AsyncSession = Depends(get_db),
):
    """Liste des paiements à vérifier pour le marchand."""
    result = await db.execute(
        select(Payment)
        .where(
            Payment.company_id == ctx.company_id,
            Payment.status == "pending_verification",
        )
        .order_by(Payment.submitted_at.asc())
    )
    payments = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "payment_number": p.payment_number,
            "amount_xof": p.amount_xof,
            "operator": p.operator,
            "transaction_ref": p.transaction_ref,
            "sender_phone": p.sender_phone,
            "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
            "order_id": str(p.order_id),
        }
        for p in payments
    ]
