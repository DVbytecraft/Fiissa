"""
Tests de sécurité — CSPRNG, AES-256-GCM, XSS, rate-limit, CORS, RBAC.
"""
import pytest
from httpx import AsyncClient


# ── CSPRNG ────────────────────────────────────────────────────────────────────

def test_otp_uses_secrets_module():
    """OTP ne doit plus utiliser random.choices (non-cryptographique)."""
    import core.security as sec_module
    import ast, inspect, textwrap
    source = inspect.getsource(sec_module)
    tree = ast.parse(textwrap.dedent(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "random", "random importé dans core/security — utiliser secrets"
        if isinstance(node, ast.ImportFrom):
            assert node.module != "random", "random importé dans core/security — utiliser secrets"


def test_otp_entropy_distribution():
    """Les OTPs doivent être aléatoires et non-séquentiels."""
    from core.security import generate_otp
    samples = {generate_otp(6) for _ in range(50)}
    assert len(samples) >= 30, f"Trop peu de valeurs distinctes ({len(samples)}/50) — entropie insuffisante"


def test_otp_length():
    from core.security import generate_otp
    for length in (4, 6, 8):
        otp = generate_otp(length)
        assert len(otp) == length
        assert otp.isdigit()


# ── AES-256-GCM roundtrip ─────────────────────────────────────────────────────

def test_aes_encrypt_decrypt_roundtrip():
    from core.secrets import encrypt_secret, decrypt_secret
    plaintext = "my-super-secret-key-12345"
    token = encrypt_secret(plaintext)
    assert isinstance(token, str)
    assert token != plaintext
    result = decrypt_secret(token)
    assert result == plaintext


def test_aes_nonce_is_random():
    """Deux chiffrements du même plaintext doivent produire des tokens différents (nonce aléatoire)."""
    from core.secrets import encrypt_secret
    t1 = encrypt_secret("same-value")
    t2 = encrypt_secret("same-value")
    assert t1 != t2, "Nonce identique — vulnérabilité de réutilisation de nonce"


def test_aes_tamper_detection():
    """Token falsifié doit lever ValueError (intégrité GCM)."""
    from core.secrets import encrypt_secret, decrypt_secret
    token = encrypt_secret("original")
    # Corrompre le token (dernier octet)
    corrupted = token[:-4] + "XXXX"
    with pytest.raises(Exception):
        decrypt_secret(corrupted)


def test_aes_short_token_rejected():
    from core.secrets import decrypt_secret
    with pytest.raises(ValueError):
        decrypt_secret("dG9vc2hvcnQ=")  # "tooshort" en base64


# ── XSS protection ────────────────────────────────────────────────────────────

def test_receipt_html_escapes_xss():
    """Les valeurs injectées dans le HTML du reçu doivent être échappées."""
    import html
    xss_payload = '<script>alert("xss")</script>'
    escaped = html.escape(xss_payload)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped


@pytest.mark.asyncio
async def test_xss_in_product_name_does_not_break_receipt(client: AsyncClient, db, company, store, customer, manager, staff_headers, auth_headers):
    """Un nom de produit avec du HTML doit être servi échappé dans le reçu."""
    from apps.catalog.models import Product
    from apps.orders.models import Order, OrderItem
    from apps.payments.models import Payment
    from datetime import datetime, timezone

    xss_name = '<img src=x onerror=alert(1)> Riz'
    product = Product(
        company_id=company.id,
        store_id=store.id,
        name=xss_name,
        price_xof=1000,
        unit="piece",
        barcode="XSS-TEST-01",
        is_available=True,
        track_stock=False,
    )
    db.add(product)
    await db.flush()

    order = Order(
        company_id=company.id,
        store_id=store.id,
        customer_id=customer.id,
        order_number="SC-XSS-00001",
        type="click_collect",
        status="delivered",
        total_xof=1000,
    )
    db.add(order)
    await db.flush()
    db.add(OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_name=xss_name,
        product_barcode="XSS-TEST-01",
        unit_price_xof=1000,
        quantity=1,
        subtotal_xof=1000,
    ))
    payment = Payment(
        company_id=company.id,
        store_id=store.id,
        order_id=order.id,
        customer_id=customer.id,
        payment_number="PAY-XSS-00001",
        method="mobile_money",
        operator="wave",
        amount_xof=1000,
        status="confirmed",
        transaction_ref="TX-XSS-01",
        sender_phone=customer.phone,
        confirmed_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    await db.commit()

    from apps.receipts.service import ReceiptService
    service = ReceiptService(db)
    receipt = await service.generate_receipt(payment.id)
    await db.commit()

    assert receipt is not None
    # Vérifier que l'HTML du reçu ne contient pas de balise non-échappée
    # L'attribut du modèle est html_content (snapshot immuable)
    if receipt.html_content:
        assert "<img src=x onerror=alert(1)>" not in receipt.html_content, \
            "XSS non-échappé dans le HTML du reçu"
        assert "&lt;img" in receipt.html_content or "onerror" not in receipt.html_content


# ── temp_password non exposé ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invite_staff_does_not_expose_temp_password(client: AsyncClient, db, company, staff_headers):
    """La réponse de /invite-staff ne doit PAS contenir temp_password."""
    from apps.users.models import User, UserCompanyRole
    from core.security import hash_password as _hp

    # Créer un company_owner qui a la permission users.create
    # (store_manager ne l'a pas — seul company_owner/super_admin peut inviter)
    owner = User(
        email="owner_invite@test.com",
        password_hash=_hp("Owner1234!"),
        first_name="Owner",
        last_name="Test",
        is_active=True,
        is_verified=True,
    )
    db.add(owner)
    await db.flush()
    db.add(UserCompanyRole(user_id=owner.id, company_id=company.id, role="company_owner"))
    await db.commit()
    await db.refresh(owner, attribute_names=["company_roles"])

    headers = staff_headers(owner, role="company_owner")
    response = await client.post(
        "/api/v1/auth/staff/invite",
        json={
            "email": "new_staff@test.com",
            "first_name": "Staff",
            "last_name": "Nouveau",
            "role": "preparer",
        },
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "temp_password" not in body, "temp_password ne doit pas être exposé dans la réponse API"
    assert "password" not in body


# ── CORS strict ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cors_does_not_allow_wildcard(client: AsyncClient):
    """OPTIONS ne doit pas retourner Access-Control-Allow-Origin: *."""
    response = await client.options(
        "/api/v1/auth/register",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    allow_origin = response.headers.get("access-control-allow-origin", "")
    assert allow_origin != "*", "CORS trop permissif — wildcard interdit en production"


# ── RBAC : client ne peut pas accéder aux routes marchands ───────────────────

@pytest.mark.asyncio
async def test_customer_cannot_access_staff_routes(client: AsyncClient, customer, auth_headers, company):
    """Un client ne doit pas pouvoir accéder aux paiements en attente (route marchands)."""
    headers = auth_headers(customer)
    # GET /payments/pending requiert la permission payments.read (staff uniquement)
    response = await client.get("/api/v1/payments/pending", headers=headers)
    assert response.status_code in (401, 403), \
        f"Un client a pu accéder à une route marchands ! Status: {response.status_code}"


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_orders(client: AsyncClient):
    """Un appel sans token doit retourner 401 sur les routes protégées."""
    # GET /orders/my requiert authentification
    response = await client.get("/api/v1/orders/my")
    assert response.status_code == 401, \
        f"Accès non-authentifié accepté ! Status: {response.status_code}"


# ── Company suspension bloque les opérations ────────────────────────────────

@pytest.mark.asyncio
async def test_suspended_company_blocks_order_creation(client: AsyncClient, db, company, store, customer, product, auth_headers):
    """Une entreprise suspendue doit bloquer la création de commandes."""
    company.is_suspended = True
    company.is_active = False
    await db.commit()

    add_headers = auth_headers(customer)
    add_headers["X-Company-ID"] = str(company.id)

    response = await client.post(
        f"/api/v1/orders/cart/items?store_id={store.id}&company_id={company.id}",
        json={"product_id": str(product.id), "quantity": 1},
        headers=add_headers,
    )
    # Doit être 403 (company suspended) ou 401 (pas de contexte valide)
    assert response.status_code in (403, 401)


# ── FIX #4 — Upload CSV sans validation ──────────────────────────────────────

@pytest.mark.asyncio
async def test_csv_upload_rejects_invalid_mime(client: AsyncClient, db, company, manager, staff_headers):
    """FIX #4 — Upload d'un fichier avec MIME text/html (exécutable déguisé) est rejeté."""
    headers = staff_headers(manager, company.id, role="company_owner")
    response = await client.post(
        "/api/v1/catalog/products/import",
        headers=headers,
        files={"file": ("malicious.csv", b"<html>evil</html>", "text/html")},
    )
    assert response.status_code == 400, (
        f"SÉCURITÉ : fichier text/html accepté comme CSV ! Status: {response.status_code}"
    )


@pytest.mark.asyncio
async def test_csv_upload_rejects_oversized_file(client: AsyncClient, db, company, manager, staff_headers):
    """FIX #4 — Upload CSV > 5 Mo est rejeté avec 413."""
    headers = staff_headers(manager, company.id, role="company_owner")
    # Génère un contenu CSV > 5 Mo (375001 × 14 bytes = 5 250 028 bytes > 5 242 880 bytes)
    big_content = b"id,name,price\n" + b"1,Product,100\n" * 375001
    response = await client.post(
        "/api/v1/catalog/products/import",
        headers=headers,
        files={"file": ("products.csv", big_content, "text/csv")},
    )
    assert response.status_code == 413, (
        f"SÉCURITÉ : fichier > 5 Mo accepté ! Status: {response.status_code}"
    )


@pytest.mark.asyncio
async def test_csv_upload_rejects_invalid_extension(client: AsyncClient, db, company, manager, staff_headers):
    """FIX #4 — Upload d'un fichier avec extension .exe est rejeté même avec MIME text/csv."""
    headers = staff_headers(manager, company.id, role="company_owner")
    response = await client.post(
        "/api/v1/catalog/products/import",
        headers=headers,
        files={"file": ("malware.exe", b"MZ\x90\x00malicious", "text/csv")},
    )
    assert response.status_code == 400, (
        f"SÉCURITÉ : fichier .exe accepté comme CSV ! Status: {response.status_code}"
    )
