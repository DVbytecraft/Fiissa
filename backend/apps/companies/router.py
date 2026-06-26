import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.catalog.service import CatalogResolutionService
from apps.companies.models import Company, CompanyRegistrationRequest, CompanySetting, FeatureFlag, Plan, Subscription, SubscriptionInvoice, SubscriptionRenewal
from apps.notifications.models import AuditLog
from apps.companies.service import SubscriptionService
from core.database import get_db
from core.dependencies import (
    TenantContext,
    get_current_user,
    get_tenant_context,
    require_permission,
)
from core.exceptions import BadRequestError, NotFoundError, TenantAccessDenied
from core.security import hash_password

try:
    from python_slugify import slugify
except ModuleNotFoundError:
    import re

    def slugify(value: str) -> str:
        value = value.lower().strip()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        return value.strip("-")


router = APIRouter(prefix="/companies", tags=["Entreprises"])


class CompanyCreate(BaseModel):
    name: str
    type: str
    country: str = "SN"
    currency: str = "XOF"
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[dict] = None
    description: Optional[str] = None
    website_url: Optional[str] = None
    opening_hours: Optional[dict] = None


class CompanySettingsUpdate(BaseModel):
    currency: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    catalog_mode: Optional[str] = None
    payment_mode: Optional[str] = None
    delivery_mode: Optional[str] = None
    vat_rate: Optional[Decimal] = None
    extra: Optional[dict] = None


class CatalogConfigUpdate(BaseModel):
    store_id: Optional[UUID] = None
    mode: str
    endpoint_url: Optional[str] = None
    http_method: str = "GET"
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    headers: Optional[dict] = None
    response_mapping: Optional[dict] = None
    timeout_seconds: int = 10
    cache_ttl_seconds: int = 300
    fallback_to_internal: bool = True


class FeatureFlagUpdate(BaseModel):
    key: str
    enabled: bool
    config: Optional[dict] = None


class SubscriptionChangeRequest(BaseModel):
    plan_code: str


class MerchantRegistrationRequestCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=5, max_length=30)
    password: str = Field(..., min_length=8, max_length=128)
    company_name: str = Field(..., min_length=2, max_length=255)
    company_type: str = Field(..., min_length=2, max_length=50)


class RegistrationRequestRejectData(BaseModel):
    reason: Optional[str] = None


@router.post("/")
async def create_company(
    data: CompanyCreate,
    current_user=Depends(require_permission("company.create")),
    db: AsyncSession = Depends(get_db),
):
    base_slug = slugify(data.name)
    result = await db.execute(select(Company).where(Company.slug.like(f"{base_slug}%")))
    existing = result.scalars().all()
    slug = base_slug if not existing else f"{base_slug}-{len(existing)}"

    company = Company(
        slug=slug,
        **data.model_dump(),
    )
    db.add(company)
    await db.flush()

    sub = Subscription(
        company_id=company.id,
        plan="starter",
        status="trial",
    )
    db.add(sub)

    from apps.users.models import UserCompanyRole

    db.add(
        UserCompanyRole(
            user_id=current_user.id,
            company_id=company.id,
            role="company_owner",
        )
    )

    if current_user.email:
        from apps.notifications.service import EmailService

        try:
            await EmailService.send_merchant_welcome(
                email=current_user.email,
                first_name=current_user.first_name,
                company_name=company.name,
            )
        except Exception as exc:
            logger.error("Merchant welcome email not sent: %s", exc)

    return {"id": str(company.id), "name": company.name, "slug": company.slug}


@router.get("/me/settings")
async def get_my_company_settings(
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("company.read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CompanySetting).where(CompanySetting.company_id == ctx.company_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = CompanySetting(company_id=ctx.company_id)
        db.add(settings)
        await db.flush()

    return {
        "id": str(settings.id),
        "company_id": str(settings.company_id),
        "currency": settings.currency,
        "timezone": settings.timezone,
        "language": settings.language,
        "catalog_mode": settings.catalog_mode,
        "payment_mode": settings.payment_mode,
        "delivery_mode": settings.delivery_mode,
        "vat_rate": float(settings.vat_rate),
        "extra": settings.extra,
    }


@router.patch("/me/settings")
async def update_my_company_settings(
    data: CompanySettingsUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("company.update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CompanySetting).where(CompanySetting.company_id == ctx.company_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = CompanySetting(company_id=ctx.company_id)
        db.add(settings)
        await db.flush()

    for key, value in data.model_dump(exclude_none=True).items():
        setattr(settings, key, value)

    return {"id": str(settings.id), "message": "Parametres entreprise mis a jour"}


@router.get("/me/catalog")
async def get_my_catalog_configuration(
    store_id: Optional[UUID] = None,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("company.read")),
    db: AsyncSession = Depends(get_db),
):
    service = CatalogResolutionService(db)
    return await service.get_catalog_configuration(ctx.company_id, store_id)


@router.put("/me/catalog")
async def update_my_catalog_configuration(
    data: CatalogConfigUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("company.update")),
    db: AsyncSession = Depends(get_db),
):
    allowed_modes = {"internal", "csv_import", "external_api", "hybrid"}
    if data.mode not in allowed_modes:
        raise BadRequestError("Mode catalogue invalide", code="invalid_catalog_mode")

    service = CatalogResolutionService(db)
    if data.mode in {"external_api", "hybrid"}:
        if not data.endpoint_url:
            raise BadRequestError("endpoint_url est requis pour ce mode", code="missing_endpoint_url")
        integration = await service.upsert_api_integration(
            company_id=ctx.company_id,
            store_id=data.store_id,
            mode=data.mode,
            endpoint_url=data.endpoint_url,
            http_method=data.http_method,
            api_key=data.api_key,
            api_secret=data.api_secret,
            headers=data.headers,
            response_mapping=data.response_mapping,
            timeout_seconds=data.timeout_seconds,
            cache_ttl_seconds=data.cache_ttl_seconds,
            fallback_to_internal=data.fallback_to_internal,
        )
        return {
            "message": "Configuration catalogue mise a jour",
            "mode": data.mode,
            "integration_id": str(integration.id),
        }

    source = await service.update_catalog_mode(ctx.company_id, data.store_id, data.mode)
    return {
        "message": "Configuration catalogue mise a jour",
        "mode": source.mode,
        "store_id": str(source.store_id) if source.store_id else None,
    }


@router.get("/me/feature-flags")
async def get_my_feature_flags(
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("feature_flags.read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FeatureFlag)
        .where(FeatureFlag.company_id == ctx.company_id)
        .order_by(FeatureFlag.key.asc())
    )
    flags = result.scalars().all()
    return {
        "items": [
            {
                "id": str(flag.id),
                "key": flag.key,
                "enabled": flag.enabled,
                "config": flag.config,
            }
            for flag in flags
        ]
    }


@router.put("/me/feature-flags")
async def upsert_my_feature_flag(
    data: FeatureFlagUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("feature_flags.update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FeatureFlag).where(
            FeatureFlag.company_id == ctx.company_id,
            FeatureFlag.key == data.key,
        )
    )
    flag = result.scalar_one_or_none()
    if not flag:
        flag = FeatureFlag(
            company_id=ctx.company_id,
            key=data.key,
            enabled=data.enabled,
            config=data.config,
        )
        db.add(flag)
        await db.flush()
    else:
        flag.enabled = data.enabled
        flag.config = data.config

    return {"id": str(flag.id), "key": flag.key, "enabled": flag.enabled}


@router.get("/plans")
async def list_plans(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.amount_xof.asc()))
    plans = result.scalars().all()
    return {
        "items": [
            {
                "id": str(plan.id),
                "code": plan.code,
                "name": plan.name,
                "billing_cycle": plan.billing_cycle,
                "amount_xof": plan.amount_xof,
                "commission_rate": float(plan.commission_rate),
                "features": plan.features,
            }
            for plan in plans
        ]
    }


@router.get("/me/subscription")
async def get_my_subscription(
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("subscriptions.read")),
    db: AsyncSession = Depends(get_db),
):
    service = SubscriptionService(db)
    subscription = await service.get_or_create_subscription(ctx.company_id)
    return {
        "id": str(subscription.id),
        "company_id": str(subscription.company_id),
        "plan": subscription.plan,
        "status": subscription.status,
        "billing_cycle": subscription.billing_cycle,
        "amount_xof": subscription.amount_xof,
        "commission_rate": float(subscription.commission_rate),
        "trial_ends_at": subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else None,
        "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        "expires_at": (
            subscription.current_period_end.isoformat()
            if subscription.current_period_end
            else subscription.trial_ends_at.isoformat()
            if subscription.trial_ends_at
            else None
        ),
    }


@router.post("/me/subscription/change")
async def change_my_subscription(
    data: SubscriptionChangeRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("company.update")),
    db: AsyncSession = Depends(get_db),
):
    service = SubscriptionService(db)
    subscription = await service.change_plan(ctx.company_id, data.plan_code)
    return {
        "id": str(subscription.id),
        "plan": subscription.plan,
        "status": subscription.status,
    }


@router.get("/me/subscription/invoices")
async def get_my_subscription_invoices(
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("subscriptions.read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SubscriptionInvoice)
        .where(SubscriptionInvoice.company_id == ctx.company_id)
        .order_by(SubscriptionInvoice.created_at.desc())
    )
    invoices = result.scalars().all()
    return {
        "items": [
            {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "status": invoice.status,
                "amount_xof": invoice.amount_xof,
                "tax_xof": invoice.tax_xof,
                "total_xof": invoice.total_xof,
                "metadata": invoice.invoice_metadata,
            }
            for invoice in invoices
        ]
    }


@router.post("/me/subscription/cancel")
async def cancel_my_subscription(
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("company.update")),
    db: AsyncSession = Depends(get_db),
):
    service = SubscriptionService(db)
    subscription = await service.cancel_subscription(ctx.company_id)
    return {"id": str(subscription.id), "status": subscription.status, "cancelled_at": subscription.cancelled_at.isoformat() if subscription.cancelled_at else None}


@router.post("/me/subscription/invoices/{invoice_id}/pay")
async def mark_invoice_paid(
    invoice_id: UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("company.update")),
    db: AsyncSession = Depends(get_db),
):
    service = SubscriptionService(db)
    invoice = await service.mark_invoice_paid(ctx.company_id, invoice_id)
    return {"id": str(invoice.id), "status": invoice.status, "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None}


@router.get("/me/subscription/renewals")
async def get_my_subscription_renewals(
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("subscriptions.read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SubscriptionRenewal)
        .where(SubscriptionRenewal.company_id == ctx.company_id)
        .order_by(SubscriptionRenewal.created_at.desc())
    )
    renewals = result.scalars().all()
    return {
        "items": [
            {
                "id": str(renewal.id),
                "status": renewal.status,
                "previous_period_end": renewal.previous_period_end.isoformat() if renewal.previous_period_end else None,
                "new_period_end": renewal.new_period_end.isoformat() if renewal.new_period_end else None,
                "processed_at": renewal.processed_at.isoformat() if renewal.processed_at else None,
                "error_message": renewal.error_message,
            }
            for renewal in renewals
        ]
    }


# ------------------------------------------------------------------ #
#  MERCHANT ONBOARDING — auto-inscription commerçant                  #
# ------------------------------------------------------------------ #

@router.post("/registration-request", status_code=201, summary="Soumettre une demande d'inscription marchand")
async def submit_registration_request(
    data: MerchantRegistrationRequestCreate,
    db: AsyncSession = Depends(get_db),
):
    """Route publique : soumission d'une demande d'inscription marchand."""
    existing = await db.execute(
        select(CompanyRegistrationRequest).where(CompanyRegistrationRequest.email == str(data.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Une demande avec cet email existe déjà")

    req = CompanyRegistrationRequest(
        first_name=data.first_name,
        last_name=data.last_name,
        email=str(data.email),
        phone=data.phone,
        password_hash=hash_password(data.password),
        company_name=data.company_name,
        company_type=data.company_type,
        status="pending",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    return {
        "id": str(req.id),
        "status": "pending",
        "message": "Votre demande a été soumise. Vous recevrez une réponse sous 24h.",
    }


@router.get("/registration-requests", summary="Lister les demandes d'inscription (superadmin)")
async def list_registration_requests(
    status: str = "pending",
    current_user=Depends(require_permission("*")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CompanyRegistrationRequest)
        .where(CompanyRegistrationRequest.status == status)
        .order_by(CompanyRegistrationRequest.created_at.desc())
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": str(r.id),
                "first_name": r.first_name,
                "last_name": r.last_name,
                "email": r.email,
                "phone": r.phone,
                "company_name": r.company_name,
                "company_type": r.company_type,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in items
        ]
    }


@router.post("/registration-requests/{request_id}/approve", summary="Approuver une demande d'inscription (superadmin)")
async def approve_registration_request(
    request_id: UUID,
    current_user=Depends(require_permission("*")),
    db: AsyncSession = Depends(get_db),
):
    """Approuve la demande : crée l'utilisateur + entreprise + rôle company_owner."""
    result = await db.execute(
        select(CompanyRegistrationRequest).where(CompanyRegistrationRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cette demande est déjà {req.status}")

    from apps.users.models import User, UserCompanyRole

    # Créer l'utilisateur
    user = User(
        email=req.email,
        phone=req.phone,
        first_name=req.first_name,
        last_name=req.last_name,
        password_hash=req.password_hash,
        is_active=True,
        is_verified=True,
        email_verified=True,
    )
    db.add(user)
    await db.flush()

    # Créer le slug de l'entreprise
    base_slug = req.company_name.lower().strip()
    try:
        from python_slugify import slugify
        base_slug = slugify(req.company_name)
    except ModuleNotFoundError:
        import re as _re
        base_slug = _re.sub(r"[^a-z0-9]+", "-", base_slug).strip("-")

    slug_result = await db.execute(select(Company).where(Company.slug.like(f"{base_slug}%")))
    existing_slugs = slug_result.scalars().all()
    slug = base_slug if not existing_slugs else f"{base_slug}-{len(existing_slugs)}"

    # Mapper le company_type sur l'enum existant
    valid_types = {"boutique", "supermarket", "restaurant", "proximity", "pharmacy", "other"}
    company_type = req.company_type if req.company_type in valid_types else "other"

    # Créer l'entreprise
    company = Company(
        name=req.company_name,
        slug=slug,
        type=company_type,
        contact_email=req.email,
        contact_phone=req.phone,
        is_active=True,
    )
    db.add(company)
    await db.flush()

    # Abonnement trial automatique
    sub = Subscription(
        company_id=company.id,
        plan="starter",
        status="trial",
    )
    db.add(sub)

    # Assigner le rôle company_owner
    role = UserCompanyRole(
        user_id=user.id,
        company_id=company.id,
        role="company_owner",
    )
    db.add(role)

    # Mettre à jour la demande
    req.status = "approved"
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by_id = current_user.id

    await db.commit()

    try:
        from apps.notifications.service import EmailService
        await EmailService.send_merchant_welcome(
            email=user.email,
            first_name=user.first_name,
            company_name=company.name,
        )
    except Exception as exc:
        logger.error("Merchant welcome (onboarding approval) email not sent: %s", exc)

    return {
        "success": True,
        "company_id": str(company.id),
        "user_id": str(user.id),
        "message": f"Demande approuvée. Entreprise '{company.name}' créée.",
    }


@router.post("/registration-requests/{request_id}/reject", summary="Rejeter une demande d'inscription (superadmin)")
async def reject_registration_request(
    request_id: UUID,
    data: RegistrationRequestRejectData,
    current_user=Depends(require_permission("*")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CompanyRegistrationRequest).where(CompanyRegistrationRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cette demande est déjà {req.status}")

    req.status = "rejected"
    req.rejection_reason = data.reason or ""
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by_id = current_user.id
    await db.commit()

    return {"success": True, "message": "Demande rejetée."}


# ------------------------------------------------------------------ #
#  PROFIL PUBLIC ENTREPRISE (par slug — pas d'auth requise)           #
# ------------------------------------------------------------------ #

@router.get("/public/{slug}", summary="Profil public d'une enseigne")
async def get_company_public_profile(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Route publique : retourne les informations visibles par les clients
    (logo, horaires, description, téléphone).
    Accessible sans authentification.
    """
    result = await db.execute(
        select(Company).where(Company.slug == slug, Company.is_active == True)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise NotFoundError("Enseigne introuvable")

    from apps.loyalty.models import LoyaltyProgram
    loyalty_result = await db.execute(
        select(LoyaltyProgram).where(
            LoyaltyProgram.company_id == company.id,
            LoyaltyProgram.is_active == True,
            LoyaltyProgram.loyalty_enabled == True,
        )
    )
    loyalty = loyalty_result.scalar_one_or_none()

    return {
        "id": str(company.id),
        "slug": company.slug,
        "name": company.name,
        "type": company.type,
        "logo_url": company.logo_url,
        "description": company.description,
        "website_url": company.website_url,
        "contact_phone": company.contact_phone,
        "contact_email": company.contact_email,
        "address": company.address,
        "opening_hours": company.opening_hours,
        "country": company.country,
        "currency": company.currency,
        "loyalty": {
            "enabled": bool(loyalty),
            "program_name": loyalty.name if loyalty else None,
            "points_per_xof": float(loyalty.points_per_xof) if loyalty else None,
            "description": loyalty.description if loyalty else None,
        } if loyalty else {"enabled": False},
    }


@router.patch("/me/public-profile", summary="Mettre à jour le profil public de l'entreprise")
async def update_company_public_profile(
    data: CompanyUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("company.update")),
    db: AsyncSession = Depends(get_db),
):
    """Met à jour les informations visibles par les clients : logo, horaires, description, téléphone."""
    result = await db.execute(select(Company).where(Company.id == ctx.company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise NotFoundError("Entreprise")

    updates = data.model_dump(exclude_none=True)
    for key, value in updates.items():
        setattr(company, key, value)

    log = AuditLog(
        company_id=ctx.company_id,
        user_id=current_user.id,
        action="company.profile_updated",
        resource_type="company",
        resource_id=company.id,
        new_data=updates,
    )
    db.add(log)

    return {
        "slug": company.slug,
        "name": company.name,
        "logo_url": company.logo_url,
        "description": company.description,
        "website_url": company.website_url,
        "opening_hours": company.opening_hours,
        "contact_phone": company.contact_phone,
        "message": "Profil public mis à jour",
    }


# ------------------------------------------------------------------ #
#  ROUTES PARAMÉTRÉES (/{company_id} — en dernier)                    #
# ------------------------------------------------------------------ #

@router.get("/{company_id}")
async def get_company(
    company_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise NotFoundError("Entreprise")

    from apps.users.models import UserCompanyRole

    role_result = await db.execute(
        select(UserCompanyRole).where(
            UserCompanyRole.user_id == current_user.id,
        )
    )
    roles = role_result.scalars().all()
    has_access = any(
        role.role == "super_admin" or str(role.company_id) == str(company_id)
        for role in roles
    )
    if not has_access:
        raise TenantAccessDenied()

    return {
        "id": str(company.id),
        "name": company.name,
        "slug": company.slug,
        "type": company.type,
        "country": company.country,
        "currency": company.currency,
        "is_active": company.is_active,
        "logo_url": company.logo_url,
        "contact_email": company.contact_email,
        "contact_phone": company.contact_phone,
    }


@router.patch("/{company_id}")
async def update_company(
    company_id: UUID,
    data: CompanyUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("company.update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise NotFoundError("Entreprise")

    # Vérification tenant : seul le superadmin peut modifier une autre entreprise
    active_role = getattr(current_user, "_active_role", None)
    if str(company.id) != str(ctx.company_id) and (not active_role or active_role.role != "super_admin"):
        raise TenantAccessDenied()

    for key, value in data.model_dump(exclude_none=True).items():
        setattr(company, key, value)

    return {"id": str(company.id), "message": "Entreprise mise a jour"}
