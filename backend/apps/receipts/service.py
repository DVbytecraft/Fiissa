"""
ReceiptService — Génération de reçus PDF avec WeasyPrint.
Un reçu est IMMUABLE après génération.
Le numéro de reçu est généré via une séquence atomique par entreprise.
"""

import html as html_module
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.notifications.service import AuditService, NotificationCenterService
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.receipts.models import Receipt
from apps.stores.models import Store
from apps.users.models import User
from core.config import settings
from core.exceptions import NotFoundError, PDFGenerationError
from core.security import generate_verification_code


class ReceiptService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_receipt(self, payment_id: UUID) -> Receipt:
        """
        Génère le reçu pour un paiement confirmé.
        Appelé de manière asynchrone par Celery après confirmation du paiement.
        """
        # Charger le paiement avec toutes ses relations
        result = await self.db.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Paiement")

        if payment.status != "confirmed":
            raise ValueError(f"Le paiement n'est pas confirmé (statut: {payment.status})")

        # Vérifier si un reçu existe déjà (idempotence)
        result = await self.db.execute(
            select(Receipt).where(Receipt.payment_id == payment_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # Charger la commande + items
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == payment.order_id)
        )
        order = result.scalar_one()

        # Charger le magasin
        result = await self.db.execute(select(Store).where(Store.id == order.store_id))
        store = result.scalar_one()

        # Charger le client
        result = await self.db.execute(select(User).where(User.id == order.customer_id))
        customer = result.scalar_one()

        from core.sequences import next_document_number
        receipt_number = await next_document_number(self.db, payment.company_id, "receipt")
        verification_code = generate_verification_code(16)

        # Générer le HTML du reçu (snapshot immuable)
        html_content = self._render_receipt_html(
            receipt_number=receipt_number,
            verification_code=verification_code,
            order=order,
            payment=payment,
            store=store,
            customer=customer,
        )

        receipt = Receipt(
            company_id=payment.company_id,
            store_id=order.store_id,
            order_id=order.id,
            payment_id=payment.id,
            customer_id=customer.id,
            receipt_number=receipt_number,
            verification_code=verification_code,
            html_content=html_content,
            amount_xof=payment.amount_xof,
            status="generated",
            issued_at=datetime.now(timezone.utc),
        )
        self.db.add(receipt)
        await self.db.flush()

        # Générer le PDF
        try:
            pdf_url = await self._generate_and_store_pdf(
                receipt_id=receipt.id,
                html_content=html_content,
                company_id=payment.company_id,
            )
            receipt.pdf_url = pdf_url
            receipt.pdf_generated_at = datetime.now(timezone.utc)
        except Exception as e:
            logger.error("PDF generation failed for receipt %s: %s", receipt_number, e)

        await self._log(
            action="receipt.generated",
            company_id=payment.company_id,
            user_id=customer.id,
            resource_type="receipt",
            resource_id=receipt.id,
            new_data={
                "receipt_number": receipt_number,
                "amount": payment.amount_xof,
                "order_number": order.order_number,
            },
        )
        await NotificationCenterService(self.db).emit_event(
            event_key="receipt.generated",
            company_id=payment.company_id,
            resource_type="receipt",
            resource_id=receipt.id,
            payload={
                "receipt_number": receipt.receipt_number,
                "order_number": order.order_number,
                "amount_xof": receipt.amount_xof,
            },
            target_user_id=customer.id,
        )

        if customer.email:
            from apps.notifications.service import EmailService
            try:
                receipt_url = receipt.pdf_url or f"{settings.APP_URL}/receipts/{receipt.id}"
                await EmailService.send_receipt_generated(
                    email=customer.email,
                    customer_name=customer.full_name,
                    order_number=order.order_number,
                    receipt_number=receipt.receipt_number,
                    receipt_url=receipt_url,
                )
            except Exception as exc:
                logger.error("Receipt email not sent: %s", exc)

        return receipt

    def _render_receipt_html(
        self,
        receipt_number: str,
        verification_code: str,
        order: Order,
        payment: Payment,
        store: Store,
        customer: User,
    ) -> str:
        """Génère le HTML du reçu. Toutes les valeurs utilisateur sont html.escape()."""
        e = html_module.escape  # alias court
        now = datetime.now(timezone.utc)

        # Valeurs statiques — pas de données utilisateur
        verify_url = f"{settings.APP_URL}/receipts/verify/{verification_code}"

        def format_xof(amount: int) -> str:
            return f"{amount:,} FCFA".replace(",", " ")  # espace insécable

        operators = {
            "orange_money": "Orange Money",
            "wave": "Wave",
            "mtn_momo": "MTN MoMo",
            "moov_money": "Moov Money",
            "free_money": "Free Money",
            "cash": "Espèces",
            "other": "Autre",
        }
        order_type_label = {
            "click_collect": "Retrait en magasin",
            "delivery": "Livraison",
            "scan_go": "Scan & Go",
        }.get(order.type, e(order.type))

        items_rows = "".join(
            f"<tr>"
            f"<td>{e(item.product_name)}</td>"
            f"<td class='td-right'>{item.quantity}</td>"
            f"<td class='td-right'>{format_xof(item.unit_price_xof)}</td>"
            f"<td class='td-right'>{format_xof(item.subtotal_xof)}</td>"
            f"</tr>"
            for item in order.items
        )

        subtotal_row = (
            f"<div class='total-row'><span>Sous-total</span>"
            f"<span>{format_xof(order.subtotal_xof)}</span></div>"
            if order.discount_xof > 0 or order.delivery_fee_xof > 0
            else ""
        )
        delivery_row = (
            f"<div class='total-row'><span>Livraison</span>"
            f"<span>{format_xof(order.delivery_fee_xof)}</span></div>"
            if order.delivery_fee_xof > 0
            else ""
        )
        discount_row = (
            f"<div class='total-row'><span>Remise</span>"
            f"<span>-{format_xof(order.discount_xof)}</span></div>"
            if order.discount_xof > 0
            else ""
        )
        ref_row = (
            f"<div class='info-row'><span class='info-label'>Référence</span>"
            f"<span class='info-value'>{e(payment.transaction_ref)}</span></div>"
            if payment.transaction_ref
            else ""
        )
        phone_row = (
            f"<div class='info-row'><span class='info-label'>N° payeur</span>"
            f"<span class='info-value'>{e(payment.sender_phone)}</span></div>"
            if payment.sender_phone
            else ""
        )

        return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'DejaVu Sans', Arial, sans-serif; margin: 0; padding: 20px; color: #1a1a1a; }}
  .header {{ text-align: center; border-bottom: 2px solid #2563eb; padding-bottom: 16px; margin-bottom: 20px; }}
  .logo {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
  .store-name {{ font-size: 18px; font-weight: bold; margin-top: 8px; }}
  .receipt-number {{ font-size: 14px; color: #6b7280; margin-top: 4px; }}
  .section {{ margin-bottom: 16px; }}
  .section-title {{ font-weight: bold; font-size: 13px; color: #374151; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em; }}
  .info-row {{ display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px; }}
  .info-label {{ color: #6b7280; }}
  .info-value {{ font-weight: 500; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 6px 8px; background: #f3f4f6; font-size: 12px; color: #374151; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #f3f4f6; }}
  .td-right {{ text-align: right; }}
  .total-section {{ margin-top: 12px; }}
  .total-row {{ display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px; }}
  .grand-total {{ font-weight: bold; font-size: 18px; color: #2563eb; border-top: 2px solid #2563eb; padding-top: 8px; margin-top: 8px; }}
  .badge-paid {{ display: inline-block; background: #dcfce7; color: #16a34a; font-weight: bold; padding: 4px 12px; border-radius: 20px; font-size: 13px; margin-top: 8px; }}
  .footer {{ margin-top: 24px; text-align: center; font-size: 11px; color: #9ca3af; border-top: 1px solid #e5e7eb; padding-top: 12px; }}
  .verify-url {{ font-size: 10px; color: #6b7280; word-break: break-all; }}
</style>
</head>
<body>
<div class="header">
  <div class="logo">Fiissa</div>
  <div class="store-name">{e(store.name)}</div>
  <div class="receipt-number">Reçu N° {e(receipt_number)}</div>
</div>

<div class="section">
  <div class="section-title">Informations</div>
  <div class="info-row"><span class="info-label">Date</span><span class="info-value">{now.strftime('%d/%m/%Y à %H:%M')}</span></div>
  <div class="info-row"><span class="info-label">Commande</span><span class="info-value">{e(order.order_number)}</span></div>
  <div class="info-row"><span class="info-label">Client</span><span class="info-value">{e(customer.full_name)}</span></div>
  <div class="info-row"><span class="info-label">Type</span><span class="info-value">{order_type_label}</span></div>
</div>

<div class="section">
  <div class="section-title">Articles</div>
  <table>
    <thead>
      <tr>
        <th>Produit</th>
        <th class="td-right">Qté</th>
        <th class="td-right">Prix unit.</th>
        <th class="td-right">Sous-total</th>
      </tr>
    </thead>
    <tbody>{items_rows}</tbody>
  </table>
</div>

<div class="total-section">
  {subtotal_row}{delivery_row}{discount_row}
  <div class="total-row grand-total"><span>TOTAL PAYÉ</span><span>{format_xof(payment.amount_xof)}</span></div>
</div>

<div class="section" style="margin-top: 16px;">
  <div class="section-title">Paiement</div>
  <div class="info-row"><span class="info-label">Mode</span><span class="info-value">{e(operators.get(payment.operator, payment.operator))}</span></div>
  {ref_row}{phone_row}
  <div style="margin-top: 8px;"><span class="badge-paid">✓ PAYÉ</span></div>
</div>

<div class="footer">
  <div>Vérifiez ce reçu sur :</div>
  <div class="verify-url">{e(verify_url)}</div>
  <div style="margin-top: 8px;">Code : {e(verification_code)}</div>
  <div style="margin-top: 12px;">Fiissa — La plateforme digitale du commerce UEMOA</div>
  <div>Ce reçu est un document officiel. Conservez-le.</div>
</div>
</body>
</html>"""

    async def _generate_and_store_pdf(
        self, receipt_id: UUID, html_content: str, company_id: UUID
    ) -> str:
        """Génère le PDF avec WeasyPrint et le stocke."""
        try:
            from weasyprint import HTML, CSS

            pdf_bytes = HTML(string=html_content).write_pdf()

            # Stocker le PDF
            storage_key = f"receipts/{company_id}/{receipt_id}.pdf"

            if settings.STORAGE_BACKEND in ("minio", "s3"):
                url = await self._upload_to_s3(pdf_bytes, storage_key)
            else:
                url = await self._save_local(pdf_bytes, storage_key)

            return url
        except Exception as e:
            raise PDFGenerationError() from e

    async def _upload_to_s3(self, pdf_bytes: bytes, key: str) -> str:
        """Upload vers MinIO/S3."""
        import aioboto3
        session = aioboto3.Session()
        async with session.client(
            "s3",
            endpoint_url=f"{'https' if settings.MINIO_USE_SSL else 'http'}://{settings.MINIO_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
        ) as s3:
            await s3.put_object(
                Bucket=settings.MINIO_BUCKET_RECEIPTS,
                Key=key,
                Body=pdf_bytes,
                ContentType="application/pdf",
            )
        return f"{settings.API_URL}/receipts/download/{key}"

    async def _save_local(self, pdf_bytes: bytes, key: str) -> str:
        """Sauvegarde locale (dev)."""
        import os
        path = f"/app/media/{key}"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(pdf_bytes)
        return f"{settings.API_URL}/media/{key}"

    async def _log(self, action: str, **kwargs) -> None:
        await AuditService(self.db).log(action=action, **kwargs)

    async def verify_receipt(self, verification_code: str) -> dict:
        """Endpoint public : vérification d'un reçu par QR code."""
        result = await self.db.execute(
            select(Receipt)
            .options(selectinload(Receipt.order).selectinload(Order.items))
            .where(Receipt.verification_code == verification_code)
        )
        receipt = result.scalar_one_or_none()
        if not receipt:
            return {"valid": False, "status": "not_found", "color": "red"}

        order = receipt.order
        status_map = {
            "delivered": ("valid", "green", "Reçu valide — Commande livrée"),
            "ready": ("valid", "green", "Reçu valide — Prêt pour retrait"),
            "confirmed": ("pending", "orange", "Commande confirmée — En préparation"),
            "cancelled": ("invalid", "red", "Commande annulée"),
            "refunded": ("invalid", "red", "Commande remboursée"),
        }

        status_info = status_map.get(order.status, ("pending", "orange", "En cours"))

        return {
            "valid": status_info[0] == "valid",
            "status": status_info[0],
            "color": status_info[1],
            "message": status_info[2],
            "receipt_number": receipt.receipt_number,
            "order_number": order.order_number,
            "amount_xof": receipt.amount_xof,
            "issued_at": receipt.issued_at.isoformat(),
            "items_count": len(order.items),
        }
