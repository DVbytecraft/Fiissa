from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.models import User
from core.exceptions import BadRequestError, ConflictError, NotFoundError

# Champs autorisés pour la mise à jour du profil via self-service
_UPDATABLE_FIELDS = {"first_name", "last_name", "avatar_url", "preferred_language", "marketing_opt_in"}


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("Utilisateur")
        return user

    async def get_by_phone(self, phone: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def ensure_email_unique(self, email: str, exclude_user_id: Optional[UUID] = None) -> None:
        """Lève ConflictError si l'email est déjà utilisé par un autre compte."""
        q = select(User).where(User.email == email)
        if exclude_user_id:
            q = q.where(User.id != exclude_user_id)
        result = await self.db.execute(q)
        if result.scalar_one_or_none():
            raise ConflictError("Cette adresse email est déjà utilisée", "email_taken")

    async def update_profile(self, user_id: UUID, data: dict) -> User:
        """
        Met à jour les champs autorisés du profil.
        Filtre les champs non autorisés pour éviter la modification de champs sensibles.
        """
        safe = {k: v for k, v in data.items() if k in _UPDATABLE_FIELDS and v is not None}
        if not safe:
            return await self.get_by_id(user_id)
        await self.db.execute(update(User).where(User.id == user_id).values(**safe))
        await self.db.flush()
        return await self.get_by_id(user_id)

    async def deactivate(self, user_id: UUID) -> None:
        await self.db.execute(
            update(User).where(User.id == user_id).values(is_active=False)
        )

    async def reactivate(self, user_id: UUID) -> None:
        await self.db.execute(
            update(User).where(User.id == user_id).values(is_active=True)
        )
