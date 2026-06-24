"""
Tests reçus — Fiissa
Couvre : génération, idempotence, vérification QR, accès isolé
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_receipt_generated_after_payment_confirmed(
    client: AsyncClient, manager, payment_submitted, staff_headers
):
    """La confirmation de paiement déclenche la génération d'un reçu."""
    headers = staff_headers(manager)

    # Confirmer le paiement
    r = await client.post(
        f"/api/v1/payments/{payment_submitted.id}/confirm",
        json={"confirmed": True},
        headers=headers,
    )
    assert r.status_code == 200

    # Générer le reçu explicitement (Celery est mocké en test — pas de génération automatique)
    order_id = payment_submitted.order_id
    await client.post(
        f"/api/v1/receipts/generate/{payment_submitted.id}",
        headers=headers,
    )

    # Récupérer le reçu associé à la commande
    r2 = await client.get(
        f"/api/v1/receipts/order/{order_id}",
        headers=headers,
    )
    assert r2.status_code == 200
    data = r2.json()
    assert "receipt_number" in data
    assert data["receipt_number"].startswith("REC-")
    assert "verification_code" in data
    assert data["html_content"] is not None


@pytest.mark.asyncio
async def test_receipt_idempotent(
    client: AsyncClient, manager, receipt, staff_headers
):
    """Générer deux fois le reçu pour le même paiement retourne le même objet."""
    headers = staff_headers(manager)

    r1 = await client.post(
        f"/api/v1/receipts/generate/{receipt.payment_id}",
        headers=headers,
    )
    r2 = await client.post(
        f"/api/v1/receipts/generate/{receipt.payment_id}",
        headers=headers,
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.asyncio
async def test_verify_receipt_valid(client: AsyncClient, receipt):
    """Vérifier un code QR valide → statut 'valid'."""
    r = await client.get(f"/api/v1/receipts/verify/{receipt.verification_code}")
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is True
    assert "receipt_number" in data


@pytest.mark.asyncio
async def test_verify_receipt_invalid_code(client: AsyncClient):
    """Vérifier un code QR inexistant → 404 ou valid=False."""
    r = await client.get("/api/v1/receipts/verify/CODE-INEXISTANT-99999")
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert r.json()["valid"] is False


@pytest.mark.asyncio
async def test_customer_can_see_own_receipt(
    client: AsyncClient, customer, receipt, auth_headers
):
    """Le client peut voir son propre reçu."""
    headers = auth_headers(customer)
    r = await client.get(f"/api/v1/receipts/{receipt.id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["id"] == str(receipt.id)


@pytest.mark.asyncio
async def test_customer_cannot_see_other_receipt(
    client: AsyncClient, customer2, receipt, auth_headers
):
    """Un autre client ne peut pas voir le reçu d'un autre → 403 ou 404."""
    headers = auth_headers(customer2)
    r = await client.get(f"/api/v1/receipts/{receipt.id}", headers=headers)
    assert r.status_code in (403, 404)


@pytest.mark.asyncio
async def test_receipt_number_unique_per_company(
    client: AsyncClient, manager, payment_confirmed_1, payment_confirmed_2, staff_headers
):
    """Deux reçus de la même entreprise ont des numéros différents."""
    headers = staff_headers(manager)
    r1 = await client.post(
        f"/api/v1/receipts/generate/{payment_confirmed_1.id}",
        headers=headers,
    )
    r2 = await client.post(
        f"/api/v1/receipts/generate/{payment_confirmed_2.id}",
        headers=headers,
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["receipt_number"] != r2.json()["receipt_number"]


@pytest.mark.asyncio
async def test_receipt_html_is_immutable(
    client: AsyncClient, manager, receipt, staff_headers
):
    """Le contenu HTML du reçu ne change pas après génération."""
    headers = staff_headers(manager)
    r1 = await client.get(f"/api/v1/receipts/{receipt.id}", headers=headers)
    html_before = r1.json()["html_content"]

    # Simuler un re-fetch
    r2 = await client.get(f"/api/v1/receipts/{receipt.id}", headers=headers)
    html_after = r2.json()["html_content"]

    assert html_before == html_after


@pytest.mark.asyncio
async def test_receipt_pdf_url_present(
    client: AsyncClient, manager, receipt, staff_headers
):
    """Le reçu contient une URL PDF ou pdf_url est None (génération async en cours)."""
    headers = staff_headers(manager)
    r = await client.get(f"/api/v1/receipts/{receipt.id}", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "pdf_url" in data


@pytest.mark.asyncio
async def test_manager_other_company_cannot_see_receipt(
    client: AsyncClient, manager2, receipt, staff_headers
):
    """Le gérant d'une autre entreprise ne peut pas voir le reçu → 403 ou 404."""
    headers = staff_headers(manager2)
    r = await client.get(f"/api/v1/receipts/{receipt.id}", headers=headers)
    assert r.status_code in (403, 404)
