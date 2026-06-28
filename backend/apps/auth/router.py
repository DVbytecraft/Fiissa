import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.schemas import (
    CustomerLoginRequest,
    CustomerRegisterRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    OTPSentResponse,
    RefreshTokenRequest,
    RequestEmailVerificationResponse,
    ResetPasswordRequest,
    StaffLoginRequest,
    TokenResponse,
    UpdateProfileRequest,
    VerifyEmailRequest,
    VerifyOTPRequest,
)
from apps.auth.service import AuthService
from apps.notifications.models import AuditLog
from apps.users.models import User, UserCompanyRole
from core.database import get_db
from core.dependencies import get_current_user, get_tenant_context, TenantContext, require_permission
from core.exceptions import NotFoundError
from core.rate_limit import limiter
from core.security import hash_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentification"])


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "")


@router.post("/register", response_model=OTPSentResponse, summary="Inscription client ou demande entreprise")
@limiter.limit("5/minute")
async def register_customer(
    data: CustomerRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Inscription client (OTP email) ou soumission d'une demande entreprise (pending → validation superadmin).
    """
    if data.account_type == "company":
        from sqlalchemy import select as _select
        from apps.companies.models import CompanyRegistrationRequest
        from core.security import hash_password as _hash
        existing = await db.execute(
            _select(CompanyRegistrationRequest).where(CompanyRegistrationRequest.email == str(data.email))
        )
        if existing.scalar_one_or_none():
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Une demande avec cet email existe déjà")
        if not data.company_name or not data.company_type:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="company_name et company_type sont requis")
        req = CompanyRegistrationRequest(
            first_name=data.first_name,
            last_name=data.last_name,
            email=str(data.email),
            phone=data.phone,
            password_hash=_hash(data.password),
            company_name=data.company_name,
            company_type=data.company_type,
            status="pending",
        )
        db.add(req)
        await db.commit()
        return OTPSentResponse(
            message="Votre demande a été soumise. Vous recevrez vos accès sous 24h.",
            destination="pending",
        )
    service = AuthService(db)
    return await service.register_customer(data, ip_address=_get_ip(request))


@router.post("/login/request-otp", response_model=OTPSentResponse, summary="Demande OTP client")
@limiter.limit("5/minute")
async def request_otp(
    data: CustomerLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Envoie un OTP par SMS au numéro de téléphone du client."""
    service = AuthService(db)
    return await service.request_otp(data, ip_address=_get_ip(request))


@router.post("/login/verify-otp", response_model=TokenResponse, summary="Vérification OTP client")
@limiter.limit("10/minute")
async def verify_otp(
    data: VerifyOTPRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Vérifie le code OTP et retourne les tokens JWT.
    Le refresh token est à rotation unique : chaque utilisation génère un nouveau.
    """
    service = AuthService(db)
    return await service.verify_otp(data, ip_address=_get_ip(request))


@router.post("/staff/login", response_model=TokenResponse, summary="Connexion staff")
@limiter.limit("10/minute")
async def staff_login(
    data: StaffLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Connexion des employés (gérant, comptable, préparateur, support, sécurité).
    Utilise email + mot de passe.
    """
    service = AuthService(db)
    return await service.staff_login(data, ip_address=_get_ip(request))


@router.post("/refresh", response_model=TokenResponse, summary="Renouveler les tokens")
async def refresh_token(
    data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Rotation du refresh token.
    L'ancien token est immédiatement révoqué.
    """
    service = AuthService(db)
    return await service.refresh_access_token(data.refresh_token, ip_address=_get_ip(request))


@router.post("/logout", summary="Déconnexion")
async def logout(
    data: RefreshTokenRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Révoque le refresh token. Le token d'accès expire naturellement."""
    service = AuthService(db)
    await service.logout(data.refresh_token, user_id=current_user.id)
    return {"message": "Déconnecté avec succès"}


@router.get("/me", summary="Profil utilisateur courant")
async def get_me(current_user=Depends(get_current_user)):
    """Retourne les informations de l'utilisateur authentifié."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "phone": current_user.phone,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "full_name": current_user.full_name,
        "is_verified": current_user.is_verified,
        "email_verified": current_user.email_verified,
        "phone_verified": current_user.phone_verified,
        "preferred_language": current_user.preferred_language,
        "marketing_opt_in": current_user.marketing_opt_in,
    }


@router.patch("/me", summary="Mettre à jour le profil")
async def update_me(
    data: UpdateProfileRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from apps.users.service import UserService

    updates = data.model_dump(exclude_none=True)
    if not updates:
        return {"message": "Aucune modification"}

    service = UserService(db)
    user = await service.update_profile(current_user.id, updates)
    await db.commit()
    return {
        "id": str(user.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "preferred_language": user.preferred_language,
        "marketing_opt_in": user.marketing_opt_in,
        "message": "Profil mis à jour",
    }


# ── Vérification email ────────────────────────────────────────────────────────

@router.post(
    "/request-email-verification",
    response_model=RequestEmailVerificationResponse,
    summary="Demander la vérification email",
)
@limiter.limit("3/minute")
async def request_email_verification(
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Envoie un email de vérification à l'adresse de l'utilisateur connecté.
    En dev, retourne aussi le token pour faciliter les tests.
    """
    from apps.auth.identity import EmailVerificationService
    from apps.notifications.service import EmailService
    from core.config import settings

    service = EmailVerificationService(db)
    raw_token = await service.request_verification(current_user.id)
    await db.commit()

    await EmailService.send_email_verification(
        email=current_user.email,
        first_name=current_user.first_name,
        raw_token=raw_token,
    )

    return RequestEmailVerificationResponse(
        message="Email de vérification envoyé",
        debug_token=raw_token if settings.ENVIRONMENT == "development" else None,
    )


@router.post("/verify-email", summary="Vérifier l'adresse email")
@limiter.limit("10/minute")
async def verify_email(
    data: VerifyEmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Vérifie l'email avec le token reçu par email."""
    from apps.auth.identity import EmailVerificationService

    service = EmailVerificationService(db)
    user = await service.verify_email(data.token)
    await db.commit()
    return {"message": "Email vérifié avec succès", "email": user.email}


# ── Réinitialisation mot de passe ─────────────────────────────────────────────

@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Demander la réinitialisation du mot de passe",
)
@limiter.limit("3/minute")
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Envoie un email de réinitialisation si l'adresse existe.
    Retourne toujours 200 pour éviter l'énumération des emails.
    """
    from apps.auth.identity import PasswordResetService
    from apps.notifications.service import EmailService
    from core.config import settings

    service = PasswordResetService(db)
    result = await service.request_reset(str(data.email))
    await db.commit()

    debug_token = None
    if result is not None:
        user, raw_token = result
        debug_token = raw_token if settings.ENVIRONMENT == "development" else None
        await EmailService.send_password_reset(
            email=user.email,
            first_name=user.first_name,
            raw_token=raw_token,
        )

    return ForgotPasswordResponse(
        message="Si cette adresse existe, vous recevrez un lien de réinitialisation.",
        debug_token=debug_token,
    )


@router.post("/reset-password", summary="Réinitialiser le mot de passe")
@limiter.limit("5/minute")
async def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Réinitialise le mot de passe avec le token reçu par email."""
    from apps.auth.identity import PasswordResetService

    service = PasswordResetService(db)
    await service.reset_password(data.token, data.new_password)
    await db.commit()
    return {"message": "Mot de passe réinitialisé avec succès"}


# ─── Gestion des employés (marchand) ─────────────────────────────

class InviteStaffRequest(BaseModel):
    email: str
    first_name: str
    last_name: str
    role: str
    store_id: Optional[UUID] = None
    send_email: bool = True


@router.get("/staff", summary="Liste des employés de l'entreprise")
async def list_staff(
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("users.read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User, UserCompanyRole)
        .join(UserCompanyRole, UserCompanyRole.user_id == User.id)
        .where(UserCompanyRole.company_id == ctx.company_id)
        .where(UserCompanyRole.role != "customer")
        .order_by(User.first_name.asc())
    )
    rows = result.all()
    return {
        "items": [
            {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": role.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
            }
            for user, role in rows
        ]
    }


@router.post("/staff/invite", summary="Inviter un employé")
async def invite_staff(
    data: InviteStaffRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("users.create")),
    db: AsyncSession = Depends(get_db),
):
    import secrets

    # Créer ou récupérer l'utilisateur
    existing = await db.execute(select(User).where(User.email == data.email))
    user = existing.scalar_one_or_none()

    temp_password = secrets.token_urlsafe(12)
    if not user:
        user = User(
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
            password_hash=hash_password(temp_password),
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.flush()

    # Assigner le rôle
    role = UserCompanyRole(
        user_id=user.id,
        company_id=ctx.company_id,
        store_id=data.store_id,
        role=data.role,
    )
    db.add(role)

    log = AuditLog(
        company_id=ctx.company_id,
        user_id=current_user.id,
        action="staff.invited",
        resource_type="user",
        resource_id=user.id,
        new_data={"email": data.email, "role": data.role},
    )
    db.add(log)

    # Le mot de passe temporaire est envoyé par email uniquement — jamais retourné dans l'API
    if data.send_email:
        from apps.companies.models import Company
        from apps.notifications.service import EmailService
        company_name_result = await db.execute(select(Company).where(Company.id == ctx.company_id))
        company_obj = company_name_result.scalar_one_or_none()
        try:
            await EmailService.send_staff_invitation(
                email=data.email,
                first_name=data.first_name,
                temp_password=temp_password,
                company_name=company_obj.name if company_obj else str(ctx.company_id),
            )
        except Exception as exc:
            logger.error("Staff invitation email not sent: %s", exc)

    return {
        "id": str(user.id),
        "email": user.email,
        "role": data.role,
        "message": (
            f"Employé {data.first_name} invité avec succès. "
            f"Les identifiants ont été envoyés par email."
        ),
    }


@router.delete("/staff/{user_id}", summary="Révoquer l'accès d'un employé")
async def remove_staff(
    user_id: UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("users.deactivate")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserCompanyRole).where(
            UserCompanyRole.user_id == user_id,
            UserCompanyRole.company_id == ctx.company_id,
        )
    )
    role = result.scalar_one_or_none()
    if not role:
        raise NotFoundError("Employé")

    await db.delete(role)

    log = AuditLog(
        company_id=ctx.company_id,
        user_id=current_user.id,
        action="staff.removed",
        resource_type="user",
        resource_id=user_id,
    )
    db.add(log)
    return {"message": "Accès révoqué"}


# ── Bootstrap premier superadmin ──────────────────────────────────────────────

class BootstrapAdminRequest(BaseModel):
    email: str
    password: str
    phone: Optional[str] = None
    first_name: str = "Super"
    last_name: str = "Admin"


@router.post("/bootstrap-admin", include_in_schema=False)
async def bootstrap_admin(
    data: BootstrapAdminRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Crée le premier superadmin.
    Automatiquement désactivé dès qu'un super_admin existe en base.
    """
    existing_role = await db.execute(
        select(UserCompanyRole).where(UserCompanyRole.role == "super_admin")
    )
    if existing_role.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Un superadmin existe déjà. Endpoint désactivé.")

    existing_user = await db.execute(select(User).where(User.email == data.email))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Cet email est déjà utilisé.")

    if len(data.password) < 8:
        raise HTTPException(status_code=422, detail="Le mot de passe doit contenir au moins 8 caractères.")

    user = User(
        email=data.email,
        phone=data.phone or None,
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
        company_id=None,
        role="super_admin",
    )
    db.add(role)
    await db.commit()

    logger.info("Bootstrap superadmin created: %s", data.email)
    return {"message": "Superadmin créé avec succès.", "email": data.email}


class AdminResetRequest(BaseModel):
    new_email: str
    new_password: str
    new_phone: Optional[str] = None
    new_first_name: Optional[str] = None
    new_last_name: Optional[str] = None


@router.post("/admin-reset", include_in_schema=False)
async def admin_reset(
    data: AdminResetRequest,
    db: AsyncSession = Depends(get_db),
):
    if len(data.new_password) < 8:
        raise HTTPException(status_code=422, detail="Le mot de passe doit contenir au moins 8 caractères.")

    # Use .limit(1) + .scalars().first() to safely handle multiple super_admin rows
    role_result = await db.execute(
        select(UserCompanyRole)
        .where(UserCompanyRole.role == "super_admin")
        .limit(1)
    )
    role = role_result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="Aucun superadmin trouvé.")

    user_result = await db.execute(
        select(User).where(User.id == role.user_id).limit(1)
    )
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur superadmin introuvable.")

    # Check email conflict only against OTHER users
    email_conflict_result = await db.execute(
        select(User.id).where(User.email == data.new_email, User.id != user.id).limit(1)
    )
    if email_conflict_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Cet email est déjà utilisé par un autre compte.")

    user.email = data.new_email
    user.password_hash = hash_password(data.new_password)
    if data.new_phone is not None:
        user.phone = data.new_phone or None
    if data.new_first_name:
        user.first_name = data.new_first_name
    if data.new_last_name:
        user.last_name = data.new_last_name
    user.is_verified = True

    # Remove all other super_admin roles so only this one account controls the system
    await db.execute(
        delete(UserCompanyRole).where(
            UserCompanyRole.role == "super_admin",
            UserCompanyRole.user_id != user.id,
        )
    )

    await db.commit()
    logger.info("Superadmin credentials updated and duplicates purged: %s", data.new_email)
    return {"message": "Compte superadmin mis à jour. Accès exclusif accordé.", "email": data.new_email}


@router.get("/debug-db-state", include_in_schema=False)
async def debug_db_state(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    import traceback
    try:
        ver = await db.execute(text("SELECT version_num FROM alembic_version"))
        versions = [r[0] for r in ver.fetchall()]

        cols = await db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' ORDER BY ordinal_position"
        ))
        user_cols = [r[0] for r in cols.fetchall()]

        test_err = None
        try:
            await db.execute(text("SELECT failed_login_attempts FROM users LIMIT 1"))
        except Exception as e:
            test_err = str(e)

        return {
            "alembic_versions": versions,
            "users_columns": user_cols,
            "failed_login_attempts_query_error": test_err,
        }
    except Exception as e:
        return {"error": type(e).__name__, "detail": str(e), "trace": traceback.format_exc()}


@router.post("/force-migrate", include_in_schema=False)
async def force_migrate(db: AsyncSession = Depends(get_db)):
    """
    Directly applies all idempotent DDL from migrations 0010–0018
    and stamps alembic_version, bypassing alembic's own runner.
    Safe to call multiple times — all statements use IF NOT EXISTS / IF EXISTS.
    """
    from sqlalchemy import text
    import traceback

    steps = []

    async def run(label: str, sql: str):
        try:
            await db.execute(text(sql))
            steps.append({"step": label, "status": "ok"})
        except Exception as e:
            steps.append({"step": label, "status": "error", "detail": str(e)})
            raise

    try:
        # 0010 — product enrichment
        await run("0010_products", """
            ALTER TABLE products
                ADD COLUMN IF NOT EXISTS brand VARCHAR(200),
                ADD COLUMN IF NOT EXISTS origin_country VARCHAR(100),
                ADD COLUMN IF NOT EXISTS weight_g INTEGER,
                ADD COLUMN IF NOT EXISTS volume_ml INTEGER,
                ADD COLUMN IF NOT EXISTS dimensions JSONB,
                ADD COLUMN IF NOT EXISTS tax_rate INTEGER,
                ADD COLUMN IF NOT EXISTS images JSONB,
                ADD COLUMN IF NOT EXISTS attributes JSONB,
                ADD COLUMN IF NOT EXISTS tags JSONB,
                ADD COLUMN IF NOT EXISTS min_order_qty INTEGER NOT NULL DEFAULT 1,
                ADD COLUMN IF NOT EXISTS max_order_qty INTEGER
        """)

        # 0011 — account lockout
        await run("0011_users_lockout", """
            ALTER TABLE users
                ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP WITH TIME ZONE
        """)

        # 0012 — Togo operators (enum values)
        await run("0012_togo_enum_flooz", """
            DO $$ BEGIN
                ALTER TYPE mobile_operator_enum ADD VALUE IF NOT EXISTS 'flooz';
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """)
        await run("0012_togo_enum_tmoney", """
            DO $$ BEGIN
                ALTER TYPE mobile_operator_enum ADD VALUE IF NOT EXISTS 'tmoney';
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """)

        # 0013 — loyalty validation mode
        await run("0013_loyalty_enum", """
            DO $$ BEGIN
                CREATE TYPE loyalty_validation_mode_enum AS ENUM ('auto', 'manual');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """)
        await run("0013_company_settings", """
            ALTER TABLE company_settings
                ADD COLUMN IF NOT EXISTS loyalty_validation_mode
                    loyalty_validation_mode_enum NOT NULL DEFAULT 'auto'
        """)

        # 0014 — merchant API keys
        await run("0014_merchant_api_keys", """
            CREATE TABLE IF NOT EXISTS merchant_api_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                name VARCHAR(200) NOT NULL,
                key_prefix VARCHAR(12) NOT NULL,
                key_hash VARCHAR(255) NOT NULL,
                scopes JSONB NOT NULL DEFAULT '[]',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                last_used_at TIMESTAMP WITH TIME ZONE,
                expires_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """)
        await run("0014_merchant_api_keys_idx1", """
            CREATE UNIQUE INDEX IF NOT EXISTS ix_merchant_api_keys_key_prefix
                ON merchant_api_keys(key_prefix)
        """)
        await run("0014_merchant_api_keys_idx2", """
            CREATE INDEX IF NOT EXISTS ix_merchant_api_keys_company_id
                ON merchant_api_keys(company_id)
        """)

        # 0015 — promotions
        await run("0015_promo_type_enum", """
            DO $$ BEGIN
                CREATE TYPE promotion_type_enum AS ENUM (
                    'percentage', 'fixed_amount', 'free_shipping', 'buy_x_get_y'
                );
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """)
        await run("0015_promo_applies_enum", """
            DO $$ BEGIN
                CREATE TYPE promotion_applies_to_enum AS ENUM (
                    'all', 'category', 'product', 'minimum_order'
                );
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """)
        await run("0015_promotions_table", """
            CREATE TABLE IF NOT EXISTS promotions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                name VARCHAR(200) NOT NULL,
                code VARCHAR(50),
                promotion_type promotion_type_enum NOT NULL,
                value NUMERIC(12,2) NOT NULL,
                applies_to promotion_applies_to_enum NOT NULL DEFAULT 'all',
                target_ids JSONB,
                minimum_order_amount NUMERIC(12,2),
                usage_limit INTEGER,
                usage_count INTEGER NOT NULL DEFAULT 0,
                per_customer_limit INTEGER,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                starts_at TIMESTAMP WITH TIME ZONE,
                ends_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """)
        await run("0015_orders_promotion_cols", """
            ALTER TABLE orders
                ADD COLUMN IF NOT EXISTS promotion_id UUID REFERENCES promotions(id) ON DELETE SET NULL,
                ADD COLUMN IF NOT EXISTS promotion_code VARCHAR(50)
        """)

        # 0016 — delivery zones
        await run("0016_delivery_zones", """
            CREATE TABLE IF NOT EXISTS delivery_zones (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                zone_type VARCHAR(50) NOT NULL DEFAULT 'polygon',
                coordinates JSONB NOT NULL DEFAULT '[]',
                radius_km NUMERIC(8,2),
                base_fee_xof INTEGER NOT NULL DEFAULT 0,
                per_km_fee_xof INTEGER NOT NULL DEFAULT 0,
                estimated_minutes INTEGER,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """)

        # 0017 — payment refund columns
        await run("0017_payments_refund", """
            ALTER TABLE payments
                ADD COLUMN IF NOT EXISTS refunded_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
                ADD COLUMN IF NOT EXISTS refunded_at TIMESTAMP WITH TIME ZONE,
                ADD COLUMN IF NOT EXISTS refund_reason TEXT,
                ADD COLUMN IF NOT EXISTS refund_amount_xof INTEGER
        """)

        # Stamp alembic_version
        await run("stamp_alembic", """
            DELETE FROM alembic_version
        """)
        await run("stamp_alembic_insert", """
            INSERT INTO alembic_version (version_num)
            VALUES ('0018_fix_missing_columns')
        """)

        await db.commit()
        return {"status": "success", "steps": steps}

    except Exception as e:
        await db.rollback()
        return {
            "status": "error",
            "steps": steps,
            "error": type(e).__name__,
            "detail": str(e),
            "trace": traceback.format_exc(),
        }
