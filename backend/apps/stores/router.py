from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
try:
    from python_slugify import slugify
except ModuleNotFoundError:
    import re

    def slugify(value: str) -> str:
        value = value.lower().strip()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        return value.strip("-")

from apps.stores.models import Store
from core.database import get_db
from core.dependencies import get_tenant_context, TenantContext, require_permission
from core.exceptions import NotFoundError

router = APIRouter(prefix="/stores", tags=["Magasins"])


class StoreCreate(BaseModel):
    company_id: UUID
    name: str
    description: Optional[str] = None
    address: Optional[dict] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    geo_lat: Optional[float] = None
    geo_lng: Optional[float] = None
    scan_go_enabled: bool = False
    delivery_enabled: bool = True
    click_collect_enabled: bool = True
    mobile_money_info: Optional[dict] = None


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[dict] = None
    phone: Optional[str] = None
    opening_hours: Optional[dict] = None
    mobile_money_info: Optional[dict] = None
    scan_go_enabled: Optional[bool] = None
    delivery_enabled: Optional[bool] = None
    click_collect_enabled: Optional[bool] = None
    delivery_fee_xof: Optional[int] = None
    free_delivery_threshold_xof: Optional[int] = None
    is_active: Optional[bool] = None


def _serialize_store(store: Store) -> dict:
    return {
        "id": str(store.id),
        "company_id": str(store.company_id),
        "name": store.name,
        "description": store.description,
        "address": store.address,
        "phone": store.phone,
        "opening_hours": store.opening_hours,
        "cover_image_url": store.cover_image_url,
        "mobile_money_info": {
            "operator": store.mobile_money_info.get("operator") if store.mobile_money_info else None,
            "number": store.mobile_money_info.get("number") if store.mobile_money_info else None,
            "account_name": store.mobile_money_info.get("account_name") if store.mobile_money_info else None,
        } if store.mobile_money_info else None,
        "delivery_fee_xof": store.delivery_fee_xof,
        "services": {
            "scan_go": store.scan_go_enabled,
            "delivery": store.delivery_enabled,
            "click_collect": store.click_collect_enabled,
        },
    }


@router.get("/nearby")
async def get_nearby_stores(
    lat: Optional[float] = Query(default=None),
    lng: Optional[float] = Query(default=None),
    limit: int = Query(default=20, le=50),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Store).where(Store.is_active == True).limit(limit))
    stores = result.scalars().all()
    return [
        {
            "id": str(store.id),
            "company_id": str(store.company_id),
            "name": store.name,
            "description": store.description,
            "cover_image_url": store.cover_image_url,
            "logo_url": store.logo_url,
            "address": store.address,
            "geo_lat": float(store.geo_lat) if store.geo_lat else None,
            "geo_lng": float(store.geo_lng) if store.geo_lng else None,
            "scan_go_enabled": store.scan_go_enabled,
            "delivery_enabled": store.delivery_enabled,
            "click_collect_enabled": store.click_collect_enabled,
        }
        for store in stores
    ]


@router.post("/")
async def create_store(
    data: StoreCreate,
    current_user=Depends(require_permission("stores.create")),
    db: AsyncSession = Depends(get_db),
):
    store = Store(slug=slugify(data.name), **data.model_dump())
    db.add(store)
    await db.flush()
    return {"id": str(store.id), "name": store.name}


@router.get("/me", summary="Mon magasin principal")
async def get_my_store(
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("stores.read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Store)
        .where(Store.company_id == ctx.company_id, Store.is_active == True)
        .limit(1)
    )
    store = result.scalar_one_or_none()
    if not store:
        raise NotFoundError("Magasin")
    return {
        "id": str(store.id),
        "name": store.name,
        "address": store.address,
        "phone": store.phone,
        "mobile_money_info": store.mobile_money_info,
        "opening_hours": store.opening_hours,
        "click_collect_enabled": store.click_collect_enabled,
        "delivery_enabled": store.delivery_enabled,
        "scan_go_enabled": store.scan_go_enabled,
        "free_delivery_threshold_xof": store.free_delivery_threshold_xof,
    }


@router.patch("/me", summary="Mettre à jour mon magasin principal")
async def update_my_store(
    data: StoreUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("stores.update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Store)
        .where(Store.company_id == ctx.company_id, Store.is_active == True)
        .limit(1)
    )
    store = result.scalar_one_or_none()
    if not store:
        raise NotFoundError("Magasin")

    for key, value in data.model_dump(exclude_none=True).items():
        setattr(store, key, value)
    return {"id": str(store.id), "message": "Magasin mis à jour"}


@router.get("/{store_id}")
async def get_store(store_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise NotFoundError("Magasin")
    return _serialize_store(store)


@router.patch("/{store_id}")
async def update_store(
    store_id: UUID,
    data: StoreUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("stores.update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Store).where(Store.id == store_id, Store.company_id == ctx.company_id)
    )
    store = result.scalar_one_or_none()
    if not store:
        raise NotFoundError("Magasin")

    for key, value in data.model_dump(exclude_none=True).items():
        setattr(store, key, value)
    return {"id": str(store.id), "message": "Magasin mis à jour"}
