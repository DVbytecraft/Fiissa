"""
Promotions — CRUD marchand + validation code côté client.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.promotions.models import Promotion
from core.database import get_db
from core.dependencies import TenantContext, get_tenant_context, require_permission
from core.exceptions import BadRequestError, NotFoundError

router = APIRouter(prefix="/promotions", tags=["Promotions"])


# ── Schémas ─────────────────────────────────────────────────────────────────

class PromotionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    code: Optional[str] = None
    type: str
    value: int
    applies_to: str = "all"
    target_ids: Optional[list[str]] = None
    min_order_xof: Optional[int] = None
    max_uses: Optional[int] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    is_active: bool = True
    stackable: bool = False


class PromotionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    value: Optional[int] = None
    applies_to: Optional[str] = None
    target_ids: Optional[list[str]] = None
    min_order_xof: Optional[int] = None
    max_uses: Optional[int] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    stackable: Optional[bool] = None


def _validate_promotion_data(type_: str, value: int, applies_to: str) -> None:
    if type_ not in ("percentage", "fixed", "bogo"):
        raise BadRequestError("Type de promotion invalide. Valeurs : percentage, fixed, bogo.")
    if type_ == "percentage" and not (1 <= value <= 100):
        raise BadRequestError("Une réduction en % doit être comprise entre 1 et 100.")
    if type_ in ("fixed", "bogo") and value < 1:
        raise BadRequestError("La valeur de la promotion doit être ≥ 1.")
    if applies_to not in ("all", "category", "product"):
        raise BadRequestError("applies_to invalide. Valeurs : all, category, product.")


def _serialize(p: Promotion) -> dict:
    return {
        "id": str(p.id),
        "name": p.name,
        "description": p.description,
        "code": p.code,
        "type": p.type,
        "value": p.value,
        "applies_to": p.applies_to,
        "target_ids": p.target_ids,
        "min_order_xof": p.min_order_xof,
        "max_uses": p.max_uses,
        "uses_count": p.uses_count,
        "start_at": p.start_at.isoformat() if p.start_at else None,
        "end_at": p.end_at.isoformat() if p.end_at else None,
        "is_active": p.is_active,
        "stackable": p.stackable,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


# ── Endpoints marchand ───────────────────────────────────────────────────────

@router.get("/", summary="Lister les promotions")
async def list_promotions(
    active_only: bool = Query(default=False),
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("promotions.read")),
    db: AsyncSession = Depends(get_db),
):
    query = select(Promotion).where(Promotion.company_id == ctx.company_id)
    if active_only:
        query = query.where(Promotion.is_active)
    query = query.order_by(Promotion.created_at.desc())
    result = await db.execute(query)
    promos = result.scalars().all()
    return {"items": [_serialize(p) for p in promos], "total": len(promos)}


@router.post("/", summary="Créer une promotion")
async def create_promotion(
    data: PromotionCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("promotions.create")),
    db: AsyncSession = Depends(get_db),
):
    _validate_promotion_data(data.type, data.value, data.applies_to)

    # Vérifier l'unicité du code pour cette entreprise
    if data.code:
        existing = await db.execute(
            select(Promotion).where(
                Promotion.company_id == ctx.company_id,
                Promotion.code == data.code.upper(),
            )
        )
        if existing.scalar_one_or_none():
            raise BadRequestError(f"Le code '{data.code.upper()}' existe déjà pour cette entreprise.")

    promo = Promotion(
        company_id=ctx.company_id,
        name=data.name,
        description=data.description,
        code=data.code.upper() if data.code else None,
        type=data.type,
        value=data.value,
        applies_to=data.applies_to,
        target_ids=data.target_ids,
        min_order_xof=data.min_order_xof,
        max_uses=data.max_uses,
        start_at=data.start_at,
        end_at=data.end_at,
        is_active=data.is_active,
        stackable=data.stackable,
    )
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    return _serialize(promo)


@router.get("/{promotion_id}", summary="Détail d'une promotion")
async def get_promotion(
    promotion_id: UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("promotions.read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Promotion).where(
            Promotion.id == promotion_id,
            Promotion.company_id == ctx.company_id,
        )
    )
    promo = result.scalar_one_or_none()
    if not promo:
        raise NotFoundError("Promotion")
    return _serialize(promo)


@router.patch("/{promotion_id}", summary="Mettre à jour une promotion")
async def update_promotion(
    promotion_id: UUID,
    data: PromotionUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("promotions.update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Promotion).where(
            Promotion.id == promotion_id,
            Promotion.company_id == ctx.company_id,
        )
    )
    promo = result.scalar_one_or_none()
    if not promo:
        raise NotFoundError("Promotion")

    update_data = data.model_dump(exclude_none=True)
    if "type" in update_data or "value" in update_data or "applies_to" in update_data:
        _validate_promotion_data(
            update_data.get("type", promo.type),
            update_data.get("value", promo.value),
            update_data.get("applies_to", promo.applies_to),
        )
    if "code" in update_data and update_data["code"]:
        update_data["code"] = update_data["code"].upper()
        existing = await db.execute(
            select(Promotion).where(
                Promotion.company_id == ctx.company_id,
                Promotion.code == update_data["code"],
                Promotion.id != promotion_id,
            )
        )
        if existing.scalar_one_or_none():
            raise BadRequestError(f"Le code '{update_data['code']}' est déjà utilisé.")

    for field, value in update_data.items():
        setattr(promo, field, value)

    await db.commit()
    await db.refresh(promo)
    return _serialize(promo)


@router.delete("/{promotion_id}", summary="Désactiver une promotion")
async def deactivate_promotion(
    promotion_id: UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("promotions.delete")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Promotion).where(
            Promotion.id == promotion_id,
            Promotion.company_id == ctx.company_id,
        )
    )
    promo = result.scalar_one_or_none()
    if not promo:
        raise NotFoundError("Promotion")
    promo.is_active = False
    await db.commit()
    return {"message": "Promotion désactivée"}


# ── Validation code côté client ─────────────────────────────────────────────

class ValidateCodeRequest(BaseModel):
    code: str
    order_subtotal_xof: int
    company_id: UUID


@router.post("/validate-code", summary="Valider un code promo (client)", include_in_schema=True)
async def validate_promotion_code(
    data: ValidateCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Valide un code promo et retourne le montant de réduction calculé.
    N'applique pas encore la promotion — c'est fait au checkout.
    """
    result = await db.execute(
        select(Promotion).where(
            Promotion.company_id == data.company_id,
            Promotion.code == data.code.upper(),
            Promotion.is_active,
        )
    )
    promo = result.scalar_one_or_none()
    if not promo:
        raise BadRequestError("Code promo invalide ou expiré.")

    now = datetime.now(timezone.utc)
    if promo.start_at and now < promo.start_at:
        raise BadRequestError("Ce code promo n'est pas encore actif.")
    if promo.end_at and now > promo.end_at:
        raise BadRequestError("Ce code promo a expiré.")
    if promo.max_uses and promo.uses_count >= promo.max_uses:
        raise BadRequestError("Ce code promo a atteint sa limite d'utilisation.")
    if promo.min_order_xof and data.order_subtotal_xof < promo.min_order_xof:
        raise BadRequestError(
            f"Commande minimum requise : {promo.min_order_xof} XOF "
            f"(votre panier : {data.order_subtotal_xof} XOF)."
        )

    discount = _compute_discount(promo, data.order_subtotal_xof)
    return {
        "valid": True,
        "promotion_id": str(promo.id),
        "promotion_name": promo.name,
        "type": promo.type,
        "value": promo.value,
        "discount_xof": discount,
        "final_total_xof": max(0, data.order_subtotal_xof - discount),
    }


def _compute_discount(promo: Promotion, subtotal_xof: int) -> int:
    """Calcule la remise en XOF. Le résultat ne peut pas dépasser le sous-total."""
    if promo.type == "percentage":
        discount = int(subtotal_xof * promo.value / 100)
    elif promo.type == "fixed":
        discount = promo.value
    else:
        # bogo: la valeur représente le % offert sur les articles éligibles
        discount = int(subtotal_xof * promo.value / 100)
    return min(discount, subtotal_xof)


async def apply_promotion_to_order(
    db: AsyncSession,
    order,
    promotion_id: UUID,
    promotion_code: Optional[str],
    company_id: UUID,
) -> int:
    """
    Applique la promotion à une commande et incrémente le compteur d'utilisation.
    Retourne le montant de réduction appliqué (XOF).
    Appelé depuis orders/router.py lors du checkout.
    """
    result = await db.execute(
        select(Promotion).where(
            Promotion.id == promotion_id,
            Promotion.company_id == company_id,
            Promotion.is_active,
        )
    )
    promo = result.scalar_one_or_none()
    if not promo:
        raise BadRequestError("Promotion invalide ou inactive.")

    now = datetime.now(timezone.utc)
    if promo.end_at and now > promo.end_at:
        raise BadRequestError("Ce code promo a expiré.")
    if promo.max_uses and promo.uses_count >= promo.max_uses:
        raise BadRequestError("Ce code promo a atteint sa limite d'utilisation.")

    discount = _compute_discount(promo, order.subtotal_xof)
    order.discount_xof = discount
    order.total_xof = max(0, order.subtotal_xof + order.delivery_fee_xof - discount)
    order.promotion_id = promo.id
    order.promotion_code = promotion_code or promo.code

    promo.uses_count += 1
    return discount
