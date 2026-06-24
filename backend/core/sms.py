"""
SMSService — Provider d'envoi de SMS transactionnels.
Providers supportés : mock (dev/test), Africa's Talking, Twilio.

Règles :
- Ne jamais lever d'exception vers l'appelant — logguer et retourner False.
- Tous les providers sont appelés de manière non-bloquante (run_in_executor).
- En développement ou mode mock : log console uniquement, retourne True.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SMSService:
    """Envoi de SMS avec fallback silencieux. Retourne True/False."""

    @staticmethod
    async def send(phone: str, message: str) -> bool:
        from core.config import settings

        if settings.SMS_PROVIDER == "mock" or not settings.is_production:
            logger.info("[SMS MOCK] → %s: %s", phone, message)
            return True

        if settings.SMS_PROVIDER == "africas_talking":
            return await SMSService._send_africas_talking(phone, message)

        if settings.SMS_PROVIDER == "twilio":
            return await SMSService._send_twilio(phone, message)

        logger.warning("[SMS] Provider non reconnu : %s", settings.SMS_PROVIDER)
        return False

    @staticmethod
    async def _send_africas_talking(phone: str, message: str) -> bool:
        from core.config import settings
        try:
            import africastalking

            africastalking.initialize(
                settings.AFRICAS_TALKING_USERNAME,
                settings.AFRICAS_TALKING_API_KEY,
            )
            sms_client = africastalking.SMS
            sender: Optional[str] = settings.SMS_SENDER_ID or None

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: sms_client.send(message, [phone], sender),
            )

            recipients = response.get("SMSMessageData", {}).get("Recipients", [])
            if recipients and recipients[0].get("status") == "Success":
                logger.info("[SMS AT] Envoyé → %s", phone)
                return True

            logger.warning("[SMS AT] Envoi non confirmé : %s", response)
            return False

        except Exception as exc:
            logger.error("[SMS AT] Erreur : %s", exc)
            return False

    @staticmethod
    async def _send_twilio(phone: str, message: str) -> bool:
        from core.config import settings
        try:
            from twilio.rest import Client

            def _sync_send() -> str:
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                msg = client.messages.create(
                    body=message,
                    from_=settings.TWILIO_FROM_NUMBER,
                    to=phone,
                )
                return msg.sid

            loop = asyncio.get_event_loop()
            sid = await loop.run_in_executor(None, _sync_send)
            logger.info("[SMS Twilio] SID=%s → %s", sid, phone)
            return True

        except Exception as exc:
            logger.error("[SMS Twilio] Erreur : %s", exc)
            return False
