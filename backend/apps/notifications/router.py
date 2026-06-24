from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.notifications.models import Notification, NotificationEvent, NotificationTemplate
from core.database import get_db
from core.dependencies import get_current_user, get_tenant_context, require_permission

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationTemplateUpsert(BaseModel):
    event_key: str
    channel: str = "in_app"
    subject_template: Optional[str] = None
    body_template: str
    is_active: bool = True


@router.get("/")
async def get_my_notifications(
    unread_only: bool = Query(False),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)
    result = await db.execute(stmt)
    notifs = result.scalars().all()
    return [
        {
            "id": str(notification.id),
            "type": notification.type,
            "title": notification.title,
            "body": notification.body,
            "data": notification.data,
            "channel": notification.channel,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
        }
        for notification in notifs
    ]


@router.get("/summary")
async def get_notification_summary(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
    )
    notifications = result.scalars().all()
    return {"unread_count": len(notifications)}


@router.post("/{notification_id}/read")
async def mark_one_read(
    notification_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == current_user.id)
        .values(is_read=True)
    )
    return {"message": "Notification marquee comme lue"}


@router.post("/mark-all-read")
async def mark_all_read(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)
        .values(is_read=True)
    )
    return {"message": "Toutes les notifications marquees comme lues"}


@router.get("/templates")
async def list_templates(
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("notifications.read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NotificationTemplate)
        .where(
            (NotificationTemplate.company_id == tenant.company_id)
            | (NotificationTemplate.company_id.is_(None))
        )
        .order_by(NotificationTemplate.event_key.asc())
    )
    templates = result.scalars().all()
    return {
        "items": [
            {
                "id": str(template.id),
                "company_id": str(template.company_id) if template.company_id else None,
                "event_key": template.event_key,
                "channel": template.channel,
                "subject_template": template.subject_template,
                "body_template": template.body_template,
                "is_active": template.is_active,
            }
            for template in templates
        ]
    }


@router.put("/templates")
async def upsert_template(
    data: NotificationTemplateUpsert,
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("notifications.send")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.company_id == tenant.company_id,
            NotificationTemplate.event_key == data.event_key,
            NotificationTemplate.channel == data.channel,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        template = NotificationTemplate(company_id=tenant.company_id, **data.model_dump())
        db.add(template)
        await db.flush()
    else:
        for key, value in data.model_dump().items():
            setattr(template, key, value)
    return {"id": str(template.id), "message": "Template notification enregistre"}


@router.get("/events")
async def list_notification_events(
    event_key: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("notifications.read")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(NotificationEvent)
        .where(NotificationEvent.company_id == tenant.company_id)
        .order_by(NotificationEvent.created_at.desc())
    )
    if event_key:
        stmt = stmt.where(NotificationEvent.event_key == event_key)
    if status:
        stmt = stmt.where(NotificationEvent.status == status)
    result = await db.execute(stmt.limit(100))
    events = result.scalars().all()
    return {
        "items": [
            {
                "id": str(event.id),
                "event_key": event.event_key,
                "resource_type": event.resource_type,
                "resource_id": str(event.resource_id) if event.resource_id else None,
                "status": event.status,
                "payload": event.payload,
                "error_message": event.error_message,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]
    }
