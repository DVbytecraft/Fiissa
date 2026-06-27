from uuid import UUID
from typing import Optional
import hashlib
import hmac

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.payments.gateway import PaymentGatewayService
from apps.payments.models import Payment
from apps.payments.service import PaymentService
from core.config import settings
from core.database import get_db
from core.dependencies import get_current_user, get_tenant_context, TenantContext, require_permission
from core.exceptions import BadRequestError, NotFoundError, TenantAccessDenied
from pydantic import BaseModel, model_validator


class CreatePaymentRequest(BaseModel):
    order_id: UUID
    company_id: Optional[UUID] = None
    method: str = "mobile_money"
    operator: str

class InitiateGatewayPaymentRequest(BaseModel):
    payment_id: UUID
    customer_phone: str
    provider: str = "paygate"  # "paygate" ou "fedapay"


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


class RefundPaymentRequest(BaseModel):
    reason: str
    refund_amount_xof: Optional[int] = None  # None = remboursement total

    @model_validator(mode="after")
    def validate_reason(self):
        if not (self.reason and self.reason.strip()):
            raise ValueError("La raison du rejet est obligatoire")
        return self


router = APIRouter(prefix="/payments", tags=["Paiements"])


@router.post("/webhooks/fedapay", include_in_schema=False)
async def fedapay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook entrant FedaPay.
    Valide la signature HMAC et confirme le paiement automatiquement.
    """
    if not settings.FEDAPAY_WEBHOOK_SECRET:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"error": "Webhook non configuré"})

    body = await request.body()
    signature_header = request.headers.get("x-fedapay-signature", "")

    # Validation de la signature HMAC
    expected_signature = hmac.new(
        settings.FEDAPAY_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature_header, expected_signature):
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error": "Signature invalide"})

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Payload invalide"})

    event_type = payload.get("event")
    transaction = payload.get("data", {})
    transaction_ref = transaction.get("reference")
    payment_id_str = transaction.get("metadata", {}).get("payment_id")
    company_id_str = transaction.get("metadata", {}).get("company_id")

    if not payment_id_str or not company_id_str:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Métadonnées manquantes"})

    try:
        payment_id = UUID(payment_id_str)
        company_id = UUID(company_id_str)
    except ValueError:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "IDs invalides"})

    # ── Paiement approuvé ─────────────────────────────────────────────────
    if event_type == "transaction.approved":
        service = PaymentService(db)
        try:
            payment = await service.confirm_payment_from_provider(
                payment_id=payment_id,
                company_id=company_id,
                transaction_ref=transaction_ref,
                provider="fedapay",
            )
            await db.commit()

            from workers.tasks import generate_receipt_pdf
            try:
                generate_receipt_pdf.delay(str(payment.id))
            except Exception:
                pass

            return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "confirmed", "payment_id": str(payment.id)})
        except (BadRequestError, NotFoundError) as e:
            await db.rollback()
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": str(e.detail)})
        except Exception:
            await db.rollback()
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": "Erreur interne"})

    # ── Paiement refusé / échoué ───────────────────────────────────────────
    if event_type in ("transaction.declined", "transaction.failed", "transaction.cancelled"):
        try:
            from apps.orders.models import Order as OrderModel
            result = await db.execute(
                select(Payment).where(
                    Payment.id == payment_id,
                    Payment.company_id == company_id,
                )
            )
            payment = result.scalar_one_or_none()
            if payment and payment.status not in ("confirmed", "failed"):
                payment.status = "failed"
                payment.rejection_reason = f"FedaPay: {event_type}"
                order_result = await db.execute(
                    select(OrderModel).where(OrderModel.id == payment.order_id)
                )
                order = order_result.scalar_one_or_none()
                if order and order.status not in ("cancelled", "refunded", "delivered"):
                    order.status = "awaiting_payment"
                await db.commit()
        except Exception:
            await db.rollback()
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "failure_handled", "event": event_type})

    # ── Autre événement ignoré ─────────────────────────────────────────────
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ignored"})


@router.post("/gateway/initiate", summary="Initier un paiement via passerelle (PayGate)")
async def initiate_gateway_payment(
    data: InitiateGatewayPaymentRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initialise une transaction sur la passerelle de paiement du marchand (PayGate).
    Déclenche le pop-up USSD sur le téléphone du client.
    """
    result = await db.execute(select(Payment).where(Payment.id == data.payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise NotFoundError("Paiement")
    if payment.customer_id != current_user.id:
        raise TenantAccessDenied()

    gateway_service = PaymentGatewayService(db)
    
    try:
        result_data = await gateway_service.initiate_payment(
            payment=payment,
            customer_phone=data.customer_phone,
            provider=data.provider,
        )
        await db.commit()
        return {
            "status": "success",
            "provider": data.provider,
            # PayGate renvoie "tx_reference", FedaPay renvoie "reference"
            "tx_reference": result_data.get("tx_reference") or result_data.get("reference"),
            # FedaPay uniquement — URL de redirection vers la page de paiement
            "payment_url": result_data.get("payment_url"),
            "message": result_data.get("message"),
        }
    except Exception as e:
        await db.rollback()
        if isinstance(e, BadRequestError):
            raise e
        raise BadRequestError("Erreur lors de l'initialisation du paiement.")

@router.post("/webhooks/paygate", include_in_schema=False)
async def paygate_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook entrant PayGate Togo.
    - Valide la signature HMAC si PAYGATE_WEBHOOK_SECRET est configuré.
    - Vérifie que le paiement a bien été initié via PayGate (gateway_response.provider).
    - Confirme le paiement si status=0 (succès).
    """
    body = await request.body()

    # Validation HMAC si le secret est configuré
    if settings.PAYGATE_WEBHOOK_SECRET:
        signature_header = request.headers.get("x-paygate-signature", "")
        expected_signature = hmac.new(
            settings.PAYGATE_WEBHOOK_SECRET.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature_header, expected_signature):
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error": "Signature invalide"})

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Payload invalide"})

    # PayGate renvoie status=0 pour succès
    status_code_pg = payload.get("status")
    tx_reference = payload.get("tx_reference")

    if status_code_pg != 0 or not tx_reference:
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ignored"})

    # Chercher le paiement par la référence PayGate
    result = await db.execute(
        select(Payment).where(Payment.transaction_ref == tx_reference)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ignored"})

    # Vérifier que ce paiement a bien été initié via PayGate (anti-forgery)
    gw = payment.gateway_response or {}
    if gw.get("provider") != "paygate":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Ce paiement n'est pas un paiement PayGate"},
        )

    # Cross-check : l'identifier PayGate doit correspondre
    webhook_identifier = payload.get("identifier")
    stored_identifier = gw.get("identifier")
    if webhook_identifier and stored_identifier and webhook_identifier != stored_identifier:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Identifiant de transaction incohérent"},
        )

    service = PaymentService(db)
    try:
        payment = await service.confirm_payment_from_provider(
            payment_id=payment.id,
            company_id=payment.company_id,
            transaction_ref=tx_reference,
            provider="paygate",
        )
        await db.commit()

        from workers.tasks import generate_receipt_pdf
        try:
            generate_receipt_pdf.delay(str(payment.id))
        except Exception:
            pass

        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "confirmed"})
    except Exception:
        await db.rollback()
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": "Erreur confirmation"})


@router.get("/store-options/{store_id}", summary="Options de paiement disponibles pour un magasin")
async def get_store_payment_options(
    store_id: UUID,
    _=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne les passerelles de paiement activées par le marchand pour ce magasin.
    Permet au frontend client d'afficher les bons boutons (PayGate, FedaPay, Manuel).
    """
    from apps.stores.models import Store
    from apps.integrations.models import ApiIntegration

    # 1. Récupérer le magasin et son company_id
    store_result = await db.execute(select(Store).where(Store.id == store_id))
    store = store_result.scalar_one_or_none()
    if not store:
        raise NotFoundError("Magasin")

    options = {
        "manual": True, # Le manuel est toujours proposé par défaut
        "paygate": False,
        "fedapay": False,
    }

    # 2. Vérifier si le marchand a des infos Mobile Money manuelles
    if store.mobile_money_info and store.mobile_money_info.get("number"):
        options["manual"] = True

    # 3. Vérifier les intégrations de paiement actives
    integrations_result = await db.execute(
        select(ApiIntegration).where(
            ApiIntegration.company_id == store.company_id,
            ApiIntegration.integration_type == "payment",
            ApiIntegration.is_active,
        )
    )
    integrations = integrations_result.scalars().all()

    for integ in integrations:
        if integ.name == "paygate":
            options["paygate"] = True
        elif integ.name == "fedapay":
            options["fedapay"] = True

    return options


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
    await db.commit()  # Forcer le commit avant Celery

    # Notifier le marchand (async via Celery)
    from workers.tasks import notify_merchant_payment_received
    try:
        notify_merchant_payment_received.delay(str(payment.id))
    except Exception:
        pass

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
        await db.commit()  # Forcer le commit avant Celery

        # Déclencher la génération du reçu PDF via Celery
        # generate_receipt_pdf s'occupera d'appeler notify_customer_payment_confirmed à la fin
        from workers.tasks import generate_receipt_pdf
        try:
            generate_receipt_pdf.delay(str(payment.id))
        except Exception:
            pass

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
        await db.commit()  # Forcer le commit avant Celery

        # Notifier le client du rejet
        from workers.tasks import notify_customer_payment_rejected
        try:
            notify_customer_payment_rejected.delay(str(payment.id))
        except Exception:
            pass

        return {
            "id": str(payment.id),
            "payment_id": str(payment.id),
            "status": "rejected" if payment.status == "failed" else payment.status,
            "message": "Paiement rejeté. Le client a été notifié.",
        }


@router.post("/{payment_id}/refund", summary="Rembourser un paiement confirmé")
async def refund_payment(
    payment_id: UUID,
    data: RefundPaymentRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("payments.refund")),
    db: AsyncSession = Depends(get_db),
):
    """
    Rembourse un paiement en statut 'confirmed'.
    Passe le paiement et la commande en statut 'refunded'.
    Le retour d'argent réel doit être effectué manuellement via Mobile Money.
    Remboursement partiel supporté via `refund_amount_xof`.
    """
    service = PaymentService(db)
    payment = await service.refund_payment(
        payment_id=payment_id,
        company_id=ctx.company_id,
        refunded_by=current_user,
        reason=data.reason,
        refund_amount_xof=data.refund_amount_xof,
    )
    await db.commit()
    return {
        "id": str(payment.id),
        "payment_number": payment.payment_number,
        "status": payment.status,
        "refund_amount_xof": payment.refund_amount_xof,
        "refunded_at": payment.refunded_at.isoformat() if payment.refunded_at else None,
        "message": "Remboursement enregistré. Effectuez le virement Mobile Money manuellement.",
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
