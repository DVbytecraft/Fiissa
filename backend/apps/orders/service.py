"""
OrderService — Logique commandes avec machine à états et réservation de stock.
Toute action sensible crée un audit log.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.catalog.models import Product, StockMovement
from apps.orders.models import (
    Cart, CartItem, Delivery, Order, OrderItem, OrderQRCode, Pickup,
)
from apps.users.models import User
from core.config import settings
from core.exceptions import (
    BadRequestError,
    InsufficientStock,
    InvalidOrderTransition,
    NotFoundError,
    OrderNotCancellable,
    ProductNotAvailable,
    TenantAccessDenied,
)
from apps.notifications.service import AuditService, NotificationCenterService
from core.permissions import Role, can_transition_order
from core.security import generate_pickup_code, generate_verification_code


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------ #
    #  PANIER                                                               #
    # ------------------------------------------------------------------ #

    async def get_or_create_cart(
        self, customer_id: UUID, store_id: UUID, company_id: UUID, order_type: str = "click_collect"
    ) -> Cart:
        result = await self.db.execute(
            select(Cart)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
            .where(
                Cart.customer_id == customer_id,
                Cart.store_id == store_id,
                Cart.company_id == company_id,
            )
        )
        cart = result.scalar_one_or_none()
        if not cart:
            cart = Cart(
                customer_id=customer_id,
                store_id=store_id,
                company_id=company_id,
                type=order_type,
            )
            cart.items = []
            self.db.add(cart)
            await self.db.flush()
        return cart

    async def add_to_cart(
        self,
        customer_id: UUID,
        store_id: UUID,
        company_id: UUID,
        product_id: UUID,
        quantity: int,
    ) -> Cart:
        """Ajoute ou met à jour un produit dans le panier."""
        product = await self._get_product_or_fail(product_id, company_id)
        if not product.is_available or product.is_deleted:
            raise ProductNotAvailable(product.name)

        cart = await self.get_or_create_cart(customer_id, store_id, company_id)

        # Vérifier si l'item existe déjà
        result = await self.db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.product_id == product_id,
            )
        )
        item = result.scalar_one_or_none()

        if quantity <= 0:
            if item:
                await self.db.delete(item)
        elif item:
            item.quantity = quantity
            item.unit_price_xof = product.price_xof
        else:
            item = CartItem(
                cart_id=cart.id,
                product_id=product_id,
                quantity=quantity,
                unit_price_xof=product.price_xof,
            )
            self.db.add(item)

        await self.db.flush()
        return cart

    async def clear_cart(self, customer_id: UUID, store_id: UUID, company_id: UUID) -> None:
        cart = await self.get_or_create_cart(customer_id, store_id, company_id)
        for item in cart.items:
            await self.db.delete(item)

    # ------------------------------------------------------------------ #
    #  COMMANDE                                                             #
    # ------------------------------------------------------------------ #

    async def create_order_from_cart(
        self,
        customer_id: UUID,
        store_id: UUID,
        company_id: UUID,
        order_type: str,
        notes: Optional[str] = None,
        delivery_address: Optional[dict] = None,
    ) -> Order:
        """
        Crée une commande depuis le panier.
        - Vérifie la disponibilité et le stock de chaque produit
        - Réserve le stock (stock_reserved ++)
        - Génère le numéro de commande
        """
        cart = await self.get_or_create_cart(customer_id, store_id, company_id)

        if not cart.items:
            raise BadRequestError("Le panier est vide")

        # Vérification produits + stock
        order_items_data = []
        subtotal = 0

        for cart_item in cart.items:
            product = await self._get_product_or_fail(cart_item.product_id, company_id)

            if not product.is_available or product.is_deleted:
                raise ProductNotAvailable(product.name)

            if product.track_stock:
                available = product.stock_quantity - product.stock_reserved
                if available < cart_item.quantity:
                    raise InsufficientStock(product.name, available)

            item_subtotal = product.price_xof * cart_item.quantity
            subtotal += item_subtotal

            order_items_data.append({
                "product": product,
                "quantity": cart_item.quantity,
                "unit_price_xof": product.price_xof,  # snapshot du prix actuel
                "subtotal_xof": item_subtotal,
            })

        # Récupérer le magasin pour les frais de livraison
        from apps.stores.models import Store
        result = await self.db.execute(select(Store).where(Store.id == store_id))
        store = result.scalar_one()

        delivery_fee = 0
        if order_type == "delivery":
            if store.free_delivery_threshold_xof and subtotal >= store.free_delivery_threshold_xof:
                delivery_fee = 0
            else:
                delivery_fee = store.delivery_fee_xof or 0

        total = subtotal + delivery_fee
        order_number = await self._generate_order_number(company_id)

        order = Order(
            company_id=company_id,
            store_id=store_id,
            customer_id=customer_id,
            order_number=order_number,
            type=order_type,
            status="pending",
            subtotal_xof=subtotal,
            delivery_fee_xof=delivery_fee,
            total_xof=total,
            notes=notes,
            delivery_address=delivery_address,
            payment_expires_at=datetime.now(timezone.utc) + timedelta(
                minutes=settings.PAYMENT_MANUAL_TIMEOUT_MINUTES
            ),
        )

        if order_type == "click_collect":
            order.pickup_code = generate_pickup_code()

        self.db.add(order)
        await self.db.flush()

        # Créer les items + réserver le stock
        for item_data in order_items_data:
            product = item_data["product"]

            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                product_barcode=product.barcode,
                unit_price_xof=item_data["unit_price_xof"],
                quantity=item_data["quantity"],
                subtotal_xof=item_data["subtotal_xof"],
            )
            self.db.add(order_item)

            # Réserver le stock
            if product.track_stock:
                await self._reserve_stock(
                    product=product,
                    quantity=item_data["quantity"],
                    order_id=order.id,
                    company_id=company_id,
                    user_id=customer_id,
                )

        # Créer Pickup ou Delivery record
        if order_type == "click_collect":
            pickup = Pickup(
                company_id=company_id,
                order_id=order.id,
                pickup_code=order.pickup_code,
            )
            self.db.add(pickup)
        elif order_type == "delivery" and delivery_address:
            delivery = Delivery(
                company_id=company_id,
                order_id=order.id,
                address=delivery_address,
            )
            self.db.add(delivery)

        # QR Code pour la commande
        qr = OrderQRCode(
            company_id=company_id,
            order_id=order.id,
            code=generate_verification_code(16),
            type="pickup" if order_type == "click_collect" else "receipt",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self.db.add(qr)

        # Vider le panier
        await self.clear_cart(customer_id, store_id, company_id)

        # Log
        await self._log(
            action="order.created",
            company_id=company_id,
            user_id=customer_id,
            resource_type="order",
            resource_id=order.id,
            new_data={"order_number": order_number, "total": total, "type": order_type},
        )
        await NotificationCenterService(self.db).emit_event(
            event_key="order.created",
            company_id=company_id,
            resource_type="order",
            resource_id=order.id,
            payload={"order_number": order.order_number, "total_xof": order.total_xof},
            target_user_id=customer_id,
        )

        return order

    # ------------------------------------------------------------------ #
    #  TRANSITIONS D'ÉTAT                                                   #
    # ------------------------------------------------------------------ #

    async def transition_order(
        self,
        order_id: UUID,
        company_id: UUID,
        to_status: str,
        acting_user: User,
        acting_role: Role,
        reason: Optional[str] = None,
    ) -> Order:
        """
        Applique une transition de statut validée par la machine à états.
        """
        order = await self._get_order_or_fail(order_id, company_id)
        from_status = order.status

        if not can_transition_order(acting_role, from_status, to_status):
            raise InvalidOrderTransition(from_status, to_status)

        old_status = order.status
        order.status = to_status
        now = datetime.now(timezone.utc)

        # Actions spécifiques par transition
        if to_status == "preparing":
            order.prepared_by_id = acting_user.id

        elif to_status == "ready":
            order.prepared_at = now

        elif to_status in ("cancelled", "refunded"):
            if from_status not in ("draft", "pending", "awaiting_payment", "payment_submitted"):
                # Libérer le stock réservé
                await self._release_stock_for_order(order, company_id)
            order.cancelled_by_id = acting_user.id
            order.cancelled_at = now
            order.cancelled_reason = reason

        elif to_status == "delivered":
            # Décrémenter le stock réellement vendu
            await self._confirm_stock_for_order(order, company_id, acting_user.id)

        await self._log(
            action=f"order.status.{to_status}",
            company_id=company_id,
            user_id=acting_user.id,
            resource_type="order",
            resource_id=order.id,
            old_data={"status": old_status},
            new_data={"status": to_status, "reason": reason},
        )

        if to_status == "ready":
            await NotificationCenterService(self.db).emit_event(
                event_key="order.ready",
                company_id=company_id,
                resource_type="order",
                resource_id=order.id,
                payload={"order_number": order.order_number, "status": to_status},
                target_user_id=order.customer_id,
            )
            await self._send_order_email_ready(order)
        elif to_status == "cancelled":
            await NotificationCenterService(self.db).emit_event(
                event_key="order.cancelled",
                company_id=company_id,
                resource_type="order",
                resource_id=order.id,
                payload={"order_number": order.order_number, "status": to_status, "reason": reason},
                target_user_id=order.customer_id,
            )
            await self._send_order_email_cancelled(order, reason)

        return order

    async def _send_order_email_ready(self, order: Order) -> None:
        result = await self.db.execute(select(User).where(User.id == order.customer_id))
        customer = result.scalar_one_or_none()
        if not customer or not customer.email:
            return
        from apps.notifications.service import EmailService
        from apps.stores.models import Store
        store_result = await self.db.execute(select(Store).where(Store.id == order.store_id))
        store = store_result.scalar_one_or_none()
        try:
            await EmailService.send_order_ready(
                email=customer.email,
                customer_name=customer.full_name,
                order_number=order.order_number,
                pickup_code=order.pickup_code,
                store_name=store.name if store else None,
            )
        except Exception as exc:
            logger.error("Order ready email not sent: %s", exc)

    async def _send_order_email_cancelled(self, order: Order, reason: Optional[str]) -> None:
        result = await self.db.execute(select(User).where(User.id == order.customer_id))
        customer = result.scalar_one_or_none()
        if not customer or not customer.email:
            return
        from apps.notifications.service import EmailService
        try:
            await EmailService.send_order_cancelled(
                email=customer.email,
                customer_name=customer.full_name,
                order_number=order.order_number,
                reason=reason,
            )
        except Exception as exc:
            logger.error("Order cancelled email not sent: %s", exc)

    # ------------------------------------------------------------------ #
    #  STOCK                                                                #
    # ------------------------------------------------------------------ #

    async def _reserve_stock(
        self,
        product: Product,
        quantity: int,
        order_id: UUID,
        company_id: UUID,
        user_id: UUID,
    ) -> None:
        """Réserve du stock de manière atomique via SELECT FOR UPDATE pour éviter les race conditions."""
        # Re-fetch avec verrou exclusif pour éliminer la race condition
        result = await self.db.execute(
            select(Product)
            .where(Product.id == product.id)
            .with_for_update()
        )
        locked_product = result.scalar_one_or_none()
        if not locked_product:
            raise NotFoundError("Produit")

        available = locked_product.stock_quantity - locked_product.stock_reserved
        if available < quantity:
            raise InsufficientStock(locked_product.name, available)

        before = locked_product.stock_reserved
        locked_product.stock_reserved += quantity
        movement = StockMovement(
            company_id=company_id,
            product_id=locked_product.id,
            order_id=order_id,
            type="reservation",
            quantity_change=quantity,
            quantity_before=before,
            quantity_after=locked_product.stock_reserved,
            created_by_id=user_id,
            notes=f"Réservation commande",
        )
        self.db.add(movement)

    async def _release_stock_for_order(self, order: Order, company_id: UUID) -> None:
        """Libère le stock réservé lors d'une annulation."""
        result = await self.db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        items = result.scalars().all()

        for item in items:
            if not item.product_id:
                continue
            result = await self.db.execute(
                select(Product).where(Product.id == item.product_id)
            )
            product = result.scalar_one_or_none()
            if product and product.track_stock:
                before = product.stock_reserved
                product.stock_reserved = max(0, product.stock_reserved - item.quantity)
                movement = StockMovement(
                    company_id=company_id,
                    product_id=product.id,
                    order_id=order.id,
                    type="reservation_release",
                    quantity_change=-item.quantity,
                    quantity_before=before,
                    quantity_after=product.stock_reserved,
                    notes="Libération stock — annulation commande",
                )
                self.db.add(movement)

    async def _confirm_stock_for_order(
        self, order: Order, company_id: UUID, user_id: UUID
    ) -> None:
        """Décrémente le stock réel lors de la livraison/retrait."""
        result = await self.db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        items = result.scalars().all()

        for item in items:
            if not item.product_id:
                continue
            result = await self.db.execute(
                select(Product).where(Product.id == item.product_id)
            )
            product = result.scalar_one_or_none()
            if product and product.track_stock:
                qty_before = product.stock_quantity
                product.stock_quantity = max(0, product.stock_quantity - item.quantity)
                product.stock_reserved = max(0, product.stock_reserved - item.quantity)
                movement = StockMovement(
                    company_id=company_id,
                    product_id=product.id,
                    order_id=order.id,
                    type="sale",
                    quantity_change=-item.quantity,
                    quantity_before=qty_before,
                    quantity_after=product.stock_quantity,
                    created_by_id=user_id,
                    notes="Vente confirmée",
                )
                self.db.add(movement)

    # ------------------------------------------------------------------ #
    #  HELPERS                                                              #
    # ------------------------------------------------------------------ #

    async def _get_order_or_fail(self, order_id: UUID, company_id: UUID) -> Order:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id, Order.company_id == company_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundError("Commande")
        return order

    async def _get_product_or_fail(self, product_id: UUID, company_id: UUID) -> Product:
        result = await self.db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.company_id == company_id,
                Product.is_deleted == False,
            )
        )
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundError("Produit")
        return product

    async def _generate_order_number(self, company_id: UUID) -> str:
        """Numéro séquentiel atomique par entreprise : SC-YYYY-NNNNN"""
        from core.sequences import next_document_number
        return await next_document_number(self.db, company_id, "order")

    async def create_scan_go_order(
        self,
        customer_id: UUID,
        store_id: UUID,
        company_id: UUID,
        items: list[dict],
        notes: str | None = None,
    ) -> Order:
        """
        Crée une commande Scan & Go depuis une liste de barcodes.
        Résolution catalogue automatique (internal / csv / external / hybrid).
        Pas de panier intermédiaire.
        """
        if not items:
            raise BadRequestError("La liste d'articles est vide")

        from apps.stores.models import Store
        result = await self.db.execute(select(Store).where(Store.id == store_id))
        store = result.scalar_one_or_none()
        if not store:
            raise NotFoundError("Magasin")

        # Résolution produits par barcode
        from apps.catalog.models import Product
        order_items_data: list[dict] = []
        subtotal = 0

        for item_req in items:
            barcode: str = item_req["barcode"]
            quantity: int = int(item_req.get("quantity", 1))
            if quantity <= 0:
                raise BadRequestError(f"Quantité invalide pour {barcode}")

            # Chercher le produit dans le catalogue interne (le CatalogResolutionService
            # gère le mode hybride mais nécessite une DB flush — on utilise le lookup direct
            # car le frontend Scan & Go est déjà passé par GET /catalog/products/barcode/{barcode})
            prod_result = await self.db.execute(
                select(Product).where(
                    Product.company_id == company_id,
                    Product.barcode == barcode,
                    Product.is_deleted == False,
                )
            )
            product = prod_result.scalar_one_or_none()
            if not product:
                raise NotFoundError(f"Produit introuvable : {barcode}")
            if not product.is_available:
                raise ProductNotAvailable(product.name)
            if product.track_stock:
                available = product.stock_quantity - product.stock_reserved
                if available < quantity:
                    raise InsufficientStock(product.name, available)

            subtotal += product.price_xof * quantity
            order_items_data.append({
                "product": product,
                "quantity": quantity,
                "unit_price_xof": product.price_xof,
                "subtotal_xof": product.price_xof * quantity,
            })

        order_number = await self._generate_order_number(company_id)
        order = Order(
            company_id=company_id,
            store_id=store_id,
            customer_id=customer_id,
            order_number=order_number,
            type="scan_go",
            status="pending",
            subtotal_xof=subtotal,
            delivery_fee_xof=0,
            total_xof=subtotal,
            notes=notes,
            pickup_code=generate_pickup_code(),
            payment_expires_at=datetime.now(timezone.utc) + timedelta(
                minutes=settings.PAYMENT_MANUAL_TIMEOUT_MINUTES
            ),
        )
        self.db.add(order)
        await self.db.flush()

        for item_data in order_items_data:
            product = item_data["product"]
            self.db.add(OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                product_barcode=product.barcode,
                unit_price_xof=item_data["unit_price_xof"],
                quantity=item_data["quantity"],
                subtotal_xof=item_data["subtotal_xof"],
            ))
            if product.track_stock:
                await self._reserve_stock(
                    product=product,
                    quantity=item_data["quantity"],
                    order_id=order.id,
                    company_id=company_id,
                    user_id=customer_id,
                )

        qr = OrderQRCode(
            company_id=company_id,
            order_id=order.id,
            code=generate_verification_code(16),
            type="scan_go",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self.db.add(qr)

        await self._log(
            action="order.scan_go.created",
            company_id=company_id,
            user_id=customer_id,
            resource_type="order",
            resource_id=order.id,
            new_data={"order_number": order_number, "total": subtotal, "type": "scan_go"},
        )
        await NotificationCenterService(self.db).emit_event(
            event_key="order.created",
            company_id=company_id,
            resource_type="order",
            resource_id=order.id,
            payload={"order_number": order.order_number, "total_xof": order.total_xof},
            target_user_id=customer_id,
        )

        await self.db.flush()
        await self.db.refresh(order, attribute_names=["items"])
        return order

    async def _log(
        self,
        action: str,
        company_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        old_data: Optional[dict] = None,
        new_data: Optional[dict] = None,
    ) -> None:
        await AuditService(self.db).log(
            company_id=company_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_data=old_data,
            new_data=new_data,
        )
