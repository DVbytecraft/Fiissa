"""
FastAPI dependencies for authentication, RBAC, and tenant resolution.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import (
    AuthenticationError,
    BadRequestError,
    CompanySuspended,
    PermissionDenied,
    TenantAccessDenied,
    TokenExpired,
)
from core.permissions import Role, has_permission
from core.security import decode_access_token

security_scheme = HTTPBearer(auto_error=False)


async def _get_active_roles(user_id: UUID, db: AsyncSession):
    from apps.users.models import UserCompanyRole

    result = await db.execute(
        select(UserCompanyRole).where(
            UserCompanyRole.user_id == user_id,
            UserCompanyRole.is_active == True,
        )
    )
    return result.scalars().all()


def _normalize_company_id(value: Optional[str]) -> Optional[UUID]:
    if not value:
        return None
    return UUID(value)


def _resolve_tenant_role(roles, company_id: Optional[UUID] = None):
    super_admin_role = next((role for role in roles if role.role == Role.SUPER_ADMIN), None)
    if super_admin_role:
        return super_admin_role, company_id

    company_roles = [role for role in roles if role.company_id]
    if company_id:
        for role in company_roles:
            if role.company_id == company_id:
                return role, company_id
        raise TenantAccessDenied()

    if not company_roles:
        return None, None

    unique_company_ids = {role.company_id for role in company_roles}
    if len(unique_company_ids) == 1:
        active_role = company_roles[0]
        return active_role, active_role.company_id

    raise BadRequestError(
        "Plusieurs entreprises sont associees a ce compte. Le header X-Company-ID est requis.",
        code="tenant_selection_required",
    )


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from apps.users.models import User

    if not credentials:
        raise AuthenticationError("Token d'authentification manquant")

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError as exc:
        if "expired" in str(exc).lower():
            raise TokenExpired()
        raise AuthenticationError("Token invalide")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token malforme")

    result = await db.execute(
        select(User).where(User.id == UUID(user_id), User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise AuthenticationError("Utilisateur introuvable ou desactive")

    # Vérification légère de suspension : si TOUTES les entreprises de l'user
    # sont suspendues, on bloque l'accès (les customers sans rôle company sont exemptés)
    user_roles = await _get_active_roles(UUID(user_id), db)
    company_ids = [r.company_id for r in user_roles if r.company_id and r.role != "super_admin"]
    if company_ids:
        from apps.companies.models import Company
        companies_result = await db.execute(
            select(Company.is_suspended).where(Company.id.in_(company_ids))
        )
        statuses = [row[0] for row in companies_result.fetchall()]
        if statuses and all(statuses):
            raise CompanySuspended()

    return user


async def get_current_user_with_role(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    roles = await _get_active_roles(current_user.id, db)
    current_user._roles = roles
    return current_user


def require_permission(permission: str):
    async def _check(
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        x_company_id: Annotated[Optional[str], Header()] = None,
    ):
        roles = await _get_active_roles(current_user.id, db)
        requested_company_id = _normalize_company_id(x_company_id)

        permitted_roles = [
            role_assignment
            for role_assignment in roles
            if has_permission(Role(role_assignment.role), permission)
        ]
        if not permitted_roles:
            raise PermissionDenied(f"Permission requise : {permission}")

        active_role, resolved_company_id = _resolve_tenant_role(
            permitted_roles, requested_company_id
        )
        if active_role:
            current_user._active_role = active_role
        current_user._roles = roles
        current_user._active_company_id = resolved_company_id
        return current_user

    return _check


def require_company_access(company_id_param: str = "company_id"):
    async def _check(
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        **kwargs,
    ):
        company_id = kwargs.get(company_id_param)
        if not company_id:
            return current_user

        roles = await _get_active_roles(current_user.id, db)
        active_role, resolved_company_id = _resolve_tenant_role(
            roles, UUID(str(company_id))
        )
        current_user._active_role = active_role
        current_user._active_company_id = resolved_company_id
        return current_user

    return _check


class TenantContext:
    def __init__(self, company_id: Optional[UUID] = None):
        self.company_id = company_id


async def _check_company_not_suspended(company_id: Optional[UUID], db: AsyncSession) -> None:
    """Lève CompanySuspended si l'entreprise est suspendue par un super-admin."""
    if not company_id:
        return
    from sqlalchemy import select as sa_select
    from apps.companies.models import Company
    result = await db.execute(sa_select(Company.is_suspended, Company.is_active).where(Company.id == company_id))
    row = result.one_or_none()
    if row and (row.is_suspended or not row.is_active):
        raise CompanySuspended()


async def get_tenant_context(
    x_company_id: Annotated[Optional[str], Header()] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    roles = await _get_active_roles(current_user.id, db)
    active_role, company_id = _resolve_tenant_role(
        roles, _normalize_company_id(x_company_id)
    )
    # Blocage immédiat si entreprise suspendue (super_admin contourne)
    if active_role and active_role.role != Role.SUPER_ADMIN:
        await _check_company_not_suspended(company_id, db)
    current_user._roles = roles
    current_user._active_role = active_role
    current_user._active_company_id = company_id
    return TenantContext(company_id=company_id)


CurrentUser = Annotated[object, Depends(get_current_user)]
DB = Annotated[AsyncSession, Depends(get_db)]
