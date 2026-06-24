"""
Scenarios E2E — Fiissa / SmartCheckout
=======================================
Chaque test couvre un flux complet de bout en bout avec tracage
de chaque requete/reponse. Preuve d'execution = logs captures.

Conventions de log :
    [STEP N] URL -> HTTP STATUS | cle=valeur
    [OK]     Assertion passee
"""

import io
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient


# ─────────────────────────────────────────────────────────────────────────────
# Helper de trace
# ─────────────────────────────────────────────────────────────────────────────

def _log(step: str, url: str, status: int, data: dict | None = None):
    summary = ""
    if data:
        parts = []
        for k in ("id", "order_number", "payment_number", "receipt_number",
                  "status", "code", "message", "verification_code", "debug_code",
                  "job_id", "total_rows", "created_count"):
            if k in data:
                parts.append(f"{k}={data[k]}")
        summary = " | " + ", ".join(parts) if parts else ""
    print(f"  [{step}] {url} -> HTTP {status}{summary}")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 1 — Inscription -> OTP -> Panier -> Commande -> Paiement -> Recu
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_full_customer_journey(
    client: AsyncClient, db, company, store, product, manager, staff_headers
):
    """
    Flux complet : nouveau client s'inscrit, commande, paie, reçoit son recu.
    Note : debug_code retourne l'OTP en mode development (pas d'email reel).
    """
    print("\n=== SCENARIO 1 : Parcours client complet ===")

    phone = "+221771000001"

    # Etape 1 : Inscription (email obligatoire depuis Sprint 1)
    r = await client.post("/api/v1/auth/register", json={
        "phone": phone,
        "email": "fatou.e2e@example.com",
        "password": "StrongPass123!",
        "first_name": "Fatou",
        "last_name": "Diallo",
    })
    _log("1 REGISTER", "/auth/register", r.status_code, r.json())
    assert r.status_code == 200, f"Register failed: {r.text}"
    otp_code = r.json().get("debug_code")
    assert otp_code, "debug_code absent (requis en mode development)"

    # Etape 2 : Verification OTP
    r = await client.post("/api/v1/auth/login/verify-otp",
                          json={"email": "fatou.e2e@example.com", "code": otp_code})
    _log("2 VERIFY_OTP", "/auth/login/verify-otp", r.status_code)
    assert r.status_code == 200, f"OTP verify failed: {r.text}"
    token = r.json()["access_token"]
    # Note : PAS de X-Company-ID pour les clients — company_id passe en query/body
    c_headers = {"Authorization": f"Bearer {token}"}
    print(f"  [OK] Token JWT obtenu")

    # Etape 3 : Ajout panier (company_id en query param, pas en header)
    r = await client.post(
        f"/api/v1/orders/cart/items?store_id={store.id}&company_id={company.id}",
        json={"product_id": str(product.id), "quantity": 2},
        headers=c_headers,
    )
    _log("3 ADD_CART", "/orders/cart/items", r.status_code, r.json())
    assert r.status_code == 200, f"Add to cart failed: {r.text}"

    # Etape 4 : Creation commande
    r = await client.post(
        "/api/v1/orders/",
        json={"store_id": str(store.id), "company_id": str(company.id), "order_type": "click_collect"},
        headers=c_headers,
    )
    _log("4 CREATE_ORDER", "/orders/", r.status_code, r.json())
    assert r.status_code == 200, f"Create order failed: {r.text}"
    order = r.json()
    assert order["order_number"].startswith("SC-")
    assert order["status"] in ("awaiting_payment", "pending")

    # Etape 5 : Creation paiement
    r = await client.post(
        "/api/v1/payments/",
        json={"order_id": order["id"], "operator": "wave"},
        headers=c_headers,
    )
    _log("5 CREATE_PAYMENT", "/payments/", r.status_code, r.json())
    assert r.status_code == 200, f"Create payment failed: {r.text}"
    payment = r.json()
    assert payment["payment_number"].startswith("PAY-")
    assert "instructions" in payment

    # Etape 6 : Soumission preuve
    r = await client.post(
        f"/api/v1/payments/{payment['id']}/submit-proof",
        json={"transaction_ref": "WAVE-TX-E2E-001", "sender_phone": phone},
        headers=c_headers,
    )
    _log("6 SUBMIT_PROOF", "submit-proof", r.status_code, r.json())
    assert r.status_code == 200, f"Submit proof failed: {r.text}"

    # Etape 7 : Confirmation gerant
    mgr_headers = staff_headers(manager)
    r = await client.post(
        f"/api/v1/payments/{payment['id']}/confirm",
        json={"confirmed": True},
        headers=mgr_headers,
    )
    _log("7 CONFIRM_PAYMENT", "confirm", r.status_code, r.json())
    assert r.status_code == 200, f"Confirm payment failed: {r.text}"
    assert r.json()["status"] == "confirmed"

    # Etape 8 : Generation recu
    r = await client.post(
        f"/api/v1/receipts/generate/{payment['id']}",
        headers=mgr_headers,
    )
    _log("8 GENERATE_RECEIPT", "generate", r.status_code, r.json())
    assert r.status_code in (200, 201), f"Generate receipt failed: {r.text}"
    receipt = r.json()
    assert receipt["receipt_number"].startswith("REC-")
    assert receipt["html_content"] is not None
    verification_code = receipt["verification_code"]

    # Etape 9 : Recuperation recu par commande
    r = await client.get(f"/api/v1/receipts/order/{order['id']}", headers=mgr_headers)
    _log("9 GET_RECEIPT_BY_ORDER", f"/receipts/order/{order['id']}", r.status_code)
    assert r.status_code == 200
    assert r.json()["receipt_number"] == receipt["receipt_number"]

    # Etape 9b-9d : Transition confirmed -> preparing -> ready -> delivered
    # La machine d'etat n'autorise pas de sauter les etapes
    for status in ("preparing", "ready", "delivered"):
        r = await client.patch(
            f"/api/v1/orders/{order['id']}/status",
            json={"status": status},
            headers=mgr_headers,
        )
        _log(f"9x {status}", f"status={status}", r.status_code)
        assert r.status_code == 200, f"Transition -> {status} failed: {r.text}"

    # Etape 10 : Verification QR (sans auth — route publique)
    r = await client.get(f"/api/v1/receipts/verify/{verification_code}")
    _log("10 VERIFY_QR", f"/receipts/verify/{verification_code}", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json()["valid"] is True

    print(f"  [OK] SCENARIO 1 COMPLET — {receipt['receipt_number']} verifie par QR")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 2 — Scan & Go : barcode -> commande directe -> paiement -> recu
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_scan_go_full_flow(
    client: AsyncClient, db, company, store, product, customer, manager,
    auth_headers, staff_headers
):
    """
    Flux Scan & Go : commande directe depuis barcodes scannes, sans panier.
    """
    print("\n=== SCENARIO 2 : Scan & Go ===")

    # Les clients passent company_id en body ou query — PAS en X-Company-ID header
    c_headers = auth_headers(customer)
    mgr_headers = staff_headers(manager)

    # Etape 1 : Commande Scan & Go
    r = await client.post(
        "/api/v1/orders/scan-go",
        json={
            "store_id": str(store.id),
            "company_id": str(company.id),
            "items": [{"barcode": product.barcode, "quantity": 1}],
        },
        headers=c_headers,
    )
    _log("1 SCAN_GO_ORDER", "/orders/scan-go", r.status_code, r.json())
    assert r.status_code == 200, f"Scan-go failed: {r.text}"
    sg_order = r.json()
    assert sg_order["type"] == "scan_go"
    assert "pickup_code" in sg_order
    print(f"  [OK] Commande {sg_order['order_number']} — code retrait: {sg_order['pickup_code']}")

    # Etape 2 : Paiement
    r = await client.post(
        "/api/v1/payments/",
        json={"order_id": sg_order["id"], "operator": "orange_money"},
        headers=c_headers,
    )
    _log("2 CREATE_PAYMENT", "/payments/", r.status_code, r.json())
    assert r.status_code == 200
    payment = r.json()

    # Etape 3 : Soumission preuve
    r = await client.post(
        f"/api/v1/payments/{payment['id']}/submit-proof",
        json={"transaction_ref": "OM-TX-SCAN-001", "sender_phone": customer.phone},
        headers=c_headers,
    )
    _log("3 SUBMIT_PROOF", "submit-proof", r.status_code)
    assert r.status_code == 200

    # Etape 4 : Confirmation
    r = await client.post(
        f"/api/v1/payments/{payment['id']}/confirm",
        json={"confirmed": True},
        headers=mgr_headers,
    )
    _log("4 CONFIRM", "confirm", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

    # Etape 5 : Recu
    r = await client.post(
        f"/api/v1/receipts/generate/{payment['id']}",
        headers=mgr_headers,
    )
    _log("5 RECEIPT", "generate", r.status_code, r.json())
    assert r.status_code in (200, 201)
    assert r.json()["receipt_number"].startswith("REC-")

    print(f"  [OK] SCENARIO 2 COMPLET — Scan & Go {sg_order['order_number']}")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 3 — Marchand cree un produit -> client le trouve par barcode
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_merchant_creates_product_customer_scans(
    client: AsyncClient, db, company, store, customer, manager,
    auth_headers, staff_headers
):
    """
    Le gerant cree un produit via API, le client le retrouve par barcode.
    Note : POST /catalog/products retourne uniquement {id, name}.
    """
    print("\n=== SCENARIO 3 : Marchand cree produit -> scan client ===")

    mgr_headers = staff_headers(manager)
    new_barcode = "E2E-BARCODE-CUSTOM-001"

    # Etape 1 : Gerant cree le produit
    r = await client.post(
        "/api/v1/catalog/products",
        json={
            "name": "Huile Vegetale 1L",
            "price_xof": 1200,
            "unit": "bouteille",
            "barcode": new_barcode,
            "store_id": str(store.id),
            "is_available": True,
            "track_stock": False,
        },
        headers=mgr_headers,
    )
    _log("1 CREATE_PRODUCT", "/catalog/products", r.status_code, r.json())
    assert r.status_code in (200, 201), f"Create product failed: {r.text}"
    created = r.json()
    # La route retourne uniquement {id, name}
    assert "id" in created
    product_id = created["id"]
    print(f"  [OK] Produit cree : id={product_id}, name={created['name']}")

    # Etape 2 : Client resout par barcode
    c_headers = auth_headers(customer)
    r = await client.get(
        f"/api/v1/catalog/products/barcode/{new_barcode}?store_id={store.id}&company_id={company.id}",
        headers=c_headers,
    )
    _log("2 RESOLVE_BARCODE", f"/catalog/products/barcode/{new_barcode}", r.status_code,
         r.json() if r.status_code == 200 else {})
    assert r.status_code == 200, f"Barcode resolution failed: {r.text}"
    resolved = r.json()
    assert resolved["name"] == "Huile Vegetale 1L"
    assert resolved["price_xof"] == 1200
    assert resolved["source"] == "internal"

    print(f"  [OK] SCENARIO 3 COMPLET — {new_barcode} -> {resolved['name']} ({resolved['price_xof']} XOF)")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 4 — Import CSV -> scan barcode
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_csv_import_then_scan(
    client: AsyncClient, db, company, store, customer, manager,
    auth_headers, staff_headers
):
    """
    Gerant importe un catalogue CSV -> client scanne un barcode du CSV.
    Colonnes requises : barcode, name, price_xof, stock_quantity, category, unit, is_available
    """
    print("\n=== SCENARIO 4 : Import CSV -> scan ===")

    mgr_headers = staff_headers(manager)

    # Etape 1 : CSV avec toutes les colonnes requises
    csv_content = (
        "barcode,name,price_xof,stock_quantity,category,unit,is_available\n"
        "CSV-PROD-001,Farine 1kg,850,100,Epicerie,paquet,true\n"
        "CSV-PROD-002,Sucre 1kg,650,200,Epicerie,paquet,true\n"
        "CSV-PROD-003,Sel 500g,250,300,Epicerie,sachet,true\n"
    )
    csv_bytes = csv_content.encode("utf-8")

    r = await client.post(
        f"/api/v1/catalog/products/import-csv?store_id={store.id}",
        files={"file": ("catalog.csv", csv_bytes, "text/csv")},
        headers=mgr_headers,
    )
    _log("1 CSV_IMPORT", "/catalog/products/import-csv", r.status_code,
         r.json() if r.status_code in (200, 201) else {"error": r.text[:120]})
    assert r.status_code in (200, 201), f"CSV import failed: {r.text}"
    job = r.json()
    assert job["status"] == "completed"
    assert job["created_count"] >= 3
    print(f"  [OK] Import job={job['job_id']} — {job['created_count']} produits crees")

    # Etape 2 : Client scanne un barcode importe
    c_headers = auth_headers(customer)
    r = await client.get(
        f"/api/v1/catalog/products/barcode/CSV-PROD-001?store_id={store.id}&company_id={company.id}",
        headers=c_headers,
    )
    _log("2 SCAN_CSV", "/catalog/products/barcode/CSV-PROD-001", r.status_code,
         r.json() if r.status_code == 200 else {})
    assert r.status_code == 200, f"CSV barcode resolution failed: {r.text}"
    resolved = r.json()
    assert resolved["name"] == "Farine 1kg"
    assert resolved["price_xof"] == 850
    assert resolved["source"] in ("internal", "csv_import")

    print(f"  [OK] SCENARIO 4 COMPLET — CSV importe, CSV-PROD-001 -> {resolved['name']}")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 5 — Paiement refuse -> commande reste ouverte
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_payment_rejected(
    client: AsyncClient, db, company, store, product, customer, manager,
    auth_headers, staff_headers
):
    """
    Client soumet une preuve -> gerant rejette -> commande maintenue.
    """
    print("\n=== SCENARIO 5 : Paiement refuse ===")

    c_headers = auth_headers(customer)
    mgr_headers = staff_headers(manager)

    # Panier + commande
    await client.post(
        f"/api/v1/orders/cart/items?store_id={store.id}&company_id={company.id}",
        json={"product_id": str(product.id), "quantity": 1},
        headers=c_headers,
    )
    r = await client.post(
        "/api/v1/orders/",
        json={"store_id": str(store.id), "company_id": str(company.id), "order_type": "click_collect"},
        headers=c_headers,
    )
    assert r.status_code == 200
    order = r.json()
    _log("1 ORDER", "/orders/", r.status_code, order)

    # Paiement
    r = await client.post(
        "/api/v1/payments/",
        json={"order_id": order["id"], "operator": "wave"},
        headers=c_headers,
    )
    assert r.status_code == 200
    payment = r.json()
    _log("2 PAYMENT", "/payments/", r.status_code, payment)

    # Soumission preuve
    r = await client.post(
        f"/api/v1/payments/{payment['id']}/submit-proof",
        json={"transaction_ref": "WAVE-FAKE-9999", "sender_phone": customer.phone},
        headers=c_headers,
    )
    assert r.status_code == 200
    _log("3 SUBMIT_PROOF", "submit-proof", r.status_code)

    # Rejet par le gerant (champ : "reason", pas "rejection_reason")
    r = await client.post(
        f"/api/v1/payments/{payment['id']}/confirm",
        json={"confirmed": False, "reason": "Reference transaction introuvable"},
        headers=mgr_headers,
    )
    _log("4 REJECT_PAYMENT", "confirm(reject)", r.status_code, r.json())
    assert r.status_code == 200, f"Reject payment failed: {r.text}"
    resp = r.json()
    assert resp["status"] == "rejected"
    # La raison peut etre dans "reason", "rejection_reason" ou portee par le message
    has_reason = (
        resp.get("reason") is not None
        or resp.get("rejection_reason") is not None
        or "rejet" in resp.get("message", "").lower()
    )
    assert has_reason, f"Raison de rejet absente: {resp}"

    # Commande doit rester non annulee
    r = await client.get(f"/api/v1/orders/{order['id']}", headers=c_headers)
    _log("5 CHECK_ORDER", f"/orders/{order['id']}", r.status_code, r.json())
    assert r.status_code == 200
    order_status = r.json()["status"]
    # Apres rejet, la commande peut etre en awaiting_payment ou payment_rejected
    assert order_status not in ("cancelled", "delivered"), \
        f"La commande ne doit pas etre annulee/livree apres rejet paiement : {order_status}"

    print(f"  [OK] SCENARIO 5 COMPLET — Paiement rejete, commande en statut '{order_status}'")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 6 — Entreprise suspendue -> operations bloquees
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_suspended_company_blocks_all_ops(
    client: AsyncClient, db, company, store, product, customer, manager,
    auth_headers, staff_headers
):
    """
    Une entreprise suspendue bloque les routes staff (qui utilisent X-Company-ID).
    Le check passe par get_tenant_context -> _check_company_not_suspended.
    Note : les routes customer sans X-Company-ID header ne passent pas par ce check.
    """
    print("\n=== SCENARIO 6 : Entreprise suspendue -> operations bloquees ===")

    mgr_headers = staff_headers(manager)

    # Etape 1 : Verifier que le manager fonctionne normalement avant suspension
    r = await client.get("/api/v1/orders/merchant/list", headers=mgr_headers)
    _log("1 BEFORE_SUSPEND_MANAGER", "/orders/merchant/list", r.status_code)
    assert r.status_code == 200, f"Manager devrait avoir acces avant suspension: {r.text}"
    print(f"  [OK] Acces staff OK avant suspension")

    # Etape 2 : Suspendre l'entreprise
    company.is_suspended = True
    company.is_active = False
    await db.commit()
    _log("2 SUSPEND", "DB: company.is_suspended=True", 200)

    # Etape 3 : Tentative acces manager -> doit etre bloquee par X-Company-ID check
    r = await client.get("/api/v1/orders/merchant/list", headers=mgr_headers)
    _log("3 TRY_MANAGER_SUSPENDED", "/orders/merchant/list", r.status_code)
    assert r.status_code in (403, 401), \
        f"Manager devrait etre bloque (company_suspended), got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("code") == "company_suspended", \
        f"Code d'erreur inattendu: {body}"
    print(f"  [OK] Staff bloque (HTTP {r.status_code}, code=company_suspended)")

    # Etape 4 : Reactiver
    company.is_suspended = False
    company.is_active = True
    await db.commit()
    _log("4 REACTIVATE", "DB: company.is_suspended=False", 200)

    # Etape 5 : Le manager peut de nouveau acceder
    r = await client.get("/api/v1/orders/merchant/list", headers=mgr_headers)
    _log("5 RETRY_MANAGER", "/orders/merchant/list", r.status_code)
    assert r.status_code == 200, f"Manager devrait avoir acces apres reactivation: {r.text}"
    print(f"  [OK] Acces staff restaure apres reactivation")

    print(f"  [OK] SCENARIO 6 COMPLET — Suspension bloque staff, reactivation restaure")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 7 — Webhook payment.confirmed delivre
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_webhook_payment_confirmed_delivery(
    client: AsyncClient, db, company, store, product, customer, manager,
    payment_submitted, auth_headers, staff_headers
):
    """
    Enregistrement webhook -> confirmation paiement -> delivery creee.
    Schema : {name, target_url, events}
    """
    print("\n=== SCENARIO 7 : Webhook payment.confirmed ===")

    mgr_headers = staff_headers(manager)

    # Etape 1 : Creer endpoint webhook
    r = await client.post(
        "/api/v1/integrations/webhooks",
        json={
            "name": "Test Webhook E2E",
            "target_url": "https://example.com/webhook",
            "events": ["payment.confirmed"],
        },
        headers=mgr_headers,
    )
    _log("1 CREATE_WEBHOOK", "/integrations/webhooks", r.status_code, r.json())
    assert r.status_code in (200, 201), f"Webhook creation failed: {r.text}"
    webhook = r.json()
    assert "id" in webhook
    print(f"  [OK] Webhook {webhook['id']} cree")

    # Etape 2 : Confirmer le paiement
    r = await client.post(
        f"/api/v1/payments/{payment_submitted.id}/confirm",
        json={"confirmed": True},
        headers=mgr_headers,
    )
    _log("2 CONFIRM_PAYMENT", "confirm", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

    # Etape 3 : Verifier la delivery webhook
    r = await client.get("/api/v1/integrations/webhooks/deliveries", headers=mgr_headers)
    _log("3 LIST_DELIVERIES", "/integrations/webhooks/deliveries", r.status_code)
    assert r.status_code == 200
    body = r.json()
    items = body if isinstance(body, list) else body.get("items", body.get("deliveries", []))
    assert len(items) >= 1, f"Au moins une delivery attendue, {len(items)} trouvee(s)"

    delivery = items[0]
    assert delivery.get("event_type") == "payment.confirmed"
    print(f"  [OK] Delivery creee — event={delivery.get('event_type')}")

    print(f"  [OK] SCENARIO 7 COMPLET — Webhook delivery cree pour payment.confirmed")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 8 — Abonnement expire -> suspension automatique -> reactivation
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_subscription_expiry_suspends_company(db, company):
    """
    L'abonnement expire declenche la suspension de l'entreprise.
    Le job Celery beat suspend_expired_subscriptions est teste ici directement.
    """
    print("\n=== SCENARIO 8 : Abonnement expire -> suspension ===")

    from apps.companies.models import Subscription, Company, SubscriptionInvoice
    from apps.companies.service import SubscriptionService
    from sqlalchemy import select

    # Etape 1 : Recuperer l'abonnement
    result = await db.execute(select(Subscription).where(Subscription.company_id == company.id))
    sub = result.scalar_one_or_none()
    assert sub is not None

    original_status = sub.status
    _log("1 INITIAL_STATE", "DB subscription", 200, {"status": sub.status})

    # Etape 2 : Forcer l'expiration
    sub.status = "active"
    sub.current_period_end = datetime.now(timezone.utc) - timedelta(days=3)
    await db.commit()
    _log("2 SET_EXPIRED", "sub.current_period_end = NOW()-3j", 200)

    # Etape 3 : Executer le job de suspension
    count = await SubscriptionService.suspend_expired_subscriptions(db)
    await db.commit()
    _log("3 RUN_JOB", "suspend_expired_subscriptions()", 200, {"suspended_count": count})
    assert count >= 1, f"Job devrait suspendre >= 1 entreprise, a suspendu {count}"

    # Etape 4 : Verifier l'etat
    await db.refresh(sub)
    result2 = await db.execute(select(Company).where(Company.id == company.id))
    co = result2.scalar_one()
    _log("4 CHECK_STATE", "DB state", 200, {
        "status": sub.status,
        "code": str(co.is_suspended),
    })
    assert sub.status == "suspended"
    assert co.is_suspended is True

    # Etape 5 : Reactiver via paiement de facture
    invoice = SubscriptionInvoice(
        company_id=company.id,
        subscription_id=sub.id,
        invoice_number="INV-E2E-REACTIVATE",
        status="issued",
        amount_xof=15000,
        tax_xof=0,
        total_xof=15000,
    )
    db.add(invoice)
    await db.commit()

    service = SubscriptionService(db)
    paid = await service.mark_invoice_paid(company.id, invoice.id)
    await db.commit()

    await db.refresh(sub)
    result3 = await db.execute(select(Company).where(Company.id == company.id))
    co_r = result3.scalar_one()
    _log("5 REACTIVATE", "mark_invoice_paid()", 200, {
        "status": paid.status,
        "code": sub.status,
    })
    assert paid.status == "paid"
    assert sub.status == "active"
    assert co_r.is_suspended is False

    print(f"  [OK] SCENARIO 8 COMPLET — expiration -> suspension -> reactivation OK")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 9 — Isolation multi-tenant stricte
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_multi_tenant_isolation(
    client: AsyncClient, db, company, company2, store, store2,
    manager, manager2, customer, product, staff_headers, auth_headers
):
    """
    Manager de company2 ne peut pas voir les donnees de company.
    """
    print("\n=== SCENARIO 9 : Isolation multi-tenant ===")

    mgr1_headers = staff_headers(manager)
    mgr2_headers = staff_headers(manager2)
    c_headers = auth_headers(customer)

    # Etape 1 : customer cree une commande dans company
    await client.post(
        f"/api/v1/orders/cart/items?store_id={store.id}&company_id={company.id}",
        json={"product_id": str(product.id), "quantity": 1},
        headers=c_headers,
    )
    r = await client.post(
        "/api/v1/orders/",
        json={"store_id": str(store.id), "company_id": str(company.id), "order_type": "click_collect"},
        headers=c_headers,
    )
    _log("1 CREATE_ORDER_CO1", "/orders/", r.status_code, r.json())
    assert r.status_code == 200
    order_co1_id = r.json()["id"]

    # Etape 2 : Manager1 voit sa commande
    r = await client.get("/api/v1/orders/merchant/list", headers=mgr1_headers)
    _log("2 MANAGER1_LIST", "/orders/merchant/list", r.status_code)
    assert r.status_code == 200
    body = r.json()
    items1 = body if isinstance(body, list) else body.get("items", [])
    assert any(o.get("id") == order_co1_id for o in items1), \
        "Manager1 devrait voir sa commande"
    print(f"  [OK] Manager1 voit {len(items1)} commande(s) de company1")

    # Etape 3 : Manager2 ne voit PAS les commandes de company1
    r = await client.get("/api/v1/orders/merchant/list", headers=mgr2_headers)
    _log("3 MANAGER2_LIST", "/orders/merchant/list", r.status_code)
    assert r.status_code == 200
    body2 = r.json()
    items2 = body2 if isinstance(body2, list) else body2.get("items", [])
    assert not any(o.get("id") == order_co1_id for o in items2), \
        "Manager2 ne doit PAS voir les commandes de company1 — isolation violee!"
    print(f"  [OK] Manager2 voit {len(items2)} commande(s) de company2 (aucune de company1)")

    # Etape 4 : Rapports company2 -> 0 revenus
    r = await client.get("/api/v1/reports/summary", headers=mgr2_headers)
    _log("4 REPORT_CO2", "/reports/summary", r.status_code)
    assert r.status_code == 200
    assert r.json()["orders_count"] == 0, \
        f"Company2 ne devrait avoir 0 commande, a {r.json()['orders_count']}"

    print(f"  [OK] SCENARIO 9 COMPLET — Isolation multi-tenant verifiee")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 10 — Numerotation sequentielle sans collision
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_sequential_numbering_no_collision(
    client: AsyncClient, db, company, store, product, customer,
    manager, auth_headers, staff_headers
):
    """
    5 commandes creees -> numeros SC-YYYY-NNNNN uniques et croissants.
    """
    print("\n=== SCENARIO 10 : Numerotation sans collision ===")

    c_headers = auth_headers(customer)
    order_numbers = []

    for i in range(5):
        # Panier
        await client.post(
            f"/api/v1/orders/cart/items?store_id={store.id}&company_id={company.id}",
            json={"product_id": str(product.id), "quantity": 1},
            headers=c_headers,
        )
        # Commande
        r = await client.post(
            "/api/v1/orders/",
            json={"store_id": str(store.id), "company_id": str(company.id), "order_type": "click_collect"},
            headers=c_headers,
        )
        assert r.status_code == 200, f"Order {i+1} failed: {r.text}"
        num = r.json()["order_number"]
        order_numbers.append(num)
        print(f"  [STEP {i+1}] -> {num}")

    # Unicite
    assert len(set(order_numbers)) == len(order_numbers), \
        f"Doublons detectes : {order_numbers}"

    # Format et progression
    for num in order_numbers:
        assert num.startswith("SC-")
        assert str(datetime.now().year) in num

    seq_parts = [int(n.split("-")[2]) for n in order_numbers]
    assert seq_parts == sorted(seq_parts), f"Numeros non croissants: {seq_parts}"
    print(f"  [OK] SCENARIO 10 COMPLET — sequences: {seq_parts}")
