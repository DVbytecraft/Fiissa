from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.companies.models import Company
from apps.users.models import User
from apps.orders.models import Order
from apps.notifications.models import AuditLog


class SuperAdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_platform_stats(self) -> dict:
        total_companies = await self.db.scalar(select(func.count(Company.id))) or 0
        active_companies = await self.db.scalar(
            select(func.count(Company.id)).where(Company.is_active)
        ) or 0
        total_users = await self.db.scalar(select(func.count(User.id))) or 0

        from datetime import datetime, timezone
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        orders_month = await self.db.scalar(
            select(func.count(Order.id)).where(Order.created_at >= month_start)
        ) or 0

        return {
            "total_companies": total_companies,
            "active_companies": active_companies,
            "total_users": total_users,
            "orders_this_month": orders_month,
            "revenue_xof": 0,
            "active_subscriptions": active_companies,
        }

    async def toggle_company_suspend(
        self,
        company_id: UUID,
        suspend: bool,
        reason: str | None,
        actor_id: UUID,
    ) -> Company:
        result = await self.db.execute(select(Company).where(Company.id == company_id))
        company = result.scalar_one_or_none()
        if not company:
            from core.exceptions import NotFoundError
            raise NotFoundError("Entreprise")

        company.is_active = not suspend

        log = AuditLog(
            company_id=company_id,
            user_id=actor_id,
            action="company.suspended" if suspend else "company.activated",
            resource_type="company",
            resource_id=company_id,
            new_data={"is_active": company.is_active, "reason": reason},
        )
        self.db.add(log)
        await self.db.flush()
        return company
