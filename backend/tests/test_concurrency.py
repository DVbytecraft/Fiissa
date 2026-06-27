from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.integrations.models import (
    ApiCredential,
    ApiIntegration,
    WebhookDelivery,
    WebhookEndpoint,
    WEBHOOK_EVENT_TYPES,
)
from core.database import get_db
from core.dependencies import get_tenant_context, require_permission
from core.exceptions import BadRequestError, NotFoundError, TenantAccessDenied
from core.secrets import encrypt_secret, mask_secret


def _validate_events(events: list[str]) -> None:
    """Valide que tous les événements sont supportés."""
    invalid = [e for e in events if e not in WEBHOOK_EVENT_TYPES]
    if invalid:
        raise BadRequestError(f"Événements non supportés : {', '.join(invalid)}. Événements valides : {', '.join(WEBHOOK_EVENT_TYPES)}")

router = APIRouter(prefix="/integrations", tags=["Integrations"])


class WebhookEndpointUpsert(BaseModel):
    name: str
    target_url: str
    events: list[str]
    secret: Optional[str] = None
    is_active: bool = True

class PaymentIntegrationUpsert(BaseModel):
    provider: str # "paygate" ou "fedapay"
    credentials: dict[str, str]


class WebhookEndpointUpdate(BaseModel):
    name: Optional[str] = None
    target_url: Optional[str] = None
    events: Optional[list[str]] = None
    secret: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/payment", summary="Récupérer la configuration de paiement")
async def get_payment_integration(
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("integrations.read")),
    db: AsyncSession = Depends(get_db),
):
    """Récupère la passerelle de paiement configurée par le marchand."""
    result = await db.execute(
        select(ApiIntegration)
        .where(
            ApiIntegration.company_id == tenant.company_id,
            ApiIntegration.integration_type == "payment",
            ApiIntegration.is_active,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        return None

    creds_result = await db.execute(
        select(ApiCredential).where(ApiCredential.integration_id == integration.id)
    )
    creds = creds_result.scalars().all()

    return {
        "provider": integration.name,
        "credentials": [{"key_name": c.key_name, "masked": c.masked_preview} for c in creds],
    }

@router.post("/payment", summary="Configurer la passerelle de paiement")
async def upsert_payment_integration(
    data: PaymentIntegrationUpsert,
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("integrations.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Permet au marchand de lier son compte PayGate ou FedaPay."""


    # Désactiver les anciennes intégrations de paiement
    result = await db.execute(
        select(ApiIntegration)
        .where(
            ApiIntegration.company_id == tenant.company_id,
            ApiIntegration.integration_type == "payment",
        )
    )
    existing_integs = result.scalars().all()
    for integ in existing_integs:
        integ.is_active = False
        # Désactiver les credentials associés
        await db.execute(
            update(ApiCredential)
            .where(ApiCredential.integration_id == integ.id)
            .values(is_active=False)
        )

    # Créer la nouvelle intégration
    integration = ApiIntegration(
        company_id=tenant.company_id,
        integration_type="payment",
        name=data.provider,
        endpoint_url=f"https://{data.provider}.com",
        is_active=True,
    )
    db.add(integration)
    await db.flush()

    for key, value in data.credentials.items():
        if not value:
            continue
        cred = ApiCredential(
            integration_id=integration.id,
            key_name=key,
            masked_preview=mask_secret(value),
            is_active=True,
        )
        db.add(cred)

    await db.commit()
    return {"message": "Configuration de paiement mise à jour avec succès"}

@router.get("/webhooks")
async def list_webhooks(
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("webhooks.read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebhookEndpoint)
        .where(WebhookEndpoint.company_id == tenant.company_id)
        .order_by(WebhookEndpoint.created_at.desc())
    )
    endpoints = result.scalars().all()
    return {
        "items": [
            {
                "id": str(endpoint.id),
                "name": endpoint.name,
                "target_url": endpoint.target_url,
                "events": endpoint.events,
                "is_active": endpoint.is_active,
                "last_success_at": endpoint.last_success_at.isoformat() if endpoint.last_success_at else None,
            }
            for endpoint in endpoints
        ]
    }


@router.post("/webhooks")
async def create_webhook(
    data: WebhookEndpointUpsert,
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("webhooks.create")),
    db: AsyncSession = Depends(get_db),
):
    _validate_events(data.events)

    endpoint = WebhookEndpoint(
        company_id=tenant.company_id,
        name=data.name,
        target_url=data.target_url,
        events=data.events,
        is_active=data.is_active,
        secret_encrypted=encrypt_secret(data.secret) if data.secret else None,
    )
    db.add(endpoint)
    await db.flush()
    return {"id": str(endpoint.id), "message": "Webhook cree"}


@router.patch("/webhooks/{endpoint_id}")
async def update_webhook(
    endpoint_id: UUID,
    data: WebhookEndpointUpdate,
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("webhooks.update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WebhookEndpoint).where(WebhookEndpoint.id == endpoint_id))
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise NotFoundError("Webhook")
    if endpoint.company_id != tenant.company_id:
        raise TenantAccessDenied()

    update_data = data.model_dump(exclude_none=True)
    if "events" in update_data:
        _validate_events(update_data["events"])
    for field, value in update_data.items():
        if field == "secret":
            endpoint.secret_encrypted = encrypt_secret(value)
        else:
            setattr(endpoint, field, value)
    return {"id": str(endpoint.id), "message": "Webhook mis a jour"}


@router.delete("/webhooks/{endpoint_id}")
async def delete_webhook(
    endpoint_id: UUID,
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("webhooks.update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WebhookEndpoint).where(WebhookEndpoint.id == endpoint_id))
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise NotFoundError("Webhook")
    if endpoint.company_id != tenant.company_id:
        raise TenantAccessDenied()

    await db.delete(endpoint)
    return {"id": str(endpoint_id), "message": "Webhook supprime"}


@router.get("/webhooks/deliveries")
async def list_webhook_deliveries(
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("webhooks.read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.company_id == tenant.company_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(100)
    )
    deliveries = result.scalars().all()
    return {
        "items": [
            {
                "id": str(delivery.id),
                "endpoint_id": str(delivery.endpoint_id),
                "event_type": delivery.event_type,
                "status": delivery.status,
                "response_status": delivery.response_status,
                "retry_count": delivery.retry_count,
                "created_at": delivery.created_at.isoformat(),
            }
            for delivery in deliveries
        ]
    }


@router.post("/webhooks/{endpoint_id}/test")
async def send_test_webhook(
    endpoint_id: UUID,
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("webhooks.update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WebhookEndpoint).where(WebhookEndpoint.id == endpoint_id))
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise NotFoundError("Webhook")
    if endpoint.company_id != tenant.company_id:
        raise TenantAccessDenied()

    delivery = WebhookDelivery(
        endpoint_id=endpoint.id,
        company_id=tenant.company_id,
        event_type="order.created",
        payload={"test": True, "event": "order.created"},
        status="pending",
    )
    db.add(delivery)
    await db.commit()  # Commit avant l'appel HTTP pour libérer la connexion DB

    # Délégue la livraison à Celery pour ne pas bloquer la connexion DB
    from workers.tasks import deliver_webhook
    try:
        deliver_webhook.delay(str(delivery.id))
        return {"message": "Test webhook envoyé", "delivery_id": str(delivery.id)}
    except Exception:
        return {"message": "Test webhook planifié (Celery indisponible)", "delivery_id": str(delivery.id)}
