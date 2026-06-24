"""Services wallet client Fiissa."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.wallet.models import WalletPaymentMethod
from core.exceptions import BadRequestError, NotFoundError, TenantAccessDenied


class WalletService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_own(self, customer_id: UUID) -> list[WalletPaymentMethod]:
        result = await self.db.execute(
            select(WalletPaymentMethod)
            .where(WalletPaymentMethod.customer_id == customer_id)
            .order_by(WalletPaymentMethod.is_default.desc(), WalletPaymentMethod.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_for_company(self, company_id: UUID) -> list[WalletPaymentMethod]:
        result = await self.db.execute(
            select(WalletPaymentMethod)
            .where(WalletPaymentMethod.company_id == company_id)
            .order_by(WalletPaymentMethod.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_own(self, customer_id: UUID, data: dict) -> WalletPaymentMethod:
        method_type = data["method_type"]
        if method_type in {"bank_card", "bank_account"}:
            raise BadRequestError(
                "Cette methode est prevue mais desactivee en V1",
                code="wallet_method_disabled",
            )

        if data.get("is_default"):
            await self._clear_default_methods(customer_id, data.get("company_id"))

        method = WalletPaymentMethod(
            customer_id=customer_id,
            company_id=data.get("company_id"),
            method_type=method_type,
            operator=data.get("operator"),
            phone_number=data.get("phone_number"),
            display_name=data["display_name"],
            is_default=data.get("is_default", False),
            metadata_=data.get("metadata"),
        )
        self.db.add(method)
        await self.db.flush()
        await self.db.refresh(method)
        return method

    async def update_own(
        self, method_id: UUID, customer_id: UUID, data: dict
    ) -> WalletPaymentMethod:
        method = await self.get_own(method_id, customer_id)

        if data.get("is_default") is True:
            await self._clear_default_methods(customer_id, method.company_id)

        for key, value in data.items():
            if key == "metadata":
                method.metadata_ = value
            elif value is not None:
                setattr(method, key, value)

        await self.db.flush()
        await self.db.refresh(method)
        return method

    async def get_own(self, method_id: UUID, customer_id: UUID) -> WalletPaymentMethod:
        result = await self.db.execute(
            select(WalletPaymentMethod).where(WalletPaymentMethod.id == method_id)
        )
        method = result.scalar_one_or_none()
        if not method:
            raise NotFoundError("Methode wallet")
        if method.customer_id != customer_id:
            raise TenantAccessDenied()
        return method

    async def deactivate_own(self, method_id: UUID, customer_id: UUID) -> None:
        method = await self.get_own(method_id, customer_id)
        method.is_active = False
        method.is_default = False
        await self.db.flush()

    async def _clear_default_methods(
        self, customer_id: UUID, company_id: Optional[UUID]
    ) -> None:
        await self.db.execute(
            update(WalletPaymentMethod)
            .where(
                WalletPaymentMethod.customer_id == customer_id,
                WalletPaymentMethod.company_id == company_id,
            )
            .values(is_default=False)
        )
