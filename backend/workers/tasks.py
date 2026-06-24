"""
Taches Celery asynchrones.
- Generation PDF recu
- Notifications client/marchand
- Annulation commandes expirees
- Rapports mensuels
- Alertes stock
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

logger = logging.getLogger(__name__)

from workers.celery_app import celery_app

_ASYNC_LOOP = None


def run_async(coro):
    """Execute une coroutine Celery sur une boucle persistante par process."""
    global _ASYNC_LOOP

    if _ASYNC_LOOP is None or _ASYNC_LOOP.is_closed():
        _ASYNC_LOOP = asyncio.new_event_loop()
        asyncio.set_event_loop(_ASYNC_LOOP)

    return _ASYNC_LOOP.run_until_complete(coro)


@celery_app.task(name="workers.tasks.generate_receipt_pdf", bind=True, max_retries=3)
def generate_receipt_pdf(self, payment_id: str):
    """Genere le PDF du recu apres confirmation du paiement."""

    async def _run():
        from core.database import AsyncSessionLocal
        from apps.receipts.service import ReceiptService

        async with AsyncSessionLocal() as db:
            service = ReceiptService(db)
            try:
                receipt = await service.generate_receipt(UUID(payment_id))
                await db.commit()
                logger.info("Receipt generated: %s", receipt.receipt_number)
                return str(receipt.id)
            except Exception as e:
                await db.rollback()
                raise e

    try:
        return run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="workers.tasks.notify_merchant_payment_received")
def notify_merchant_payment_received(payment_id: str):
    """Notifie le marchand qu'un paiement est a verifier."""

    async def _run():
        from sqlalchemy import select

        from core.database import AsyncSessionLocal
        from apps.payments.models import Payment
        from apps.notifications.models import Notification
        from apps.users.models import UserCompanyRole

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Payment).where(Payment.id == UUID(payment_id)))
            payment = result.scalar_one_or_none()
            if not payment:
                return

            result = await db.execute(
                select(UserCompanyRole).where(
                    UserCompanyRole.company_id == payment.company_id,
                    UserCompanyRole.role.in_(["company_owner", "store_manager"]),
                    UserCompanyRole.is_active == True,
                )
            )
            roles = result.scalars().all()

            for role in roles:
                notif = Notification(
                    company_id=payment.company_id,
                    user_id=role.user_id,
                    type="payment_received",
                    title="Nouveau paiement a verifier",
                    body=f"Paiement de {payment.amount_xof:,} FCFA - Ref: {payment.transaction_ref or 'N/A'}",
                    data={"payment_id": str(payment.id), "order_id": str(payment.order_id)},
                    channel="in_app",
                )
                db.add(notif)
            await db.commit()

    run_async(_run())


@celery_app.task(name="workers.tasks.notify_customer_payment_confirmed")
def notify_customer_payment_confirmed(payment_id: str):
    """Notifie le client (in-app + email) que son paiement est confirme."""

    async def _run():
        from sqlalchemy import select

        from core.database import AsyncSessionLocal
        from apps.orders.models import Order
        from apps.payments.models import Payment
        from apps.receipts.models import Receipt
        from apps.notifications.models import Notification
        from apps.users.models import User
        from apps.notifications.service import EmailService

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Payment).where(Payment.id == UUID(payment_id)))
            payment = result.scalar_one_or_none()
            if not payment:
                return

            result = await db.execute(select(Receipt).where(Receipt.payment_id == payment.id))
            receipt = result.scalar_one_or_none()

            result = await db.execute(select(Order).where(Order.id == payment.order_id))
            order = result.scalar_one_or_none()

            result = await db.execute(select(User).where(User.id == payment.customer_id))
            customer = result.scalar_one_or_none()

            notif = Notification(
                company_id=payment.company_id,
                user_id=payment.customer_id,
                type="payment_received",
                title="Paiement confirme",
                body=f"Votre paiement de {payment.amount_xof:,} FCFA a ete confirme. Votre commande est en cours de preparation.",
                data={
                    "payment_id": str(payment.id),
                    "receipt_id": str(receipt.id) if receipt else None,
                },
                channel="in_app",
            )
            db.add(notif)
            await db.commit()

            if customer and customer.email and order:
                try:
                    from core.config import settings
                    receipt_url = (
                        f"{settings.APP_URL}/receipts/{receipt.id}"
                        if receipt else None
                    )
                    await EmailService.send_payment_confirmed(
                        email=customer.email,
                        customer_name=customer.full_name,
                        order_number=order.order_number,
                        amount_xof=payment.amount_xof,
                        receipt_url=receipt_url,
                    )
                except Exception as exc:
                    logger.error("Payment confirmed email not sent: %s", exc)

    run_async(_run())


@celery_app.task(name="workers.tasks.notify_customer_payment_rejected")
def notify_customer_payment_rejected(payment_id: str):
    """Notifie le client (in-app + email) que son paiement a ete rejete."""

    async def _run():
        from sqlalchemy import select

        from core.database import AsyncSessionLocal
        from apps.orders.models import Order
        from apps.payments.models import Payment
        from apps.notifications.models import Notification
        from apps.users.models import User
        from apps.notifications.service import EmailService

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Payment).where(Payment.id == UUID(payment_id)))
            payment = result.scalar_one_or_none()
            if not payment:
                return

            result = await db.execute(select(Order).where(Order.id == payment.order_id))
            order = result.scalar_one_or_none()

            result = await db.execute(select(User).where(User.id == payment.customer_id))
            customer = result.scalar_one_or_none()

            notif = Notification(
                company_id=payment.company_id,
                user_id=payment.customer_id,
                type="payment_rejected",
                title="Paiement non confirme",
                body=f"Votre paiement n'a pas pu etre verifie. Raison : {payment.rejection_reason or 'Non precisee'}. Veuillez reessayer.",
                data={"payment_id": str(payment.id)},
                channel="in_app",
            )
            db.add(notif)
            await db.commit()

            if customer and customer.email and order:
                try:
                    await EmailService.send_payment_rejected(
                        email=customer.email,
                        customer_name=customer.full_name,
                        order_number=order.order_number,
                        reason=payment.rejection_reason,
                    )
                except Exception as exc:
                    logger.error("Payment rejected email not sent: %s", exc)

    run_async(_run())


@celery_app.task(name="workers.tasks.cancel_expired_orders")
def cancel_expired_orders():
    """Annule les commandes dont le delai de paiement est depasse."""

    async def _run():
        from sqlalchemy import select

        from core.database import AsyncSessionLocal
        from apps.orders.models import Order
        from apps.notifications.models import AuditLog

        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(Order).where(
                    Order.status.in_(["pending", "awaiting_payment"]),
                    Order.payment_expires_at < now,
                )
            )
            orders = result.scalars().all()

            for order in orders:
                order.status = "cancelled"
                order.cancelled_at = now
                order.cancelled_reason = "Delai de paiement depasse"
                log = AuditLog(
                    company_id=order.company_id,
                    action="order.auto_cancelled",
                    resource_type="order",
                    resource_id=order.id,
                    new_data={"reason": "payment_timeout"},
                )
                db.add(log)

            await db.commit()
            if orders:
                logger.info("%d orders auto-cancelled (payment timeout)", len(orders))

    run_async(_run())


@celery_app.task(name="workers.tasks.send_stock_alerts")
def send_stock_alerts():
    """Envoie des alertes pour les produits dont le stock est sous le seuil."""

    async def _run():
        from sqlalchemy import select

        from core.database import AsyncSessionLocal
        from apps.catalog.models import Product
        from apps.notifications.models import Notification
        from apps.users.models import UserCompanyRole

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Product).where(
                    Product.track_stock == True,
                    Product.is_deleted == False,
                    Product.stock_quantity <= Product.stock_alert_qty,
                )
            )
            products = result.scalars().all()

            for product in products:
                result = await db.execute(
                    select(UserCompanyRole).where(
                        UserCompanyRole.company_id == product.company_id,
                        UserCompanyRole.role.in_(["company_owner", "store_manager"]),
                        UserCompanyRole.is_active == True,
                    )
                )
                roles = result.scalars().all()
                for role in roles:
                    notif = Notification(
                        company_id=product.company_id,
                        user_id=role.user_id,
                        type="stock_alert",
                        title="Alerte stock faible",
                        body=f"'{product.name}' : {product.stock_quantity} restants (seuil : {product.stock_alert_qty})",
                        data={"product_id": str(product.id)},
                        channel="in_app",
                    )
                    db.add(notif)

            await db.commit()

    run_async(_run())


@celery_app.task(
    name="workers.tasks.deliver_webhook",
    bind=True,
    max_retries=5,
    default_retry_delay=60,
)
def deliver_webhook(self, delivery_id: str):
    """
    Livre un webhook sortant avec retry exponentiel.
    Signature HMAC-SHA256 dans X-Fiissa-Signature.
    """

    async def _run():
        from core.database import AsyncSessionLocal
        from apps.integrations.service import WebhookService

        async with AsyncSessionLocal() as db:
            success = await WebhookService.deliver_delivery(UUID(delivery_id), db)
            return success

    try:
        success = run_async(_run())
        if not success:
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(countdown=countdown)
    except Exception as exc:
        if self.request.retries < self.max_retries:
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)
        logger.error("Webhook %s permanently failed after %d retries", delivery_id, self.max_retries)


@celery_app.task(name="workers.tasks.check_subscription_expiry")
def check_subscription_expiry():
    """Suspend les entreprises dont la periode d'abonnement est expiree."""

    async def _run():
        from core.database import AsyncSessionLocal
        from apps.companies.service import SubscriptionService

        async with AsyncSessionLocal() as db:
            count = await SubscriptionService.suspend_expired_subscriptions(db)
            if count:
                logger.info("%d company(ies) suspended for expired subscription", count)

    run_async(_run())


@celery_app.task(name="workers.tasks.generate_monthly_reports")
def generate_monthly_reports():
    """Genere les rapports mensuels agreges pour toutes les entreprises actives."""

    async def _run():
        from sqlalchemy import select

        from core.database import AsyncSessionLocal
        from apps.companies.models import Company
        from apps.reports.service import ReportService

        now = datetime.now(timezone.utc)
        if now.day != 1:
            return

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Company).where(Company.is_active == True, Company.is_suspended == False)
            )
            companies = result.scalars().all()
            for company in companies:
                try:
                    service = ReportService(db)
                    await service.generate_monthly_report(company.id, now.year, now.month - 1 or 12)
                    logger.info("Monthly report generated: company=%s", company.id)
                except Exception as exc:
                    logger.error("Monthly report error for company %s: %s", company.id, exc)

    run_async(_run())


@celery_app.task(name="workers.tasks.compute_customer_scores")
def compute_customer_scores():
    """Recalcule quotidiennement les segments RFM pour toutes les entreprises actives."""

    async def _run():
        from sqlalchemy import select

        from apps.companies.models import Company
        from apps.loyalty.service import CustomerIntelligenceService
        from core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Company).where(Company.is_active == True, Company.is_suspended == False)
            )
            companies = result.scalars().all()
            service = CustomerIntelligenceService(db)
            for company in companies:
                try:
                    summary = await service.recompute_company_scores(company.id)
                    logger.info(
                        "Customer scores recomputed: company=%s customers=%d",
                        company.id, summary['computed_customers']
                    )
                except Exception as exc:
                    logger.error("Customer scores error for company %s: %s", company.id, exc)
            await db.commit()

    run_async(_run())
