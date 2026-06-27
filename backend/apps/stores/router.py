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

from apps.stores.models import Store, DeliveryZone
from core.database import get_db
from core.dependencies import get_tenant_context, TenantContext, require_permission
from core.exceptions import BadRequestError, NotFoundError

router = APIRouter(prefix="/stores", tags=["Magasins"])


class MobileMoneyInfo(BaseModel):
    operator: str
    number: str
    account_name: Optional[str] = None


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
    mobile_money_info: Optional[MobileMoneyInfo] = None


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[dict] = None
    phone: Optional[str] = None
    opening_hours: Optional[dict] = None
    mobile_money_info: Optional[MobileMoneyInfo] = None
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
    result = await db.execute(select(Store).where(Store.is_active).limit(limit))
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
        .where(Store.company_id == ctx.company_id, Store.is_active)
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
        .where(Store.company_id == ctx.company_id, Store.is_active)
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


# ── Zones de livraison ────────────────────────────────────────────────────────

class DeliveryZoneCreate(BaseModel):
    name: str
    description: Optional[str] = None
    delivery_fee_xof: int = 0
    free_delivery_threshold_xof: Optional[int] = None
    estimated_minutes: Optional[int] = None
    is_active: bool = True


class DeliveryZoneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    delivery_fee_xof: Optional[int] = None
    free_delivery_threshold_xof: Optional[int] = None
    estimated_minutes: Optional[int] = None
    is_active: Optional[bool] = None


def _serialize_zone(zone: DeliveryZone) -> dict:
    return {
        "id": str(zone.id),
        "store_id": str(zone.store_id),
        "name": zone.name,
        "description": zone.description,
        "delivery_fee_xof": zone.delivery_fee_xof,
        "free_delivery_threshold_xof": zone.free_delivery_threshold_xof,
        "estimated_minutes": zone.estimated_minutes,
        "is_active": zone.is_active,
    }


@router.get("/{store_id}/delivery-zones", summary="Zones de livraison d'un magasin")
async def list_delivery_zones(
    store_id: UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("stores.read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Store).where(Store.id == store_id, Store.company_id == ctx.company_id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Magasin")

    zones_result = await db.execute(
        select(DeliveryZone)
        .where(DeliveryZone.store_id == store_id, DeliveryZone.company_id == ctx.company_id)
        .order_by(DeliveryZone.delivery_fee_xof)
    )
    zones = zones_result.scalars().all()
    return {"items": [_serialize_zone(z) for z in zones]}


@router.post("/{store_id}/delivery-zones", summary="Créer une zone de livraison")
async def create_delivery_zone(
    store_id: UUID,
    data: DeliveryZoneCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("stores.update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Store).where(Store.id == store_id, Store.company_id == ctx.company_id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Magasin")

    if data.delivery_fee_xof < 0:
        raise BadRequestError("Les frais de livraison ne peuvent pas être négatifs.")

    zone = DeliveryZone(
        store_id=store_id,
        company_id=ctx.company_id,
        **data.model_dump(),
    )
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return _serialize_zone(zone)


@router.patch("/{store_id}/delivery-zones/{zone_id}", summary="Mettre à jour une zone de livraison")
async def update_delivery_zone(
    store_id: UUID,
    zone_id: UUID,
    data: DeliveryZoneUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("stores.update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DeliveryZone).where(
            DeliveryZone.id == zone_id,
            DeliveryZone.store_id == store_id,
            DeliveryZone.company_id == ctx.company_id,
        )
    )
    zone = result.scalar_one_or_none()
    if not zone:
        raise NotFoundError("Zone de livraison")

    update_data = data.model_dump(exclude_none=True)
    if "delivery_fee_xof" in update_data and update_data["delivery_fee_xof"] < 0:
        raise BadRequestError("Les frais de livraison ne peuvent pas être négatifs.")

    for field, value in update_data.items():
        setattr(zone, field, value)

    await db.commit()
    await db.refresh(zone)
    return _serialize_zone(zone)


@router.delete("/{store_id}/delivery-zones/{zone_id}", summary="Supprimer une zone de livraison")
async def delete_delivery_zone(
    store_id: UUID,
    zone_id: UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("stores.update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DeliveryZone).where(
            DeliveryZone.id == zone_id,
            DeliveryZone.store_id == store_id,
            DeliveryZone.company_id == ctx.company_id,
        )
    )
    zone = result.scalar_one_or_none()
    if not zone:
        raise NotFoundError("Zone de livraison")

    await db.delete(zone)
    await db.commit()
    return {"id": str(zone_id), "message": "Zone de livraison supprimée"}
