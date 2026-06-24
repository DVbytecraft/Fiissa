from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.notifications.models import AuditLog
from apps.orders.models import Cart, CartItem, Order, OrderItem, Pickup
from apps.orders.service import OrderService
from core.database import get_db
from core.dependencies import get_current_user, get_tenant_context, TenantContext, require_permission
from core.exceptions import NotFoundError, TenantAccessDenied
from core.pagination import PaginatedResponse, PaginationParams


class AddToCartRequest(BaseModel):
    product_id: UUID
    quantity: int


class CreateOrderRequest(BaseModel):
    store_id: UUID
    company_id: UUID
    order_type: str = "click_collect"
    notes: Optional[str] = None
    delivery_address: Optional[dict] = None


class ScanGoItem(BaseModel):
    barcode: str
    quantity: int = 1


class ScanGoOrderRequest(BaseModel):
    store_id: UUID
    company_id: UUID
    items: list[ScanGoItem]
    notes: Optional[str] = None


class UpdateOrderStatusRequest(BaseModel):
    status: str
    reason: Optional[str] = None


class PickupVerifyRequest(BaseModel):
    pickup_code: str = Field(..., min_length=4, max_length=20, description="Code de retrait ou QR scan")


router = APIRouter(prefix="/orders", tags=["Commandes"])


# ------------------------------------------------------------------ #
#  PANIER                                                               #
# ------------------------------------------------------------------ #

@router.get("/cart")
async def get_cart(
    store_id: UUID = Query(...),
    company_id: UUID = Query(...),
    current_user=Depends(require_permission("cart.read")),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)
    cart = await service.get_or_create_cart(current_user.id, store_id, company_id)
    return cart


@router.post("/cart/items")
async def add_to_cart(
    data: AddToCartRequest,
    store_id: UUID = Query(...),
    company_id: UUID = Query(...),
    current_user=Depends(require_permission("cart.update")),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)
    cart = await service.add_to_cart(
        customer_id=current_user.id,
        store_id=store_id,
        company_id=company_id,
        product_id=data.product_id,
        quantity=data.quantity,
    )
    return {"message": "Panier mis à jour", "cart_id": str(cart.id)}


# ------------------------------------------------------------------ #
#  ROUTES STATIQUES MERCHANT  (avant /{order_id} pour éviter ambiguïté)
# ------------------------------------------------------------------ #

@router.get("/my")
async def get_my_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Historique des commandes du client connecté."""
    count_result = await db.execute(
        select(func.count(Order.id)).where(Order.customer_id == current_user.id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.payment), selectinload(Order.receipt))
        .where(Order.customer_id == current_user.id)
        .order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    orders = result.scalars().all()

    return PaginatedResponse.create(
        items=[
            {
                "id": str(o.id),
                "order_number": o.order_number,
                "status": o.status,
                "type": o.type,
                "total_xof": o.total_xof,
                "items_count": len(o.items),
                "created_at": o.created_at.isoformat(),
                "has_receipt": o.receipt is not None,
            }
            for o in orders
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/merchant/pending")
@router.get("/merchant/list")
async def get_merchant_orders(
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, le=100),
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("orders.read")),
    db: AsyncSession = Depends(get_db),
):
    """Liste des commandes pour le dashboard marchand."""
    query = select(Order).where(Order.company_id == ctx.company_id)
    if status:
        query = query.where(Order.status == status)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    result = await db.execute(
        query.options(selectinload(Order.items), selectinload(Order.customer))
        .order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    orders = result.scalars().all()

    return PaginatedResponse.create(
        items=[
            {
                "id": str(o.id),
                "order_number": o.order_number,
                "status": o.status,
                "type": o.type,
                "total_xof": o.total_xof,
                "customer_name": o.customer.full_name if o.customer else "Client",
                "items_count": len(o.items),
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ------------------------------------------------------------------ #
#  CRÉATION COMMANDES                                                   #
# ------------------------------------------------------------------ #

@router.post("/")
async def create_order(
    data: CreateOrderRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user=Depends(require_permission("orders.create")),
    db: AsyncSession = Depends(get_db),
):
    # Idempotency guard : si la même clé a déjà produit une commande, la retourner
    if idempotency_key:
        existing_result = await db.execute(
            select(Order).where(
                Order.idempotency_key == idempotency_key,
                Order.company_id == data.company_id,
            )
        )
        existing_order = existing_result.scalar_one_or_none()
        if existing_order:
            return {
                "id": str(existing_order.id),
                "order_number": existing_order.order_number,
                "status": existing_order.status,
                "total_xof": existing_order.total_xof,
                "type": existing_order.type,
                "order_type": existing_order.type,
                "company_id": str(existing_order.company_id),
                "idempotent": True,
            }

    service = OrderService(db)
    order = await service.create_order_from_cart(
        customer_id=current_user.id,
        store_id=data.store_id,
        company_id=data.company_id,
        order_type=data.order_type,
        notes=data.notes,
        delivery_address=data.delivery_address,
    )

    # Persister la clé d'idempotence sur la commande créée
    if idempotency_key:
        order.idempotency_key = idempotency_key
        await db.commit()

    return {
        "id": str(order.id),
        "order_number": order.order_number,
        "status": order.status,
        "total_xof": order.total_xof,
        "type": order.type,
        "order_type": order.type,
        "company_id": str(order.company_id),
    }


@router.post("/scan-go", summary="Créer une commande Scan & Go depuis barcodes scannés")
async def create_scan_go_order(
    data: ScanGoOrderRequest,
    current_user=Depends(require_permission("orders.create")),
    db: AsyncSession = Depends(get_db),
):
    """
    Flux Scan & Go : le client scanne les articles en rayon.
    Pas de panier intermédiaire — la commande est créée directement
    depuis les barcodes avec résolution catalogue automatique.
    """
    service = OrderService(db)
    order = await service.create_scan_go_order(
        customer_id=current_user.id,
        store_id=data.store_id,
        company_id=data.company_id,
        items=[{"barcode": i.barcode, "quantity": i.quantity} for i in data.items],
        notes=data.notes,
    )
    return {
        "id": str(order.id),
        "order_number": order.order_number,
        "status": order.status,
        "total_xof": order.total_xof,
        "type": order.type,
        "order_type": order.type,
        "company_id": str(order.company_id),
        "pickup_code": order.pickup_code,
        "items_count": len(order.items) if order.items else 0,
    }


# ------------------------------------------------------------------ #
#  VÉRIFICATION PICKUP (agent sécurité / préparateur)                 #
# ------------------------------------------------------------------ #

@router.post("/pickups/verify", summary="Vérifier un pickup_code (agent sécurité)")
async def verify_pickup_code(
    data: PickupVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("pickups.verify")),
):
    """
    L'agent de sécurité ou le préparateur scanne le QR/saisit le pickup_code.
    Retourne les détails de la commande et valide le retrait.
    Si le statut est 'ready', la commande est automatiquement passée à 'delivered'.
    """
    active_role = getattr(current_user, "_active_role", None)
    if not active_role or not active_role.company_id:
        raise HTTPException(status_code=403, detail="Contexte entreprise requis")

    result = await db.execute(
        select(Order)
        .where(
            Order.pickup_code == data.pickup_code.upper().strip(),
            Order.company_id == active_role.company_id,
        )
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.customer),
            selectinload(Order.pickup),
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Code de retrait invalide ou introuvable")

    if order.status not in ("ready", "confirmed", "preparing"):
        raise HTTPException(
            status_code=400,
            detail=f"Cette commande ne peut pas être retirée (statut: {order.status})",
        )

    # Audit log
    log = AuditLog(
        company_id=active_role.company_id,
        user_id=current_user.id,
        action="pickup.verified",
        resource_type="order",
        resource_id=order.id,
        new_data={"pickup_code": data.pickup_code, "order_status": order.status},
    )
    db.add(log)

    # Si statut = ready, marquer comme delivered + mettre à jour le Pickup si existant
    if order.status == "ready":
        order.status = "delivered"
        if order.pickup:
            order.pickup.status = "completed"
            order.pickup.picked_up_at = datetime.utcnow()
            order.pickup.verified_by_id = current_user.id

    await db.commit()

    return {
        "success": True,
        "order_id": str(order.id),
        "order_number": order.order_number,
        "status": order.status,
        "customer_name": order.customer.full_name if order.customer else "Client",
        "customer_phone": order.customer.phone if order.customer else None,
        "total_xof": order.total_xof,
        "items": [
            {
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price_xof": item.unit_price_xof,
            }
            for item in (order.items or [])
        ],
        "pickup_code": order.pickup_code,
        "order_type": order.type,
        "picked_up_at": order.pickup.picked_up_at.isoformat() if order.pickup and order.pickup.picked_up_at else None,
    }


# ------------------------------------------------------------------ #
#  DÉTAIL ET TRANSITIONS (routes paramétrées — en dernier)            #
# ------------------------------------------------------------------ #

@router.get("/{order_id}")
async def get_order_detail(
    order_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.payment),
            selectinload(Order.receipt),
            selectinload(Order.customer),
        )
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise NotFoundError("Commande")

    # Clients ne voient que leurs propres commandes
    if order.customer_id != current_user.id:
        from apps.users.models import UserCompanyRole
        from sqlalchemy import select as sa_select
        role_result = await db.execute(
            sa_select(UserCompanyRole).where(
                UserCompanyRole.user_id == current_user.id,
                UserCompanyRole.company_id == order.company_id,
                UserCompanyRole.is_active == True,
            )
        )
        role = role_result.scalar_one_or_none()
        if not role:
            raise TenantAccessDenied()

    return {
        "id": str(order.id),
        "order_number": order.order_number,
        "company_id": str(order.company_id),
        "store_id": str(order.store_id),
        "status": order.status,
        "type": order.type,
        "order_type": order.type,
        "subtotal_xof": order.subtotal_xof,
        "delivery_fee_xof": order.delivery_fee_xof,
        "total_xof": order.total_xof,
        "notes": order.notes,
        "pickup_code": order.pickup_code,
        "customer_name": order.customer.full_name if order.customer else None,
        "customer_phone": order.customer.phone if order.customer else None,
        "delivery_address": order.delivery_address,
        "payment_expires_at": order.payment_expires_at.isoformat() if order.payment_expires_at else None,
        "created_at": order.created_at.isoformat(),
        "items": [
            {
                "id": str(item.id),
                "product_id": str(item.product_id) if item.product_id else None,
                "product_name": item.product_name,
                "product_barcode": item.product_barcode,
                "quantity": item.quantity,
                "unit_price_xof": item.unit_price_xof,
                "subtotal_xof": item.subtotal_xof,
            }
            for item in order.items
        ],
        "payment": {
            "id": str(order.payment.id),
            "status": order.payment.status,
            "amount_xof": order.payment.amount_xof,
            "operator": order.payment.operator,
            "transaction_ref": order.payment.transaction_ref,
        } if order.payment else None,
        "receipt_id": str(order.receipt.id) if order.receipt else None,
        "receipt": {
            "id": str(order.receipt.id),
            "receipt_number": order.receipt.receipt_number,
            "pdf_url": order.receipt.pdf_url,
        } if order.receipt else None,
    }


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: UUID,
    data: UpdateOrderStatusRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("orders.update_status")),
    db: AsyncSession = Depends(get_db),
):
    """Transition de statut commande (staff seulement)."""
    from core.permissions import Role
    active_role = getattr(current_user, "_active_role", None)
    if not active_role:
        from core.exceptions import PermissionDenied
        raise PermissionDenied()

    acting_role = Role(active_role.role)
    service = OrderService(db)

    order = await service.transition_order(
        order_id=order_id,
        company_id=ctx.company_id or active_role.company_id,
        to_status=data.status,
        acting_user=current_user,
        acting_role=acting_role,
        reason=data.reason,
    )

    return {"id": str(order.id), "status": order.status, "order_number": order.order_number}
