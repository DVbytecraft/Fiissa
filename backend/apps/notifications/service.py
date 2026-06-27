from __future__ import annotations

from datetime import datetime, timezone
from string import Template
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.notifications.models import (
    AuditLog,
    Notification,
    NotificationEvent,
    NotificationTemplate,
)
from apps.integrations.service import WebhookService
from core.request_context import get_request_ip, get_request_user_agent


DEFAULT_NOTIFICATION_CONTENT: dict[str, dict[str, str]] = {
    "payment.confirmed": {
        "title": "Paiement valide",
        "body": "Le paiement de la commande ${order_number} a ete valide.",
    },
    "payment.rejected": {
        "title": "Paiement rejete",
        "body": "Le paiement de la commande ${order_number} a ete rejete.",
    },
    "order.ready": {
        "title": "Commande prete",
        "body": "La commande ${order_number} est prete.",
    },
    "order.cancelled": {
        "title": "Commande annulee",
        "body": "La commande ${order_number} a ete annulee.",
    },
    "stock.low": {
        "title": "Stock faible",
        "body": "Le stock du produit ${product_name} est faible.",
    },
    "receipt.generated": {
        "title": "Recu disponible",
        "body": "Le recu ${receipt_number} est disponible.",
    },
}


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        *,
        action: str,
        company_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        old_data: Optional[dict[str, Any]] = None,
        new_data: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        log = AuditLog(
            company_id=company_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_data=old_data,
            new_data=new_data,
            ip_address=ip_address if ip_address is not None else get_request_ip(),
            user_agent=user_agent if user_agent is not None else get_request_user_agent(),
        )
        self.db.add(log)
        return log


class NotificationCenterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def emit_event(
        self,
        *,
        event_key: str,
        company_id: Optional[UUID],
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        payload: Optional[dict[str, Any]] = None,
        target_user_id: Optional[UUID] = None,
        channel: str = "in_app",
    ) -> NotificationEvent:
        event = NotificationEvent(
            company_id=company_id,
            event_key=event_key,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload,
            status="pending",
        )
        self.db.add(event)
        await self.db.flush()

        try:
            if target_user_id:
                template = await self._get_template(company_id, event_key, channel)
                title, body = self._render_template(event_key, template, payload or {})
                self.db.add(
                    Notification(
                        company_id=company_id,
                        user_id=target_user_id,
                        type=self._map_notification_type(event_key),
                        title=title,
                        body=body,
                        data=payload,
                        channel=channel,
                        sent_at=datetime.now(timezone.utc),
                    )
                )
            await WebhookService(self.db).dispatch_event(
                company_id=company_id,
                event_key=event_key,
                payload=payload or {},
            )
            event.status = "processed"
            event.error_message = None
        except Exception as exc:
            event.status = "failed"
            event.error_message = str(exc)

        return event

    async def _get_template(
        self, company_id: Optional[UUID], event_key: str, channel: str
    ) -> Optional[NotificationTemplate]:
        if company_id:
            result = await self.db.execute(
                select(NotificationTemplate).where(
                    NotificationTemplate.company_id == company_id,
                    NotificationTemplate.event_key == event_key,
                    NotificationTemplate.channel == channel,
                    NotificationTemplate.is_active,
                )
            )
            template = result.scalar_one_or_none()
            if template:
                return template

        result = await self.db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.company_id.is_(None),
                NotificationTemplate.event_key == event_key,
                NotificationTemplate.channel == channel,
                NotificationTemplate.is_active,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _render_template(
        event_key: str,
        template: Optional[NotificationTemplate],
        payload: dict[str, Any],
    ) -> tuple[str, str]:
        if template:
            subject = Template(template.subject_template or "").safe_substitute(payload)
            body = Template(template.body_template).safe_substitute(payload)
            return subject or DEFAULT_NOTIFICATION_CONTENT.get(event_key, {}).get("title", event_key), body

        fallback = DEFAULT_NOTIFICATION_CONTENT.get(event_key, {"title": event_key, "body": event_key})
        return (
            Template(fallback["title"]).safe_substitute(payload),
            Template(fallback["body"]).safe_substitute(payload),
        )

    @staticmethod
    def _map_notification_type(event_key: str) -> str:
        mapping = {
            "payment.confirmed": "payment_received",
            "payment.rejected": "payment_rejected",
            "order.ready": "order_ready",
            "order.cancelled": "order_cancelled",
            "stock.low": "stock_alert",
            "receipt.generated": "receipt_ready",
        }
        return mapping.get(event_key, "order_confirmed")


class EmailService:
    """Service d'envoi d'emails transactionnels via SMTP."""

    # ── Helpers privés ─────────────────────────────────────────────────────────

    @staticmethod
    async def _send(*, to: str, subject: str, body_html: str) -> None:
        """Envoie un email via SMTP, API Brevo ou mock selon la config."""
        import asyncio
        import json
        import logging
        import smtplib
        import urllib.request
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from core.config import settings

        logger = logging.getLogger(__name__)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = (
            f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
            if settings.EMAIL_FROM_NAME
            else settings.EMAIL_FROM
        )
        msg["To"] = to
        if settings.EMAIL_REPLY_TO:
            msg["Reply-To"] = (
                f"{settings.EMAIL_REPLY_TO_NAME} <{settings.EMAIL_REPLY_TO}>"
                if settings.EMAIL_REPLY_TO_NAME
                else settings.EMAIL_REPLY_TO
            )
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        def _sync():
            if settings.EMAIL_PROVIDER == "mock" or not settings.SMTP_HOST or settings.SMTP_HOST == "localhost":
                logger.info("[EMAIL MOCK] To=%s | Subject=%s", to, subject)
                return

            if settings.EMAIL_PROVIDER == "brevo_api" and settings.BREVO_API_KEY:
                payload = {
                    "sender": {
                        "name": settings.EMAIL_FROM_NAME or "Fiissa",
                        "email": settings.EMAIL_FROM,
                    },
                    "to": [{"email": to}],
                    "subject": subject,
                    "htmlContent": body_html,
                }
                if settings.EMAIL_REPLY_TO:
                    payload["replyTo"] = {
                        "name": settings.EMAIL_REPLY_TO_NAME or settings.EMAIL_FROM_NAME or "Fiissa",
                        "email": settings.EMAIL_REPLY_TO,
                    }

                request = urllib.request.Request(
                    "https://api.brevo.com/v3/smtp/email",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "accept": "application/json",
                        "api-key": settings.BREVO_API_KEY,
                        "content-type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=settings.SMTP_TIMEOUT_SECONDS) as response:
                    if response.status >= 400:
                        raise RuntimeError(f"Brevo API email error: status={response.status}")
                return

            with smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            ) as srv:
                if settings.SMTP_USE_TLS:
                    srv.starttls()
                if settings.SMTP_USER:
                    srv.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                srv.sendmail(settings.EMAIL_FROM, [to], msg.as_string())

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _sync)

    # ── Emails transactionnels ──────────────────────────────────────────────────

    @staticmethod
    async def send_staff_invitation(
        *,
        email: str,
        first_name: str,
        temp_password: str,
        company_name: str,
    ) -> None:
        from core.config import settings

        body_html = f"""
        <html><body style="font-family: Arial, sans-serif; color: #1a1a1a;">
        <h2 style="color: #2563eb;">Bienvenue sur Fiissa, {first_name} !</h2>
        <p>Vous avez été invité(e) à rejoindre <strong>{company_name}</strong>.</p>
        <table style="border: 1px solid #e5e7eb; padding: 16px; border-radius: 8px;">
          <tr><td style="font-weight: bold; padding: 4px 16px 4px 0;">Email</td><td>{email}</td></tr>
          <tr><td style="font-weight: bold; padding: 4px 16px 4px 0;">Mot de passe temporaire</td>
              <td style="font-family: monospace; font-size: 16px;">{temp_password}</td></tr>
        </table>
        <p style="color: #ef4444;"><strong>Changez ce mot de passe dès votre première connexion.</strong></p>
        <p><a href="{settings.APP_URL}/login">Se connecter</a></p>
        <p style="font-size: 12px; color: #6b7280;">Fiissa</p>
        </body></html>
        """
        await EmailService._send(
            to=email,
            subject=f"Bienvenue sur Fiissa — {company_name}",
            body_html=body_html,
        )

    @staticmethod
    async def send_customer_welcome(
        *,
        email: str,
        first_name: str,
    ) -> None:
        from core.config import settings

        body_html = f"""
        <html><body style="font-family: Arial, sans-serif; color: #1a1a1a;">
        <h2 style="color: #2563eb;">Bienvenue sur Fiissa, {first_name} !</h2>
        <p>Votre compte client a bien ete cree.</p>
        <p>Vous pouvez des maintenant consulter vos commandes, recus, cartes de fidelite et wallet depuis l'application.</p>
        <p style="margin: 24px 0;">
          <a href="{settings.APP_URL}/login"
             style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;
                    text-decoration:none;font-weight:bold;">
            Acceder a mon compte
          </a>
        </p>
        <p style="font-size: 12px; color: #6b7280;">Fiissa</p>
        </body></html>
        """
        await EmailService._send(
            to=email,
            subject="Bienvenue sur Fiissa",
            body_html=body_html,
        )

    @staticmethod
    async def send_merchant_welcome(
        *,
        email: str,
        first_name: str,
        company_name: str,
    ) -> None:
        from core.config import settings

        body_html = f"""
        <html><body style="font-family: Arial, sans-serif; color: #1a1a1a;">
        <h2 style="color: #2563eb;">Bienvenue sur Fiissa, {first_name} !</h2>
        <p>Votre espace marchand <strong>{company_name}</strong> est maintenant cree.</p>
        <p>Vous pouvez configurer vos magasins, votre catalogue, vos moyens de paiement, la fidelite et les integrations.</p>
        <p style="margin: 24px 0;">
          <a href="{settings.APP_URL}/merchant/dashboard"
             style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;
                    text-decoration:none;font-weight:bold;">
            Ouvrir le dashboard marchand
          </a>
        </p>
        <p style="font-size: 12px; color: #6b7280;">Fiissa</p>
        </body></html>
        """
        await EmailService._send(
            to=email,
            subject=f"Bienvenue sur Fiissa - {company_name}",
            body_html=body_html,
        )

    @staticmethod
    async def send_login_otp(
        *,
        email: str,
        first_name: str,
        code: str,
    ) -> None:
        body_html = f"""
        <html><body style="font-family: Arial, sans-serif; color: #1a1a1a;">
        <h2 style="color: #2563eb;">Code de connexion Fiissa</h2>
        <p>Bonjour {first_name},</p>
        <p>Voici votre code de verification pour acceder a votre compte :</p>
        <p style="font-size: 28px; font-weight: 800; letter-spacing: 0.3em; margin: 24px 0;">{code}</p>
        <p>Ce code expire rapidement. Ne le partagez avec personne.</p>
        <p style="font-size: 12px; color: #6b7280;">Fiissa</p>
        </body></html>
        """
        await EmailService._send(
            to=email,
            subject="Votre code de connexion Fiissa",
            body_html=body_html,
        )

    @staticmethod
    async def send_payment_confirmed(
        *,
        email: str,
        customer_name: str,
        order_number: str,
        amount_xof: int,
        receipt_url: Optional[str] = None,
    ) -> None:
        receipt_link = (
            f'<p><a href="{receipt_url}" style="color:#2563eb;">Télécharger le reçu</a></p>'
            if receipt_url else ""
        )
        body_html = f"""
        <html><body style="font-family: Arial, sans-serif;">
        <h2 style="color: #16a34a;">Paiement confirmé</h2>
        <p>Bonjour {customer_name},</p>
        <p>Votre paiement de <strong>{amount_xof:,} FCFA</strong> pour la commande
           <strong>{order_number}</strong> a été confirmé.</p>
        {receipt_link}
        <p style="font-size: 12px; color: #6b7280;">Fiissa</p>
        </body></html>
        """
        await EmailService._send(
            to=email,
            subject=f"Paiement confirmé — {order_number}",
            body_html=body_html,
        )

    @staticmethod
    async def send_email_verification(
        *,
        email: str,
        first_name: str,
        raw_token: str,
    ) -> None:
        from core.config import settings

        verify_url = f"{settings.APP_URL}/verify-email?token={raw_token}"
        body_html = f"""
        <html><body style="font-family: Arial, sans-serif; color: #1a1a1a;">
        <h2 style="color: #2563eb;">Vérifiez votre adresse email</h2>
        <p>Bonjour {first_name},</p>
        <p>Cliquez sur le lien ci-dessous pour confirmer votre adresse email.
           Ce lien est valable <strong>24 heures</strong>.</p>
        <p style="margin: 24px 0;">
          <a href="{verify_url}"
             style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;
                    text-decoration:none;font-weight:bold;">
            Vérifier mon email
          </a>
        </p>
        <p style="color: #6b7280; font-size: 12px;">
          Si vous n'avez pas créé de compte Fiissa, ignorez cet email.
        </p>
        <p style="font-size: 12px; color: #6b7280;">Fiissa</p>
        </body></html>
        """
        await EmailService._send(
            to=email,
            subject="Vérifiez votre adresse email — Fiissa",
            body_html=body_html,
        )

    @staticmethod
    async def send_password_reset(
        *,
        email: str,
        first_name: str,
        raw_token: str,
    ) -> None:
        from core.config import settings

        reset_url = f"{settings.APP_URL}/reset-password?token={raw_token}"
        body_html = f"""
        <html><body style="font-family: Arial, sans-serif; color: #1a1a1a;">
        <h2 style="color: #dc2626;">Réinitialisation de votre mot de passe</h2>
        <p>Bonjour {first_name},</p>
        <p>Vous avez demandé la réinitialisation de votre mot de passe Fiissa.
           Ce lien est valable <strong>15 minutes</strong>.</p>
        <p style="margin: 24px 0;">
          <a href="{reset_url}"
             style="background:#dc2626;color:#fff;padding:12px 24px;border-radius:6px;
                    text-decoration:none;font-weight:bold;">
            Réinitialiser mon mot de passe
          </a>
        </p>
        <p style="color: #6b7280; font-size: 12px;">
          Si vous n'avez pas fait cette demande, ignorez cet email.
          Votre mot de passe reste inchangé.
        </p>
        <p style="font-size: 12px; color: #6b7280;">Fiissa</p>
        </body></html>
        """
        await EmailService._send(
            to=email,
            subject="Réinitialisation de mot de passe — Fiissa",
            body_html=body_html,
        )

    @staticmethod
    async def send_payment_rejected(
        *,
        email: str,
        customer_name: str,
        order_number: str,
        reason: Optional[str] = None,
    ) -> None:
        reason_block = (
            f'<p style="color:#6b7280;">Motif : {reason}</p>'
            if reason
            else ""
        )
        body_html = f"""
        <html><body style="font-family: Arial, sans-serif; color: #1a1a1a;">
        <h2 style="color: #dc2626;">Paiement non validé</h2>
        <p>Bonjour {customer_name},</p>
        <p>Votre preuve de paiement pour la commande <strong>{order_number}</strong>
           n'a pas pu être validée par le marchand.</p>
        {reason_block}
        <p>Vous pouvez soumettre une nouvelle preuve ou contacter le support.</p>
        <p style="font-size: 12px; color: #6b7280;">Fiissa</p>
        </body></html>
        """
        await EmailService._send(
            to=email,
            subject=f"Paiement non validé — {order_number}",
            body_html=body_html,
        )

    @staticmethod
    async def send_receipt_generated(
        *,
        email: str,
        customer_name: str,
        order_number: str,
        receipt_number: str,
        receipt_url: str,
    ) -> None:
        body_html = f"""
        <html><body style="font-family: Arial, sans-serif; color: #1a1a1a;">
        <h2 style="color: #2563eb;">Votre reçu est disponible</h2>
        <p>Bonjour {customer_name},</p>
        <p>Le reçu <strong>{receipt_number}</strong> pour la commande
           <strong>{order_number}</strong> est disponible.</p>
        <p style="margin: 24px 0;">
          <a href="{receipt_url}"
             style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;
                    text-decoration:none;font-weight:bold;">
            Télécharger le reçu
          </a>
        </p>
        <p style="font-size: 12px; color: #6b7280;">Fiissa</p>
        </body></html>
        """
        await EmailService._send(
            to=email,
            subject=f"Votre reçu {receipt_number} — Fiissa",
            body_html=body_html,
        )

    @staticmethod
    async def send_order_ready(
        *,
        email: str,
        customer_name: str,
        order_number: str,
        pickup_code: Optional[str] = None,
        store_name: Optional[str] = None,
    ) -> None:
        pickup_block = (
            f'<p>Code de retrait : <strong style="font-size:20px;letter-spacing:.2em;">'
            f'{pickup_code}</strong></p>'
            if pickup_code
            else ""
        )
        store_block = f"<p>Point de retrait : <strong>{store_name}</strong></p>" if store_name else ""
        body_html = f"""
        <html><body style="font-family: Arial, sans-serif; color: #1a1a1a;">
        <h2 style="color: #16a34a;">Votre commande est prête !</h2>
        <p>Bonjour {customer_name},</p>
        <p>La commande <strong>{order_number}</strong> est prête à être récupérée.</p>
        {store_block}
        {pickup_block}
        <p style="font-size: 12px; color: #6b7280;">Fiissa</p>
        </body></html>
        """
        await EmailService._send(
            to=email,
            subject=f"Commande prête — {order_number}",
            body_html=body_html,
        )

    @staticmethod
    async def send_order_cancelled(
        *,
        email: str,
        customer_name: str,
        order_number: str,
        reason: Optional[str] = None,
    ) -> None:
        reason_block = (
            f'<p style="color:#6b7280;">Motif : {reason}</p>'
            if reason
            else ""
        )
        body_html = f"""
        <html><body style="font-family: Arial, sans-serif; color: #1a1a1a;">
        <h2 style="color: #dc2626;">Commande annulée</h2>
        <p>Bonjour {customer_name},</p>
        <p>La commande <strong>{order_number}</strong> a été annulée.</p>
        {reason_block}
        <p>Si vous avez des questions, contactez notre support.</p>
        <p style="font-size: 12px; color: #6b7280;">Fiissa</p>
        </body></html>
        """
        await EmailService._send(
            to=email,
            subject=f"Commande annulée — {order_number}",
            body_html=body_html,
        )
