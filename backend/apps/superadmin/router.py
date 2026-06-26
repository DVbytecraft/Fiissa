import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

logger = logging.getLogger(__name__)
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.companies.models import Company, Plan, Subscription
from apps.notifications.models import AuditLog
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.stores.models import Store
from apps.users.models import User, UserCompanyRole
from core.database import get_db
from core.dependencies import require_permission
from core.exceptions import NotFoundError
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

router = APIRouter(prefix="/superadmin", tags=["Super Admin"])


class SuspendCompanyRequest(BaseModel):
    reason: str


class SuspendToggleRequest(BaseModel):
    suspend: bool
    reason: Optional[str] = None


class CreateStaffRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    role: str
    company_id: Optional[UUID] = None


class CreateCompanyWithOwnerRequest(BaseModel):
    company_name: str
    company_type: str
    country: str = "SN"
    currency: str = "XOF"
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    owner_email: str
    owner_password: str
    owner_first_name: str
    owner_last_name: str
    owner_phone: Optional[str] = None


class CreatePlanRequest(BaseModel):
    code: str
    name: str
    billing_cycle: str = "monthly"
    amount_xof: int = 0
    commission_rate: float = 0
    features: Optional[dict] = None


@router.get("/companies")
async def list_all_companies(
    search: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    current_user=Depends(require_permission("*")),
    db: AsyncSession = Depends(get_db),
):
    """Super-admin : liste toutes les entreprises."""
    last_30_days = datetime.now(timezone.utc) - timedelta(days=30)

    stores_count_sq = (
        select(func.count(Store.id))
        .where(Store.company_id == Company.id)
        .correlate(Company)
        .scalar_subquery()
    )
    orders_count_30d_sq = (
        select(func.count(Order.id))
        .where(
            and_(
                Order.company_id == Company.id,
                Order.created_at >= last_30_days,
            )
        )
        .correlate(Company)
        .scalar_subquery()
    )
    revenue_30d_sq = (
        select(func.coalesce(func.sum(Payment.amount_xof), 0))
        .where(
            and_(
                Payment.company_id == Company.id,
                Payment.status == "confirmed",
                Payment.created_at >= last_30_days,
            )
        )
        .correlate(Company)
        .scalar_subquery()
    )

    stmt = (
        select(
            Company,
            Subscription,
            stores_count_sq.label("stores_count"),
            orders_count_30d_sq.label("orders_count_30d"),
            revenue_30d_sq.label("revenue_xof_30d"),
        )
        .outerjoin(Subscription, Company.id == Subscription.company_id)
        .order_by(Company.created_at.desc())
    )
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Company.name.ilike(pattern),
                Company.slug.ilike(pattern),
                Company.contact_email.ilike(pattern),
                Company.contact_phone.ilike(pattern),
            )
        )
    if status:
        stmt = stmt.where(Subscription.status == status)

    result = await db.execute(
        stmt
    )
    rows = result.all()
    return {
        "items": [
            {
                "id": str(company.id),
                "name": company.name,
                "slug": company.slug,
                "type": company.type,
                "is_active": company.is_active,
                "is_suspended": company.is_suspended,
                "contact_email": company.contact_email,
                "contact_phone": company.contact_phone,
                "subscription_status": sub.status if sub else None,
                "subscription_plan": sub.plan if sub else None,
                "stores_count": stores_count or 0,
                "orders_count_30d": orders_count_30d or 0,
                "revenue_xof_30d": revenue_xof_30d or 0,
                "created_at": company.created_at.isoformat(),
            }
            for company, sub, stores_count, orders_count_30d, revenue_xof_30d in rows
        ],
        "total": len(rows),
    }


@router.post("/plans")
async def create_plan(
    data: CreatePlanRequest,
    current_user=Depends(require_permission("*")),
    db: AsyncSession = Depends(get_db),
):
    plan = Plan(
        code=data.code,
        name=data.name,
        billing_cycle=data.billing_cycle,
        amount_xof=data.amount_xof,
        commission_rate=data.commission_rate,
        features=data.features,
    )
    db.add(plan)
    await db.flush()
    return {"id": str(plan.id), "code": plan.code}


@router.post("/companies/{company_id}/suspend")
async def suspend_company(
    company_id: UUID,
    data: SuspendCompanyRequest,
    current_user=Depends(require_permission("*")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise NotFoundError("Entreprise")

    company.is_active = False
    company.is_suspended = True

    log = AuditLog(
        user_id=current_user.id,
        action="company.suspended",
        resource_type="company",
        resource_id=company.id,
        new_data={"reason": data.reason, "is_suspended": True},
    )
    db.add(log)
    return {"message": f"Entreprise '{company.name}' suspendue"}


@router.post("/companies/{company_id}/activate")
async def activate_company(
    company_id: UUID,
    current_user=Depends(require_permission("*")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise NotFoundError("Entreprise")
    company.is_active = True
    company.is_suspended = False
    log = AuditLog(
        user_id=current_user.id,
        action="company.activated",
        resource_type="company",
        resource_id=company.id,
        new_data={"is_suspended": False},
    )
    db.add(log)
    return {"message": f"Entreprise '{company.name}' activée"}


@router.post("/staff")
async def create_staff_user(
    data: CreateStaffRequest,
    current_user=Depends(require_permission("*")),
    db: AsyncSession = Depends(get_db),
):
    """Crée un employé staff avec son rôle."""
    from core.security import hash_password

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()

    role = UserCompanyRole(
        user_id=user.id,
        company_id=data.company_id,
        role=data.role,
    )
    db.add(role)

    log = AuditLog(
        user_id=current_user.id,
        company_id=data.company_id,
        action="staff.created",
        resource_type="user",
        resource_id=user.id,
        new_data={"email": data.email, "role": data.role},
    )
    db.add(log)

    return {"id": str(user.id), "email": user.email, "role": data.role}


@router.post("/companies", summary="Créer une entreprise avec son propriétaire (superadmin)")
async def create_company_with_owner(
    data: CreateCompanyWithOwnerRequest,
    current_user=Depends(require_permission("*")),
    db: AsyncSession = Depends(get_db),
):
    """Superadmin : crée une entreprise + son compte company_owner en une seule opération."""
    from core.security import hash_password
    from apps.companies.models import Company, Subscription

    try:
        from python_slugify import slugify
        base_slug = slugify(data.company_name)
    except ModuleNotFoundError:
        import re as _re
        base_slug = _re.sub(r"[^a-z0-9]+", "-", data.company_name.lower().strip()).strip("-")

    slug_result = await db.execute(select(Company).where(Company.slug.like(f"{base_slug}%")))
    existing_slugs = slug_result.scalars().all()
    slug = base_slug if not existing_slugs else f"{base_slug}-{len(existing_slugs)}"

    valid_types = {"boutique", "supermarket", "restaurant", "proximity", "pharmacy", "other"}
    company_type = data.company_type if data.company_type in valid_types else "other"

    company = Company(
        name=data.company_name,
        slug=slug,
        type=company_type,
        country=data.country,
        currency=data.currency,
        contact_email=data.contact_email or data.owner_email,
        contact_phone=data.contact_phone or data.owner_phone,
        is_active=True,
    )
    db.add(company)
    await db.flush()

    sub = Subscription(company_id=company.id, plan="starter", status="trial")
    db.add(sub)

    existing_user = await db.execute(select(User).where(User.email == data.owner_email))
    owner = existing_user.scalar_one_or_none()
    if not owner:
        owner = User(
            email=data.owner_email,
            phone=data.owner_phone,
            first_name=data.owner_first_name,
            last_name=data.owner_last_name,
            password_hash=hash_password(data.owner_password),
            is_active=True,
            is_verified=True,
            email_verified=True,
        )
        db.add(owner)
        await db.flush()

    role = UserCompanyRole(user_id=owner.id, company_id=company.id, role="company_owner")
    db.add(role)

    log = AuditLog(
        user_id=current_user.id,
        action="company.created_by_admin",
        resource_type="company",
        resource_id=company.id,
        new_data={"company_name": data.company_name, "owner_email": data.owner_email},
    )
    db.add(log)
    await db.commit()

    try:
        from apps.notifications.service import EmailService
        await EmailService.send_merchant_welcome(
            email=owner.email,
            first_name=owner.first_name,
            company_name=company.name,
        )
    except Exception as exc:
        logger.error("Merchant welcome email not sent: %s", exc)

    return {
        "company_id": str(company.id),
        "company_name": company.name,
        "slug": slug,
        "owner_id": str(owner.id),
        "owner_email": owner.email,
        "message": f"Entreprise '{company.name}' créée avec le compte propriétaire.",
    }


@router.patch("/companies/{company_id}/suspend", summary="Suspendre ou réactiver une entreprise")
async def toggle_suspend_company(
    company_id: UUID,
    data: SuspendToggleRequest,
    current_user=Depends(require_permission("*")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise NotFoundError("Entreprise")

    company.is_active = not data.suspend
    company.is_suspended = data.suspend
    action = "company.suspended" if data.suspend else "company.activated"

    log = AuditLog(
        user_id=current_user.id,
        action=action,
        resource_type="company",
        resource_id=company.id,
        new_data={"is_active": company.is_active, "reason": data.reason},
    )
    db.add(log)
    msg = "suspendue" if data.suspend else "réactivée"
    return {"message": f"Entreprise '{company.name}' {msg}", "is_active": company.is_active}


@router.get("/audit-logs")
async def get_audit_logs(
    company_id: Optional[UUID] = None,
    action: Optional[str] = None,
    limit: int = 100,
    current_user=Depends(require_permission("*")),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if company_id:
        query = query.where(AuditLog.company_id == company_id)
    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))

    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": str(l.id),
            "action": l.action,
            "user_id": str(l.user_id) if l.user_id else None,
            "company_id": str(l.company_id) if l.company_id else None,
            "resource_type": l.resource_type,
            "resource_id": str(l.resource_id) if l.resource_id else None,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


@router.get("/stats")
async def platform_stats(
    current_user=Depends(require_permission("*")),
    db: AsyncSession = Depends(get_db),
):
    """Statistiques globales de la plateforme."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_companies = await db.execute(select(func.count(Company.id)))
    active_companies = await db.execute(
        select(func.count(Company.id)).where(Company.is_active == True)
    )
    total_users = await db.execute(select(func.count(User.id)))
    orders_this_month = await db.execute(
        select(func.count(Order.id)).where(Order.created_at >= month_start)
    )

    total_revenue = await db.execute(
        select(func.coalesce(func.sum(Payment.amount_xof), 0)).where(Payment.status == "confirmed")
    )
    revenue_this_month = await db.execute(
        select(func.coalesce(func.sum(Payment.amount_xof), 0)).where(
            Payment.status == "confirmed",
            Payment.created_at >= month_start,
        )
    )

    return {
        "total_companies": total_companies.scalar() or 0,
        "active_companies": active_companies.scalar() or 0,
        "active_subscriptions": active_companies.scalar() or 0,
        "total_users": total_users.scalar() or 0,
        "orders_this_month": orders_this_month.scalar() or 0,
        "revenue_xof": revenue_this_month.scalar() or 0,
        "total_revenue_xof": total_revenue.scalar() or 0,
    }


@router.get("/users")
async def list_platform_users(
    search: Optional[str] = Query(default=None),
    role: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    current_user=Depends(require_permission("*")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(User, UserCompanyRole)
        .outerjoin(UserCompanyRole, UserCompanyRole.user_id == User.id)
        .order_by(User.created_at.desc())
        .limit(limit)
    )
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
                User.email.ilike(pattern),
                User.phone.ilike(pattern),
            )
        )
    if role:
        stmt = stmt.where(UserCompanyRole.role == role)

    result = await db.execute(stmt)
    rows = result.all()

    seen: set[str] = set()
    items: list[dict] = []
    for user, user_role in rows:
        if str(user.id) in seen:
            continue
        seen.add(str(user.id))
        items.append(
            {
                "id": str(user.id),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone": user.phone,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "role": user_role.role if user_role else "customer",
                "company_id": str(user_role.company_id) if user_role and user_role.company_id else None,
                "created_at": user.created_at.isoformat(),
            }
        )
    return {"items": items, "total": len(items)}
