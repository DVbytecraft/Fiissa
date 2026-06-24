"""
Tests paiements Mobile Money — Fiissa
Couvre : création, soumission preuve, confirmation, rejet, double paiement, déjà confirmé
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_payment(client: AsyncClient, customer, order, auth_headers):
    """Créer un paiement pour une commande en attente."""
    headers = auth_headers(customer)
    response = await client.post(
        "/api/v1/payments/",
        json={"order_id": str(order.id), "operator": "wave"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending_proof"
    assert data["operator"] == "wave"
    assert "payment_number" in data


@pytest.mark.asyncio
async def test_create_payment_idempotent(client: AsyncClient, customer, order, auth_headers):
    """Créer deux fois un paiement pour la même commande retourne le même objet."""
    headers = auth_headers(customer)
    payload = {"order_id": str(order.id), "operator": "wave"}
    r1 = await client.post("/api/v1/payments/", json=payload, headers=headers)
    r2 = await client.post("/api/v1/payments/", json=payload, headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.asyncio
async def test_submit_payment_proof(client: AsyncClient, customer, order, payment, auth_headers):
    """Soumettre une preuve de paiement."""
    headers = auth_headers(customer)
    response = await client.post(
        f"/api/v1/payments/{payment.id}/submit-proof",
        json={
            "transaction_ref": "WAVE-TX-12345",
            "sender_phone": "+221771234567",
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pending_verification"


@pytest.mark.asyncio
async def test_duplicate_payment_ref_rejected(client: AsyncClient, customer, store, company, auth_headers):
    """Deux commandes avec la même référence transaction → 409."""
    from tests.conftest import create_order_with_payment

    headers = auth_headers(customer)
    order1, pay1 = await create_order_with_payment(client, customer, store, company)
    order2, pay2 = await create_order_with_payment(client, customer, store, company)

    same_ref = "WAVE-TX-DUPLICATE-99"

    r1 = await client.post(
        f"/api/v1/payments/{pay1.id}/submit-proof",
        json={"transaction_ref": same_ref, "sender_phone": "+221770000001"},
        headers=headers,
    )
    assert r1.status_code == 200

    r2 = await client.post(
        f"/api/v1/payments/{pay2.id}/submit-proof",
        json={"transaction_ref": same_ref, "sender_phone": "+221770000002"},
        headers=headers,
    )
    assert r2.status_code == 409
    # Le handler SmartCheckoutException retourne {"code": "...", "message": "..."} (pas {"detail": {...}})
    assert r2.json()["code"] == "duplicate_payment_ref"


@pytest.mark.asyncio
async def test_confirm_payment(client: AsyncClient, manager, payment_submitted, staff_headers):
    """Le gérant peut confirmer un paiement soumis."""
    headers = staff_headers(manager)
    response = await client.post(
        f"/api/v1/payments/{payment_submitted.id}/confirm",
        json={"confirmed": True},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"


@pytest.mark.asyncio
async def test_payment_already_confirmed_rejected(
    client: AsyncClient, manager, payment_confirmed, staff_headers
):
    """Confirmer un paiement déjà confirmé → 409."""
    headers = staff_headers(manager)
    response = await client.post(
        f"/api/v1/payments/{payment_confirmed.id}/confirm",
        json={"confirmed": True},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "payment_already_confirmed"


@pytest.mark.asyncio
async def test_reject_payment_requires_reason(
    client: AsyncClient, manager, payment_submitted, staff_headers
):
    """Rejeter un paiement sans raison → 422."""
    headers = staff_headers(manager)
    r = await client.post(
        f"/api/v1/payments/{payment_submitted.id}/confirm",
        json={"confirmed": False},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_reject_payment_with_reason(
    client: AsyncClient, manager, payment_submitted, staff_headers
):
    """Rejeter un paiement avec une raison valide → succès."""
    headers = staff_headers(manager)
    r = await client.post(
        f"/api/v1/payments/{payment_submitted.id}/confirm",
        json={"confirmed": False, "reason": "Référence introuvable"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_customer_cannot_confirm_payment(
    client: AsyncClient, customer, payment_submitted, auth_headers
):
    """Un client ne peut pas confirmer un paiement → 403."""
    headers = auth_headers(customer)
    r = await client.post(
        f"/api/v1/payments/{payment_submitted.id}/confirm",
        json={"confirmed": True},
        headers=headers,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_manager_other_company_cannot_confirm(
    client: AsyncClient, manager2, payment_submitted, staff_headers
):
    """Le gérant d'une autre entreprise ne peut pas confirmer → 403 ou 404."""
    headers = staff_headers(manager2)
    r = await client.post(
        f"/api/v1/payments/{payment_submitted.id}/confirm",
        json={"confirmed": True},
        headers=headers,
    )
    assert r.status_code in (403, 404)


@pytest.mark.asyncio
async def test_get_pending_payments(client: AsyncClient, manager, payment_submitted, staff_headers):
    """Le gérant peut voir la liste des paiements en attente."""
    headers = staff_headers(manager)
    r = await client.get("/api/v1/payments/pending", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(p["id"] == str(payment_submitted.id) for p in data)
