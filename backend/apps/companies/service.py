from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.companies.models import (
    Company,
    Plan,
    Subscription,
    SubscriptionInvoice,
    SubscriptionRenewal,
)
from core.exceptions import NotFoundError


class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_subscription(self, company_id: UUID) -> Subscription:
        result = await self.db.execute(
            select(Subscription).where(Subscription.company_id == company_id)
        )
        subscription = result.scalar_one_or_none()
        if subscription:
            return subscription

        now = datetime.now(timezone.utc)
        subscription = Subscription(
            company_id=company_id,
            plan="starter",
            status="trial",
            trial_ends_at=now + timedelta(days=14),
            current_period_start=now,
            current_period_end=now + timedelta(days=14),
        )
        self.db.add(subscription)
        await self.db.flush()
        return subscription

    async def change_plan(self, company_id: UUID, plan_code: str) -> Subscription:
        subscription = await self.get_or_create_subscription(company_id)
        result = await self.db.execute(
            select(Plan).where(Plan.code == plan_code, Plan.is_active)
        )
        plan = result.scalar_one_or_none()
        if not plan:
            raise NotFoundError("Plan")

        now = datetime.now(timezone.utc)
        days = 365 if plan.billing_cycle == "yearly" else 30
        previous_period_end = subscription.current_period_end

        subscription.plan = plan.code
        subscription.status = "active"
        subscription.billing_cycle = plan.billing_cycle
        subscription.amount_xof = plan.amount_xof
        subscription.commission_rate = plan.commission_rate
        subscription.current_period_start = now
        subscription.current_period_end = now + timedelta(days=days)

        renewal = SubscriptionRenewal(
            company_id=company_id,
            subscription_id=subscription.id,
            previous_period_end=previous_period_end,
            new_period_end=subscription.current_period_end,
            status="processed",
            processed_at=now,
        )
        self.db.add(renewal)

        invoice_number = await self._generate_invoice_number(company_id)
        invoice = SubscriptionInvoice(
            company_id=company_id,
            subscription_id=subscription.id,
            invoice_number=invoice_number,
            status="issued",
            amount_xof=plan.amount_xof,
            tax_xof=0,
            total_xof=plan.amount_xof,
            due_at=now + timedelta(days=7),
            invoice_metadata={"plan_code": plan.code, "billing_cycle": plan.billing_cycle},
        )
        self.db.add(invoice)
        return subscription

    async def mark_invoice_paid(self, company_id: UUID, invoice_id: UUID) -> SubscriptionInvoice:
        result = await self.db.execute(
            select(SubscriptionInvoice).where(
                SubscriptionInvoice.id == invoice_id,
                SubscriptionInvoice.company_id == company_id,
            )
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise NotFoundError("Facture")

        invoice.status = "paid"
        invoice.paid_at = datetime.now(timezone.utc)

        # Reactivate subscription if suspended due to unpaid invoice
        result2 = await self.db.execute(
            select(Subscription).where(Subscription.company_id == company_id)
        )
        sub = result2.scalar_one_or_none()
        if sub and sub.status == "suspended":
            now = datetime.now(timezone.utc)
            days = 365 if sub.billing_cycle == "yearly" else 30
            sub.status = "active"
            sub.current_period_start = now
            sub.current_period_end = now + timedelta(days=days)

            # Reactivate company
            result3 = await self.db.execute(
                select(Company).where(Company.id == company_id)
            )
            company = result3.scalar_one_or_none()
            if company:
                company.is_suspended = False
                company.is_active = True

        return invoice

    async def cancel_subscription(self, company_id: UUID) -> Subscription:
        sub = await self.get_or_create_subscription(company_id)
        sub.status = "cancelled"
        sub.cancelled_at = datetime.now(timezone.utc)
        return sub

    @staticmethod
    async def suspend_expired_subscriptions(db: AsyncSession) -> int:
        """
        Appelé par Celery quotidiennement.
        Suspend toutes les entreprises dont la période de facturation est expirée.
        Retourne le nombre d'entreprises suspendues.
        """
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Subscription).where(
                Subscription.status.in_(["trial", "active"]),
                Subscription.current_period_end < now,
            )
        )
        expired = result.scalars().all()
        count = 0
        for sub in expired:
            sub.status = "suspended"

            company_result = await db.execute(
                select(Company).where(Company.id == sub.company_id)
            )
            company = company_result.scalar_one_or_none()
            if company and not company.is_suspended:
                company.is_suspended = True
                count += 1

        if expired:
            await db.commit()
        return count

    async def _generate_invoice_number(self, company_id: UUID) -> str:
        """Génère un numéro de facture unique via atomic upsert (sans race condition)."""
        from core.sequences import next_document_number
        return await next_document_number(self.db, company_id, "invoice")
