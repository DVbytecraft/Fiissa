"""
IdentityService — Vérification email et réinitialisation de mot de passe.

Règles de sécurité :
- Tokens : secrets.token_urlsafe(32), stockés en SHA-256, usage unique.
- Password reset : ne révèle jamais si l'email existe (anti-énumération).
- TTL court pour password reset (15 min), plus long pour email verification (24h).
- Tout token expiré ou déjà utilisé est rejeté silencieusement avec le même code d'erreur.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.models import EmailVerificationToken, PasswordResetToken, User
from core.exceptions import BadRequestError, NotFoundError, ValidationError
from core.security import hash_password, hash_token


_INVALID_TOKEN_MSG = "Token invalide ou expiré"
_INVALID_TOKEN_CODE = "invalid_or_expired_token"


class EmailVerificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def request_verification(self, user_id: UUID) -> str:
        """
        Génère un token de vérification pour l'email de l'utilisateur.
        Invalide les tokens précédents. Retourne le raw token (pour l'email).
        """
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("Utilisateur")
        if not user.email:
            raise BadRequestError(
                "Cet utilisateur n'a pas d'adresse email", "no_email"
            )
        if user.email_verified:
            raise BadRequestError("Email déjà vérifié", "email_already_verified")

        # Invalider les tokens existants non utilisés
        await self.db.execute(
            update(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.is_used == False,  # noqa: E712
            )
            .values(is_used=True)
        )

        raw_token = secrets.token_urlsafe(32)
        self.db.add(
            EmailVerificationToken(
                id=uuid4(),
                user_id=user_id,
                token_hash=hash_token(raw_token),
                expires_at=datetime.now(timezone.utc)
                + timedelta(hours=24),
            )
        )
        return raw_token

    async def verify_email(self, raw_token: str) -> User:
        """
        Vérifie l'email à partir du token. Marque email_verified = True.
        Lève BadRequestError si token invalide, expiré ou déjà utilisé.
        """
        token = await self._get_valid_token(
            EmailVerificationToken, hash_token(raw_token)
        )

        token.is_used = True
        await self.db.execute(
            update(User)
            .where(User.id == token.user_id)
            .values(email_verified=True)
        )
        await self.db.flush()

        result = await self.db.execute(select(User).where(User.id == token.user_id))
        return result.scalar_one()

    async def _get_valid_token(self, model, token_hash: str):
        result = await self.db.execute(
            select(model).where(
                model.token_hash == token_hash,
                model.is_used == False,  # noqa: E712
            )
        )
        token = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if not token or token.expires_at.replace(tzinfo=timezone.utc) < now:
            raise BadRequestError(_INVALID_TOKEN_MSG, _INVALID_TOKEN_CODE)
        return token


class PasswordResetService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def request_reset(self, email: str) -> Optional[tuple[User, str]]:
        """
        Génère un token de réinitialisation pour l'email donné.
        Retourne (user, raw_token) si l'email existe et est actif, None sinon.
        L'appelant NE DOIT PAS révéler si l'email existe (anti-énumération).
        """
        result = await self.db.execute(
            select(User).where(User.email == email, User.is_active == True)  # noqa: E712
        )
        user = result.scalar_one_or_none()
        if not user:
            return None

        # Invalider les tokens précédents
        await self.db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.is_used == False,  # noqa: E712
            )
            .values(is_used=True)
        )

        raw_token = secrets.token_urlsafe(32)
        self.db.add(
            PasswordResetToken(
                id=uuid4(),
                user_id=user.id,
                token_hash=hash_token(raw_token),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            )
        )
        return user, raw_token

    async def reset_password(self, raw_token: str, new_password: str) -> User:
        """
        Réinitialise le mot de passe avec le token. Token usage unique.
        Lève ValidationError si mot de passe trop court.
        Lève BadRequestError si token invalide, expiré ou déjà utilisé.
        """
        if len(new_password) < 8:
            raise ValidationError(
                "Le mot de passe doit contenir au moins 8 caractères"
            )

        result = await self.db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == hash_token(raw_token),
                PasswordResetToken.is_used == False,  # noqa: E712
            )
        )
        token = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if not token or token.expires_at.replace(tzinfo=timezone.utc) < now:
            raise BadRequestError(_INVALID_TOKEN_MSG, _INVALID_TOKEN_CODE)

        token.is_used = True
        await self.db.execute(
            update(User)
            .where(User.id == token.user_id)
            .values(password_hash=hash_password(new_password))
        )
        await self.db.flush()

        result = await self.db.execute(select(User).where(User.id == token.user_id))
        return result.scalar_one()
