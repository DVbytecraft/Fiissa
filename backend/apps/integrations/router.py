from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.integrations.models import WebhookDelivery, WebhookEndpoint
from apps.integrations.service import WebhookService
from core.database import get_db
from core.dependencies import get_tenant_context, require_permission
from core.exceptions import NotFoundError, TenantAccessDenied
from core.secrets import encrypt_secret

router = APIRouter(prefix="/integrations", tags=["Integrations"])


class WebhookEndpointUpsert(BaseModel):
    name: str
    target_url: str
    events: list[str]
    secret: Optional[str] = None
    is_active: bool = True


class WebhookEndpointUpdate(BaseModel):
    name: Optional[str] = None
    target_url: Optional[str] = None
    events: Optional[list[str]] = None
    secret: Optional[str] = None
    is_active: Optional[bool] = None


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
async def test_webhook(
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
    await db.flush()
    await WebhookService.deliver_delivery(delivery.id, db)
    return {"message": "Webhook teste"}
