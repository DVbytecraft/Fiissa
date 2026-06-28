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
