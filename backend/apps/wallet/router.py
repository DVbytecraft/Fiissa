"""Routes wallet client Fiissa."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.wallet.schemas import (
    WalletMethodCreateRequest,
    WalletMethodResponse,
    WalletMethodUpdateRequest,
)
from apps.wallet.service import WalletService
from core.database import get_db
from core.dependencies import get_tenant_context, require_permission

router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.get("/methods", response_model=list[WalletMethodResponse])
async def list_my_wallet_methods(
    current_user=Depends(require_permission("wallet.read_own")),
    db: AsyncSession = Depends(get_db),
):
    service = WalletService(db)
    return await service.list_own(current_user.id)


@router.post("/methods", response_model=WalletMethodResponse)
async def create_wallet_method(
    data: WalletMethodCreateRequest,
    current_user=Depends(require_permission("wallet.manage_own")),
    db: AsyncSession = Depends(get_db),
):
    service = WalletService(db)
    return await service.create_own(current_user.id, data.model_dump())


@router.patch("/methods/{method_id}", response_model=WalletMethodResponse)
async def update_wallet_method(
    method_id: UUID,
    data: WalletMethodUpdateRequest,
    current_user=Depends(require_permission("wallet.manage_own")),
    db: AsyncSession = Depends(get_db),
):
    service = WalletService(db)
    return await service.update_own(
        method_id, current_user.id, data.model_dump(exclude_none=True)
    )


@router.delete("/methods/{method_id}")
async def delete_wallet_method(
    method_id: UUID,
    current_user=Depends(require_permission("wallet.manage_own")),
    db: AsyncSession = Depends(get_db),
):
    service = WalletService(db)
    await service.deactivate_own(method_id, current_user.id)
    return {"message": "Methode wallet desactivee"}


@router.get("/company-methods", response_model=list[WalletMethodResponse])
async def list_company_wallet_methods(
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("wallet.read")),
    db: AsyncSession = Depends(get_db),
):
    service = WalletService(db)
    return await service.list_for_company(tenant.company_id)
