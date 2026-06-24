import pytest
import httpx

from apps.companies.models import Plan


class FakeWebhookClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return httpx.Response(200, text="ok")


@pytest.mark.asyncio
async def test_feature_flag_upsert_and_list(client, manager, staff_headers):
    headers = staff_headers(manager)

    upsert = await client.put(
        "/api/v1/companies/me/feature-flags",
        json={"key": "scan_go", "enabled": True, "config": {"rollout": 100}},
        headers=headers,
    )
    assert upsert.status_code == 200
    assert upsert.json()["enabled"] is True

    listing = await client.get("/api/v1/companies/me/feature-flags", headers=headers)
    assert listing.status_code == 200
    assert any(item["key"] == "scan_go" for item in listing.json()["items"])


@pytest.mark.asyncio
async def test_notification_template_upsert_and_event_listing(client, manager, staff_headers):
    headers = staff_headers(manager)

    template = await client.put(
        "/api/v1/notifications/templates",
        json={
            "event_key": "order.ready",
            "channel": "in_app",
            "subject_template": "Commande prete",
            "body_template": "La commande ${order_number} est prete.",
            "is_active": True,
        },
        headers=headers,
    )
    assert template.status_code == 200

    templates = await client.get("/api/v1/notifications/templates", headers=headers)
    assert templates.status_code == 200
    assert any(item["event_key"] == "order.ready" for item in templates.json()["items"])

    events = await client.get("/api/v1/notifications/events", headers=headers)
    assert events.status_code == 200
    assert "items" in events.json()


@pytest.mark.asyncio
async def test_support_ticket_detail_and_reply(client, customer, company, auth_headers):
    headers = auth_headers(customer)

    created = await client.post(
        "/api/v1/support/tickets",
        json={
            "subject": "Besoin d'aide",
            "body": "Mon paiement est bloque",
            "company_id": str(company.id),
            "priority": "high",
        },
        headers=headers,
    )
    assert created.status_code == 200
    ticket_id = created.json()["ticket_id"]

    detail = await client.get(f"/api/v1/support/tickets/{ticket_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["subject"] == "Besoin d'aide"

    reply = await client.post(
        f"/api/v1/support/tickets/{ticket_id}/reply",
        json={"body": "Je relance avec une precision"},
        headers=headers,
    )
    assert reply.status_code == 200
    assert "message_id" in reply.json()


@pytest.mark.asyncio
async def test_subscription_change_creates_invoice_and_renewal(client, db, manager, company, staff_headers):
    db.add(
        Plan(
            code="pro_plus",
            name="Pro Plus",
            billing_cycle="monthly",
            amount_xof=25000,
            commission_rate=0,
            features={"scan_go": True},
            is_active=True,
        )
    )
    await db.commit()

    headers = staff_headers(manager, company.id)
    change = await client.post(
        "/api/v1/companies/me/subscription/change",
        json={"plan_code": "pro_plus"},
        headers=headers,
    )
    assert change.status_code == 200
    assert change.json()["plan"] == "pro_plus"

    invoices = await client.get("/api/v1/companies/me/subscription/invoices", headers=headers)
    renewals = await client.get("/api/v1/companies/me/subscription/renewals", headers=headers)
    assert invoices.status_code == 200
    assert renewals.status_code == 200
    assert len(invoices.json()["items"]) == 1
    assert len(renewals.json()["items"]) == 1


@pytest.mark.asyncio
async def test_webhook_delivery_created_from_payment_event(client, manager, payment_submitted, staff_headers, monkeypatch):
    monkeypatch.setattr("apps.integrations.service.httpx.AsyncClient", lambda *args, **kwargs: FakeWebhookClient())
    headers = staff_headers(manager)

    created = await client.post(
        "/api/v1/integrations/webhooks",
        json={
            "name": "ERP Listener",
            "target_url": "https://example.test/webhook",
            "events": ["payment.confirmed"],
            "secret": "hook-secret",
            "is_active": True,
        },
        headers=headers,
    )
    assert created.status_code == 200

    confirmed = await client.post(
        f"/api/v1/payments/{payment_submitted.id}/confirm",
        json={"confirmed": True},
        headers=headers,
    )
    assert confirmed.status_code == 200

    deliveries = await client.get("/api/v1/integrations/webhooks/deliveries", headers=headers)
    assert deliveries.status_code == 200
    assert any(item["event_type"] == "payment.confirmed" for item in deliveries.json()["items"])
