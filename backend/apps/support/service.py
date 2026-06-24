from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.support.models import SupportTicket, SupportMessage
from core.exceptions import NotFoundError


class SupportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_ticket(
        self,
        company_id: UUID,
        customer_id: UUID,
        subject: str,
        body: str,
        priority: str = "medium",
        category: str | None = None,
    ) -> SupportTicket:
        ticket = SupportTicket(
            company_id=company_id,
            customer_id=customer_id,
            subject=subject,
            priority=priority,
            category=category,
        )
        self.db.add(ticket)
        await self.db.flush()

        message = SupportMessage(
            ticket_id=ticket.id,
            sender_id=customer_id,
            body=body,
        )
        self.db.add(message)
        await self.db.flush()
        return ticket

    async def get_ticket(self, ticket_id: UUID, company_id: UUID) -> SupportTicket:
        result = await self.db.execute(
            select(SupportTicket)
            .options(selectinload(SupportTicket.messages))
            .where(SupportTicket.id == ticket_id, SupportTicket.company_id == company_id)
        )
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise NotFoundError("Ticket")
        return ticket

    async def add_message(
        self,
        ticket_id: UUID,
        sender_id: UUID,
        body: str,
        is_internal: bool = False,
    ) -> SupportMessage:
        msg = SupportMessage(
            ticket_id=ticket_id,
            sender_id=sender_id,
            body=body,
            is_internal=is_internal,
        )
        self.db.add(msg)
        await self.db.flush()
        return msg

    async def close_ticket(self, ticket_id: UUID) -> None:
        from datetime import datetime, timezone
        result = await self.db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
        ticket = result.scalar_one_or_none()
        if ticket:
            ticket.status = "resolved"
            ticket.resolved_at = datetime.now(timezone.utc)
