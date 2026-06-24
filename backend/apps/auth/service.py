"""
Service Auth - logique d'authentification.
- Clients : email + mot de passe + OTP email
- Staff : email + mot de passe
- Refresh token rotation : chaque utilisation invalide l'ancien
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.schemas import (
    CustomerLoginRequest,
    CustomerRegisterRequest,
    OTPSentResponse,
    StaffLoginRequest,
    TokenResponse,
    UserInfo,
    VerifyOTPRequest,
)
from apps.notifications.models import AuditLog
from apps.users.models import OTPCode, RefreshToken, User, UserCompanyRole
from core.config import settings
from core.exceptions import ConflictError, InvalidCredentials, InvalidOTP, TokenExpired
from core.security import (
    create_access_token,
    create_refresh_token,
    generate_otp,
    hash_password,
    hash_token,
    otp_expires_at,
    refresh_token_expires_at,
    verify_password,
)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_customer(
        self, data: CustomerRegisterRequest, ip_address: str = ""
    ) -> OTPSentResponse:
        """Inscrit un client et démarre la vérification OTP email."""
        existing_phone = await self.db.execute(select(User).where(User.phone == data.phone))
        if existing_phone.scalar_one_or_none():
            raise ConflictError("Un compte existe déjà avec ce numéro", code="phone_taken")

        from apps.users.service import UserService

        await UserService(self.db).ensure_email_unique(str(data.email))

        user = User(
            phone=data.phone,
            email=str(data.email),
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            preferred_language=data.preferred_language,
            marketing_opt_in=data.marketing_opt_in,
            is_active=True,
            is_verified=False,
            email_verified=False,
            phone_verified=False,
        )
        self.db.add(user)
        await self.db.flush()

        self.db.add(
            UserCompanyRole(
                user_id=user.id,
                company_id=None,
                role="customer",
            )
        )

        from apps.notifications.service import EmailService

        try:
            await EmailService.send_customer_welcome(
                email=user.email,
                first_name=user.first_name,
            )
        except Exception as exc:
            logger.error("Welcome customer email not sent: %s", exc)

        return await self._send_otp(user, ip_address)

    async def request_otp(
        self, data: CustomerLoginRequest, ip_address: str = ""
    ) -> OTPSentResponse:
        """Envoie un OTP email au client après validation du mot de passe."""
        result = await self.db.execute(
            select(User).where(User.email == str(data.email), User.is_active == True)
        )
        user = result.scalar_one_or_none()
        if not user or not user.password_hash:
            raise InvalidCredentials()

        if not verify_password(data.password, user.password_hash):
            await self._log(
                action="auth.login_failed",
                user_id=user.id,
                ip_address=ip_address,
                new_data={"email": user.email, "reason": "wrong_password"},
            )
            raise InvalidCredentials()

        return await self._send_otp(user, ip_address)

    async def _send_otp(self, user: User, ip_address: str) -> OTPSentResponse:
        """Génère et envoie un OTP email."""
        await self.db.execute(
            update(OTPCode)
            .where(OTPCode.user_id == user.id, OTPCode.is_used == False)
            .values(is_used=True)
        )

        code = generate_otp(settings.OTP_LENGTH)
        self.db.add(
            OTPCode(
                user_id=user.id,
                phone=user.phone,
                email=user.email,
                code=code,
                expires_at=otp_expires_at(),
            )
        )

        from apps.notifications.service import EmailService

        await EmailService.send_login_otp(
            email=user.email,
            first_name=user.first_name,
            code=code,
        )

        await self._log(
            action="auth.otp_sent",
            user_id=user.id,
            ip_address=ip_address,
            new_data={"email": user.email},
        )

        return OTPSentResponse(
            message=f"Code envoyé à {user.email}",
            destination=user.email,
            debug_code=code if not settings.is_production else None,
        )

    async def verify_otp(
        self, data: VerifyOTPRequest, ip_address: str = ""
    ) -> TokenResponse:
        """Vérifie l'OTP email et retourne les tokens JWT."""
        result = await self.db.execute(
            select(OTPCode)
            .join(User, OTPCode.user_id == User.id)
            .where(
                OTPCode.email == str(data.email),
                OTPCode.code == data.code,
                OTPCode.is_used == False,
                User.is_active == True,
            )
            .order_by(OTPCode.created_at.desc())
        )
        otp = result.scalar_one_or_none()
        if not otp:
            raise InvalidOTP()

        now = datetime.now(timezone.utc)
        if otp.expires_at.replace(tzinfo=timezone.utc) < now:
            raise InvalidOTP()

        otp.is_used = True

        result = await self.db.execute(select(User).where(User.id == otp.user_id))
        user = result.scalar_one()
        user.is_verified = True
        user.email_verified = True
        user.last_login_at = now

        await self._log(
            action="auth.login",
            user_id=user.id,
            ip_address=ip_address,
            new_data={"method": "otp_email", "email": user.email},
        )

        return await self._create_token_response(user)

    async def staff_login(
        self, data: StaffLoginRequest, ip_address: str = ""
    ) -> TokenResponse:
        """Authentification staff par email/mot de passe."""
        result = await self.db.execute(
            select(User).where(User.email == data.email, User.is_active == True)
        )
        user = result.scalar_one_or_none()

        if not user or not user.password_hash:
            raise InvalidCredentials()

        if not verify_password(data.password, user.password_hash):
            await self._log(
                action="auth.login_failed",
                user_id=user.id if user else None,
                ip_address=ip_address,
                new_data={"email": data.email, "reason": "wrong_password"},
            )
            raise InvalidCredentials()

        user.last_login_at = datetime.now(timezone.utc)

        await self._log(
            action="auth.login",
            user_id=user.id,
            ip_address=ip_address,
            new_data={"method": "password", "email": user.email},
        )

        return await self._create_token_response(user)

    async def refresh_access_token(
        self, raw_token: str, ip_address: str = ""
    ) -> TokenResponse:
        """Rotation du refresh token : invalide l'ancien, génère un nouveau."""
        token_hash = hash_token(raw_token)

        result = await self.db.execute(
            select(RefreshToken)
            .join(User, RefreshToken.user_id == User.id)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at == None,  # noqa: E711
                User.is_active == True,
            )
        )
        token_record = result.scalar_one_or_none()

        if not token_record:
            raise TokenExpired()

        now = datetime.now(timezone.utc)
        if token_record.expires_at.replace(tzinfo=timezone.utc) < now:
            token_record.revoked_at = now
            raise TokenExpired()

        token_record.revoked_at = now

        result = await self.db.execute(select(User).where(User.id == token_record.user_id))
        user = result.scalar_one()

        await self._log(
            action="auth.token_refresh",
            user_id=user.id,
            ip_address=ip_address,
        )

        return await self._create_token_response(user)

    async def logout(self, raw_token: str, user_id: UUID) -> None:
        """Révoque le refresh token."""
        token_hash = hash_token(raw_token)
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.user_id == user_id,
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self._log(action="auth.logout", user_id=user_id)

    async def _create_token_response(self, user: User) -> TokenResponse:
        result = await self.db.execute(
            select(UserCompanyRole).where(
                UserCompanyRole.user_id == user.id,
                UserCompanyRole.is_active == True,
            )
        )
        roles = result.scalars().all()
        primary_role = self._select_primary_role(roles)

        payload = {
            "sub": str(user.id),
            "email": user.email,
            "phone": user.phone,
            "role": primary_role.role if primary_role else None,
            "company_id": str(primary_role.company_id) if primary_role and primary_role.company_id else None,
        }

        access_token = create_access_token(payload)
        raw_refresh, hashed_refresh = create_refresh_token()

        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hashed_refresh,
                expires_at=refresh_token_expires_at(),
            )
        )

        user_info = UserInfo(
            id=str(user.id),
            email=user.email,
            phone=user.phone,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            role=primary_role.role if primary_role else None,
            company_id=str(primary_role.company_id) if primary_role and primary_role.company_id else None,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_info,
        )

    def _select_primary_role(
        self, roles: list[UserCompanyRole]
    ) -> Optional[UserCompanyRole]:
        if not roles:
            return None

        staff_roles = [role for role in roles if role.role != "customer"]
        if len(staff_roles) == 1:
            return staff_roles[0]
        if len(staff_roles) > 1:
            company_ids = {str(role.company_id) for role in staff_roles if role.company_id}
            if len(company_ids) == 1:
                return staff_roles[0]
            return None
        return roles[0]

    async def _log(
        self,
        action: str,
        user_id: Optional[UUID] = None,
        ip_address: str = "",
        old_data: Optional[dict] = None,
        new_data: Optional[dict] = None,
    ) -> None:
        self.db.add(
            AuditLog(
                user_id=user_id,
                action=action,
                resource_type="auth",
                ip_address=ip_address,
                old_data=old_data,
                new_data=new_data,
            )
        )
