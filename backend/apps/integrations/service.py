"""
WebhookService — Livraison sortante avec signature HMAC-SHA256.
Architecture :
- dispatch_event() crée une WebhookDelivery et délègue à Celery
- deliver_webhook_task() (Celery) effectue le HTTP POST avec retry exponentiel
- Signature : X-Fiissa-Signature: sha256=HMAC(payload_json, secret)
- La clé secrète est stockée chiffrée (AES-256-GCM) — jamais en clair ni transmise
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.integrations.models import WebhookDelivery, WebhookEndpoint
from core.secrets import decrypt_secret


class WebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def dispatch_event(
        self,
        *,
        company_id: Optional[UUID],
        event_key: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Enregistre une WebhookDelivery par endpoint abonné et envoie via Celery.
        La livraison HTTP est toujours asynchrone — jamais dans la transaction principale.
        """
        if not company_id:
            return

        result = await self.db.execute(
            select(WebhookEndpoint).where(
                WebhookEndpoint.company_id == company_id,
                WebhookEndpoint.is_active == True,
            )
        )
        endpoints = result.scalars().all()
        for endpoint in endpoints:
            if event_key not in (endpoint.events or []):
                continue

            # Crée le log de livraison (status=pending)
            delivery = WebhookDelivery(
                endpoint_id=endpoint.id,
                company_id=company_id,
                event_type=event_key,
                payload=payload,
                status="pending",
            )
            self.db.add(delivery)
            await self.db.flush()

            # Délègue la livraison HTTP à Celery (fire-and-forget)
            from workers.tasks import deliver_webhook
            try:
                deliver_webhook.delay(str(delivery.id))
            except Exception:
                pass

    @staticmethod
    def _compute_signature(secret: str, payload_json: str) -> str:
        """HMAC-SHA256 du corps JSON — format GitHub-compatible."""
        mac = hmac.new(
            secret.encode("utf-8"),
            payload_json.encode("utf-8"),
            hashlib.sha256,
        )
        return f"sha256={mac.hexdigest()}"

    @staticmethod
    async def deliver_delivery(delivery_id: UUID, db: AsyncSession) -> bool:
        """
        Effectue la livraison HTTP pour une WebhookDelivery donnée.
        Appelé par le worker Celery — indépendant de la transaction principale.
        Retourne True si succès, False si échec (le caller gère le retry).
        """
        result = await db.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.id == delivery_id)
        )
        delivery = result.scalar_one_or_none()
        if not delivery:
            return False

        result2 = await db.execute(
            select(WebhookEndpoint).where(WebhookEndpoint.id == delivery.endpoint_id)
        )
        endpoint = result2.scalar_one_or_none()
        if not endpoint or not endpoint.is_active:
            delivery.status = "failed"
            delivery.response_body = "Endpoint désactivé ou introuvable"
            await db.commit()
            return False

        payload_json = json.dumps(delivery.payload, ensure_ascii=False, default=str)
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "Fiissa-Webhook/1.0",
            "X-Fiissa-Event": delivery.event_type,
            "X-Fiissa-Delivery": str(delivery.id),
        }

        # Signature HMAC — jamais le secret lui-même
        if endpoint.secret_encrypted:
            try:
                secret = decrypt_secret(endpoint.secret_encrypted)
                headers["X-Fiissa-Signature"] = WebhookService._compute_signature(secret, payload_json)
            except Exception:
                pass  # secret corrompu → livraison sans signature

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    endpoint.target_url,
                    content=payload_json,
                    headers=headers,
                )
            delivery.response_status = response.status_code
            delivery.response_body = response.text[:4000]

            if 200 <= response.status_code < 300:
                delivery.status = "success"
                delivery.delivered_at = datetime.now(timezone.utc)
                endpoint.last_success_at = delivery.delivered_at
                await db.commit()
                return True
            else:
                delivery.status = "failed"
                delivery.retry_count = (delivery.retry_count or 0) + 1
                await db.commit()
                return False

        except Exception as exc:
            delivery.status = "failed"
            delivery.response_body = str(exc)[:2000]
            delivery.retry_count = (delivery.retry_count or 0) + 1
            await db.commit()
            return False
