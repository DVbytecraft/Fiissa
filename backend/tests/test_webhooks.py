"""
Tests des webhooks sortants :
- Dispatch d'événement crée une WebhookDelivery
- Signature HMAC-SHA256 correcte
- deliver_delivery retourne True sur HTTP 200
- deliver_delivery retourne False sur HTTP 500
- Secret n'est jamais exposé dans les headers
"""
import hashlib
import hmac
import json
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.fixture
def webhook_endpoint(db, company):
    """Crée un endpoint webhook de test."""
    async def _create():
        from apps.integrations.models import WebhookEndpoint
        from core.secrets import encrypt_secret

        endpoint = WebhookEndpoint(
            company_id=company.id,
            name="Test Endpoint",
            target_url="https://webhook.example.com/hook",
            events=["payment.confirmed", "order.ready"],
            secret_encrypted=encrypt_secret("my-webhook-secret"),
            is_active=True,
        )
        db.add(endpoint)
        await db.commit()
        return endpoint
    return _create


@pytest.mark.asyncio
async def test_dispatch_event_creates_delivery(db, company, webhook_endpoint):
    from apps.integrations.models import WebhookDelivery
    from apps.integrations.service import WebhookService
    from sqlalchemy import select

    endpoint = await webhook_endpoint()

    service = WebhookService(db)

    # Mock Celery deliver_webhook.delay
    with patch("workers.tasks.deliver_webhook") as mock_task:
        mock_task.delay = MagicMock()
        await service.dispatch_event(
            company_id=company.id,
            event_key="payment.confirmed",
            payload={"order_id": "TEST-001", "amount": 5000},
        )
        await db.commit()

    result = await db.execute(
        select(WebhookDelivery).where(WebhookDelivery.company_id == company.id)
    )
    deliveries = result.scalars().all()
    assert len(deliveries) == 1
    assert deliveries[0].event_type == "payment.confirmed"
    assert deliveries[0].status == "pending"
    assert deliveries[0].payload["amount"] == 5000


@pytest.mark.asyncio
async def test_dispatch_event_skips_unsubscribed_events(db, company, webhook_endpoint):
    from apps.integrations.models import WebhookDelivery
    from apps.integrations.service import WebhookService
    from sqlalchemy import select

    await webhook_endpoint()  # subscribed to payment.confirmed, NOT to stock.low

    service = WebhookService(db)
    with patch("workers.tasks.deliver_webhook") as mock_task:
        mock_task.delay = MagicMock()
        await service.dispatch_event(
            company_id=company.id,
            event_key="stock.low",
            payload={"product_id": "P001"},
        )
        await db.commit()

    result = await db.execute(
        select(WebhookDelivery).where(WebhookDelivery.company_id == company.id)
    )
    deliveries = result.scalars().all()
    assert len(deliveries) == 0, "Delivery créée pour un événement non-abonné"


def test_hmac_signature_format():
    """La signature HMAC doit être au format sha256=<hexdigest>."""
    from apps.integrations.service import WebhookService

    secret = "my-webhook-secret"
    payload = json.dumps({"event": "payment.confirmed", "amount": 5000}, ensure_ascii=False)
    sig = WebhookService._compute_signature(secret, payload)

    assert sig.startswith("sha256="), f"Format signature invalide : {sig}"
    hex_part = sig[7:]
    assert len(hex_part) == 64, "HMAC SHA-256 doit produire 64 caractères hex"
    assert all(c in "0123456789abcdef" for c in hex_part), "Signature non-hexadécimale"


def test_hmac_signature_is_deterministic():
    """Même secret + même payload → même signature."""
    from apps.integrations.service import WebhookService

    secret = "test-secret"
    payload = '{"event":"test"}'
    sig1 = WebhookService._compute_signature(secret, payload)
    sig2 = WebhookService._compute_signature(secret, payload)
    assert sig1 == sig2


def test_hmac_signature_changes_with_payload():
    """Un payload différent doit donner une signature différente."""
    from apps.integrations.service import WebhookService

    secret = "test-secret"
    sig1 = WebhookService._compute_signature(secret, '{"event":"a"}')
    sig2 = WebhookService._compute_signature(secret, '{"event":"b"}')
    assert sig1 != sig2


def test_hmac_signature_verified_by_receiver():
    """Simuler la vérification côté destinataire."""
    from apps.integrations.service import WebhookService

    secret = "my-webhook-secret"
    payload = json.dumps({"order": "SC-2026-00001", "status": "confirmed"})
    sig = WebhookService._compute_signature(secret, payload)

    # Vérification côté récepteur (comme GitHub le fait)
    expected = "sha256=" + hmac.new(
        secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    assert hmac.compare_digest(sig, expected), "Signature non vérifiable par le destinataire"


@pytest.mark.asyncio
async def test_deliver_delivery_success(db, company, webhook_endpoint):
    """deliver_delivery retourne True quand le HTTP POST réussit."""
    from apps.integrations.models import WebhookDelivery
    from apps.integrations.service import WebhookService

    endpoint = await webhook_endpoint()

    delivery = WebhookDelivery(
        endpoint_id=endpoint.id,
        company_id=company.id,
        event_type="payment.confirmed",
        payload={"order": "SC-001"},
        status="pending",
    )
    db.add(delivery)
    await db.commit()

    mock_response = httpx.Response(200, text="ok")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        result = await WebhookService.deliver_delivery(delivery.id, db)

    assert result is True
    await db.refresh(delivery)
    assert delivery.status == "success"
    assert delivery.delivered_at is not None


@pytest.mark.asyncio
async def test_deliver_delivery_failure_returns_false(db, company, webhook_endpoint):
    """deliver_delivery retourne False sur erreur HTTP 500."""
    from apps.integrations.models import WebhookDelivery
    from apps.integrations.service import WebhookService

    endpoint = await webhook_endpoint()

    delivery = WebhookDelivery(
        endpoint_id=endpoint.id,
        company_id=company.id,
        event_type="order.ready",
        payload={"order": "SC-002"},
        status="pending",
    )
    db.add(delivery)
    await db.commit()

    mock_response = httpx.Response(500, text="Internal Server Error")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        result = await WebhookService.deliver_delivery(delivery.id, db)

    assert result is False
    await db.refresh(delivery)
    assert delivery.status == "failed"
    assert delivery.retry_count >= 1


@pytest.mark.asyncio
async def test_webhook_header_does_not_contain_plaintext_secret(db, company, webhook_endpoint):
    """X-Fiissa-Signature ne doit JAMAIS contenir le secret en clair."""
    from apps.integrations.models import WebhookDelivery
    from apps.integrations.service import WebhookService

    endpoint = await webhook_endpoint()

    delivery = WebhookDelivery(
        endpoint_id=endpoint.id,
        company_id=company.id,
        event_type="payment.confirmed",
        payload={"test": True},
        status="pending",
    )
    db.add(delivery)
    await db.commit()

    captured_headers = {}

    async def fake_post(url, content, headers):
        captured_headers.update(headers)
        return httpx.Response(200, text="ok")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=fake_post)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        await WebhookService.deliver_delivery(delivery.id, db)

    sig_header = captured_headers.get("X-Fiissa-Signature", "")
    assert sig_header.startswith("sha256="), f"Signature mal formée : {sig_header}"
    assert "my-webhook-secret" not in sig_header, "Secret en clair dans le header !"
    assert len(sig_header) == 71  # "sha256=" (7) + 64 hex chars


@pytest.mark.asyncio
async def test_dispatch_no_company_id_is_noop(db):
    """dispatch_event avec company_id=None ne doit rien créer."""
    from apps.integrations.models import WebhookDelivery
    from apps.integrations.service import WebhookService
    from sqlalchemy import select

    service = WebhookService(db)
    await service.dispatch_event(
        company_id=None,
        event_key="payment.confirmed",
        payload={"test": True},
    )
    await db.commit()

    result = await db.execute(select(WebhookDelivery))
    deliveries = result.scalars().all()
    assert len(deliveries) == 0


@pytest.mark.asyncio
async def test_update_webhook_accepts_partial_payload(client, db, company, manager, staff_headers, webhook_endpoint):
    """PATCH /integrations/webhooks/{id} doit accepter une mise à jour partielle."""
    endpoint = await webhook_endpoint()
    headers = staff_headers(manager)

    response = await client.patch(
        f"/api/v1/integrations/webhooks/{endpoint.id}",
        json={"is_active": False},
        headers=headers,
    )

    assert response.status_code == 200

    list_response = await client.get("/api/v1/integrations/webhooks", headers=headers)
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    updated = next(item for item in items if item["id"] == str(endpoint.id))
    assert updated["is_active"] is False
    assert updated["name"] == "Test Endpoint"
    assert updated["target_url"] == "https://webhook.example.com/hook"
