#!/usr/bin/env python3
"""
Idempotent superadmin seeding. Run after Alembic migrations.
Creates the SUPERADMIN user if it doesn't exist.
"""

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from core.config import settings
from core.security import hash_password
from apps.users.models import User, UserCompanyRole


async def seed() -> None:
    if not settings.SUPERADMIN_EMAIL or not settings.SUPERADMIN_PASSWORD:
        print("[seed_superadmin] SUPERADMIN_EMAIL/PASSWORD not set — skipping")
        return

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as db:
            result = await db.execute(
                select(User).where(User.email == settings.SUPERADMIN_EMAIL)
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"[seed_superadmin] Super-admin already exists: {settings.SUPERADMIN_EMAIL}")
                return

            user = User(
                email=settings.SUPERADMIN_EMAIL,
                phone=settings.SUPERADMIN_PHONE if settings.SUPERADMIN_PHONE else None,
                password_hash=hash_password(settings.SUPERADMIN_PASSWORD),
                first_name="Super",
                last_name="Admin",
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
            print(f"[seed_superadmin] Super-admin created: {settings.SUPERADMIN_EMAIL}")

    except Exception as exc:
        print(f"[seed_superadmin] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
