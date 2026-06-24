import re
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

SAFE_STORAGE_KEY_RE = re.compile(r'^[a-zA-Z0-9_\-./]{1,500}$')

from apps.notifications.models import SupportAttachment, SupportMessage, SupportTicket
from apps.notifications.service import AuditService
from core.database import get_db
from core.dependencies import get_current_user, get_tenant_context, require_permission
from core.exceptions import NotFoundError, TenantAccessDenied

router = APIRouter(prefix="/support", tags=["Support"])


class CreateTicketRequest(BaseModel):
    subject: str
    body: str
    order_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    priority: str = "medium"


class ReplyTicketRequest(BaseModel):
    body: str
    attachments: Optional[list[dict]] = None


class UpdateTicketRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to_id: Optional[UUID] = None


def _serialize_ticket(ticket: SupportTicket) -> dict:
    return {
        "id": str(ticket.id),
        "company_id": str(ticket.company_id) if ticket.company_id else None,
        "customer_id": str(ticket.customer_id) if ticket.customer_id else None,
        "assigned_to_id": str(ticket.assigned_to_id) if ticket.assigned_to_id else None,
        "order_id": str(ticket.order_id) if ticket.order_id else None,
        "subject": ticket.subject,
        "status": ticket.status,
        "priority": ticket.priority,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        "messages_count": len(ticket.messages) if ticket.messages else 0,
    }


@router.post("/tickets")
async def create_ticket(
    data: CreateTicketRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = SupportTicket(
        company_id=data.company_id,
        customer_id=current_user.id,
        order_id=data.order_id,
        subject=data.subject,
        priority=data.priority,
    )
    db.add(ticket)
    await db.flush()

    db.add(
        SupportMessage(
            ticket_id=ticket.id,
            sender_id=current_user.id,
            body=data.body,
        )
    )
    await AuditService(db).log(
        action="support.ticket.created",
        company_id=data.company_id,
        user_id=current_user.id,
        resource_type="support_ticket",
        resource_id=ticket.id,
        new_data={"subject": data.subject, "priority": data.priority},
    )
    return {"ticket_id": str(ticket.id), "status": ticket.status}


@router.get("/tickets")
async def get_tickets(
    mine: bool = Query(True),
    tenant=Depends(get_tenant_context),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(SupportTicket)
        .options(selectinload(SupportTicket.messages))
        .order_by(SupportTicket.created_at.desc())
    )

    if mine:
        stmt = stmt.where(SupportTicket.customer_id == current_user.id)
    else:
        _ = await require_permission("support.read")(current_user=current_user, db=db, x_company_id=str(tenant.company_id))
        stmt = stmt.where(SupportTicket.company_id == tenant.company_id)

    result = await db.execute(stmt)
    tickets = result.scalars().all()
    return {"items": [_serialize_ticket(ticket) for ticket in tickets]}


@router.get("/tickets/{ticket_id}")
async def get_ticket_detail(
    ticket_id: UUID,
    tenant=Depends(get_tenant_context),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SupportTicket)
        .options(
            selectinload(SupportTicket.messages).selectinload(SupportMessage.attachment_rows),
        )
        .where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise NotFoundError("Ticket")

    is_customer_owner = ticket.customer_id == current_user.id
    is_company_staff = ticket.company_id == tenant.company_id if tenant.company_id else False
    if not is_customer_owner and not is_company_staff:
        raise TenantAccessDenied()

    return {
        **_serialize_ticket(ticket),
        "messages": [
            {
                "id": str(message.id),
                "sender_id": str(message.sender_id),
                "body": message.body,
                "attachments": message.attachments,
                "attachment_rows": [
                    {
                        "id": str(attachment.id),
                        "file_name": attachment.file_name,
                        "storage_key": attachment.storage_key,
                        "content_type": attachment.content_type,
                        "size_bytes": attachment.size_bytes,
                    }
                    for attachment in message.attachment_rows
                ],
                "created_at": message.created_at.isoformat(),
            }
            for message in ticket.messages
        ],
    }


@router.post("/tickets/{ticket_id}/reply")
async def reply_ticket(
    ticket_id: UUID,
    data: ReplyTicketRequest,
    tenant=Depends(get_tenant_context),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise NotFoundError("Ticket")

    is_customer_owner = ticket.customer_id == current_user.id
    is_company_staff = ticket.company_id == tenant.company_id if tenant.company_id else False
    if not is_customer_owner and not is_company_staff:
        raise TenantAccessDenied()

    # Valider les storage_key pour prévenir les path traversal
    for attachment in data.attachments or []:
        key = attachment.get("storage_key", "")
        if not SAFE_STORAGE_KEY_RE.match(key):
            raise HTTPException(status_code=400, detail=f"storage_key invalide: {key}")
        if ".." in key:
            raise HTTPException(status_code=400, detail="Chemin invalide dans storage_key")

    message = SupportMessage(
        ticket_id=ticket.id,
        sender_id=current_user.id,
        body=data.body,
        attachments=data.attachments,
    )
    db.add(message)
    await db.flush()

    for attachment in data.attachments or []:
        db.add(
            SupportAttachment(
                message_id=message.id,
                file_name=attachment.get("file_name", "attachment"),
                storage_key=attachment.get("storage_key", ""),
                content_type=attachment.get("content_type"),
                size_bytes=attachment.get("size_bytes"),
            )
        )

    await AuditService(db).log(
        action="support.ticket.replied",
        company_id=ticket.company_id,
        user_id=current_user.id,
        resource_type="support_ticket",
        resource_id=ticket.id,
        new_data={"message_id": str(message.id)},
    )
    return {"message_id": str(message.id)}


@router.patch("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: UUID,
    data: UpdateTicketRequest,
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("support.update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise NotFoundError("Ticket")
    if ticket.company_id != tenant.company_id:
        raise TenantAccessDenied()

    old_data = {"status": ticket.status, "priority": ticket.priority, "assigned_to_id": str(ticket.assigned_to_id) if ticket.assigned_to_id else None}
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(ticket, key, value)
    if data.status == "resolved":
        ticket.resolved_at = datetime.now(timezone.utc)

    await AuditService(db).log(
        action="support.ticket.updated",
        company_id=ticket.company_id,
        user_id=current_user.id,
        resource_type="support_ticket",
        resource_id=ticket.id,
        old_data=old_data,
        new_data=update_data,
    )
    return {"id": str(ticket.id), "status": ticket.status}
