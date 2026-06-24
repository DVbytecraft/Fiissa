"""
Configuration des tests SmartCheckout.

Stratégie d'isolation :
- Base de données : SQLite en mémoire (aiosqlite) — isolation totale par test
- Redis / Rate-limiting : désactivé via override de la dépendance SlowAPI (memory://)
- Celery : tâches mockées (pas de broker nécessaire)
- WeasyPrint / PDF : fallback silencieux déjà dans le service
- SMS : mode mock (ENVIRONMENT=development)
"""

import asyncio
import os
import sys
from types import SimpleNamespace
from typing import Awaitable, Callable

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# ── Variables d'environnement de test ──────────────────────────────────────────
# IMPORTANT : ces valeurs doivent être définies AVANT tout import du code applicatif
# REDIS_URL = "memory://" → slowapi utilise un backend mémoire, pas Redis
os.environ["SECRET_KEY"] = "test-secret-key-sufficiently-long-32chars"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "memory://"       # slowapi memory backend — pas de Redis requis
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "false"
os.environ["STORAGE_BACKEND"] = "local"

# ── Imports après variables d'env ──────────────────────────────────────────────
from core.database import Base, get_db
from core.security import create_access_token, hash_password
# Import core.sequences pour que DocumentSequence soit enregistré dans Base.metadata
# avant que create_all() soit appelé dans le fixture db (lazy imports dans les services
# ne suffisent pas — le modèle doit être connu avant la création des tables)
import core.sequences  # noqa: F401
# Sprint 2 : loyalty + wallet — modèles doivent être connus avant create_all()
import apps.loyalty.models  # noqa: F401
import apps.wallet.models   # noqa: F401
from main import app
from workers import tasks as worker_tasks

# ── Patch JSONB → JSON pour SQLite ────────────────────────────────────────────
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(_element, _compiler, **_kw):
    return "JSON"

# ── Engine SQLite en mémoire ───────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)
_ACTIVE_TEST_DB: AsyncSession | None = None
sys.modules.setdefault("tests.conftest", sys.modules[__name__])


# Note : le rate limiter utilise REDIS_URL="memory://" défini ci-dessus.
# slowapi/limits supporte "memory://" comme storage URI → pas de Redis requis en test.
# Le storage en mémoire est partagé entre tous les tests d'une session :
# il faut le réinitialiser après chaque test pour éviter des 429 parasites.

@pytest.fixture(autouse=True)
def reset_rate_limiter_storage():
    """Vide le storage en mémoire du rate limiter entre chaque test."""
    yield
    try:
        from core.rate_limit import limiter
        if hasattr(limiter, "_storage") and hasattr(limiter._storage, "reset"):
            limiter._storage.reset()
    except Exception:
        pass


# ── Helpers d'authentification ─────────────────────────────────────────────────

def build_auth_headers(user, role: str = "customer", company_id=None) -> dict:
    token = create_access_token(
        {
            "sub": str(user.id),
            "role": role,
            "company_id": str(company_id) if company_id else None,
        }
    )
    headers = {"Authorization": f"Bearer {token}"}
    if company_id:
        headers["X-Company-ID"] = str(company_id)
    return headers


def auth_headers(user) -> dict:
    return build_auth_headers(user, role="customer")


def staff_headers(user, company_id=None, role: str = "store_manager") -> dict:
    effective_company_id = company_id
    if effective_company_id is None:
        roles = getattr(user, "company_roles", None) or []
        for user_role in roles:
            if getattr(user_role, "company_id", None):
                effective_company_id = user_role.company_id
                break
    return build_auth_headers(user, role=role, company_id=effective_company_id)


@pytest.fixture(name="auth_headers")
def auth_headers_fixture():
    return auth_headers


@pytest.fixture(name="staff_headers")
def staff_headers_fixture():
    return staff_headers


# ── Event loop ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── DB fixture : création/destruction par test ────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def db():
    global _ACTIVE_TEST_DB
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        _ACTIVE_TEST_DB = session
        yield session
        _ACTIVE_TEST_DB = None

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── Client HTTPX ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db: AsyncSession):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Celery : désactivation des side-effects ────────────────────────────────────

@pytest.fixture(autouse=True)
def disable_celery_side_effects():
    originals = {
        "notify_merchant_payment_received": worker_tasks.notify_merchant_payment_received.delay,
        "generate_receipt_pdf": worker_tasks.generate_receipt_pdf.delay,
        "notify_customer_payment_confirmed": worker_tasks.notify_customer_payment_confirmed.delay,
        "notify_customer_payment_rejected": worker_tasks.notify_customer_payment_rejected.delay,
    }
    worker_tasks.notify_merchant_payment_received.delay = lambda *args, **kwargs: None
    worker_tasks.generate_receipt_pdf.delay = lambda *args, **kwargs: None
    worker_tasks.notify_customer_payment_confirmed.delay = lambda *args, **kwargs: None
    worker_tasks.notify_customer_payment_rejected.delay = lambda *args, **kwargs: None
    try:
        yield
    finally:
        worker_tasks.notify_merchant_payment_received.delay = originals["notify_merchant_payment_received"]
        worker_tasks.generate_receipt_pdf.delay = originals["generate_receipt_pdf"]
        worker_tasks.notify_customer_payment_confirmed.delay = originals["notify_customer_payment_confirmed"]
        worker_tasks.notify_customer_payment_rejected.delay = originals["notify_customer_payment_rejected"]


# ── Fixtures utilisateurs ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def super_admin(db: AsyncSession):
    from apps.users.models import User, UserCompanyRole

    user = User(
        email="admin@test.com",
        password_hash=hash_password("Admin1234!"),
        first_name="Super",
        last_name="Admin",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    role = UserCompanyRole(user_id=user.id, role="super_admin")
    db.add(role)
    await db.commit()
    await db.refresh(user, attribute_names=["company_roles"])
    return user


@pytest_asyncio.fixture
async def company(db: AsyncSession):
    from apps.companies.models import Company, Subscription

    company = Company(
        name="Supermarche Test",
        slug="supermarche-test",
        type="supermarket",
        is_active=True,
    )
    db.add(company)
    await db.flush()
    subscription = Subscription(company_id=company.id, status="active", plan="pro")
    db.add(subscription)
    await db.commit()
    return company


@pytest_asyncio.fixture
async def company2(db: AsyncSession):
    from apps.companies.models import Company, Subscription

    company = Company(
        name="Autre Magasin",
        slug="autre-magasin",
        type="supermarket",
        is_active=True,
    )
    db.add(company)
    await db.flush()
    subscription = Subscription(company_id=company.id, status="active", plan="pro")
    db.add(subscription)
    await db.commit()
    return company


@pytest_asyncio.fixture
async def store(db: AsyncSession, company):
    from apps.stores.models import Store

    store = Store(
        company_id=company.id,
        name="Magasin Central",
        slug="magasin-central",
        is_active=True,
        mobile_money_info={
            "operator": "wave",
            "number": "77 123 45 67",
            "account_name": "Supermarche Test",
        },
    )
    db.add(store)
    await db.commit()
    return store


@pytest_asyncio.fixture
async def store2(db: AsyncSession, company2):
    from apps.stores.models import Store

    store = Store(
        company_id=company2.id,
        name="Magasin Secondaire",
        slug="magasin-secondaire",
        is_active=True,
    )
    db.add(store)
    await db.commit()
    return store


async def _create_staff(db: AsyncSession, company_id, email: str, role_name: str, first_name: str):
    from apps.users.models import User, UserCompanyRole

    user = User(
        email=email,
        password_hash=hash_password("Manager1234!"),
        first_name=first_name,
        last_name="Test",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    role = UserCompanyRole(user_id=user.id, company_id=company_id, role=role_name)
    db.add(role)
    await db.commit()
    await db.refresh(user, attribute_names=["company_roles"])
    return user


@pytest_asyncio.fixture
async def manager(db: AsyncSession, company):
    return await _create_staff(db, company.id, "manager@test.com", "store_manager", "Jean")


@pytest_asyncio.fixture
async def manager2(db: AsyncSession, company2):
    return await _create_staff(db, company2.id, "manager2@test.com", "store_manager", "Awa")


@pytest_asyncio.fixture
async def customer(db: AsyncSession):
    from apps.users.models import User, UserCompanyRole

    user = User(
        phone="+221771234567",
        email="fatou@test.com",
        first_name="Fatou",
        last_name="Diallo",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    role = UserCompanyRole(user_id=user.id, role="customer")
    db.add(role)
    await db.commit()
    await db.refresh(user, attribute_names=["company_roles"])
    return user


@pytest_asyncio.fixture
async def customer2(db: AsyncSession):
    from apps.users.models import User, UserCompanyRole

    user = User(
        phone="+221772222222",
        email="client2@test.com",
        first_name="Client2",
        last_name="Test",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    role = UserCompanyRole(user_id=user.id, role="customer")
    db.add(role)
    await db.commit()
    await db.refresh(user, attribute_names=["company_roles"])
    return user


@pytest_asyncio.fixture
async def product(db: AsyncSession, company, store):
    from apps.catalog.models import Product

    product = Product(
        company_id=company.id,
        store_id=store.id,
        name="Riz 5kg",
        price_xof=3500,
        unit="sac",
        barcode="1234567890123",
        is_available=True,
        track_stock=True,
        stock_quantity=100,
        stock_alert_qty=10,
    )
    db.add(product)
    await db.commit()
    return product


async def _create_order_record(
    db: AsyncSession,
    customer,
    store,
    company,
    product,
    order_number: str,
    status: str = "awaiting_payment",
):
    from apps.orders.models import Order, OrderItem

    order = Order(
        company_id=company.id,
        store_id=store.id,
        customer_id=customer.id,
        order_number=order_number,
        type="click_collect",
        status=status,
        subtotal_xof=product.price_xof,
        total_xof=product.price_xof,
        pickup_code="PICK01",
    )
    db.add(order)
    await db.flush()
    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_name=product.name,
        product_barcode=product.barcode,
        unit_price_xof=product.price_xof,
        quantity=1,
        subtotal_xof=product.price_xof,
    )
    db.add(item)
    await db.commit()
    return order


@pytest_asyncio.fixture
async def order(db: AsyncSession, customer, store, company, product):
    return await _create_order_record(
        db, customer, store, company, product, "SC-2026-00001", status="awaiting_payment"
    )


async def _create_payment_record(
    db: AsyncSession,
    order,
    customer,
    store,
    company,
    payment_number: str,
    status: str,
    operator: str = "wave",
    transaction_ref: str | None = None,
):
    from apps.payments.models import Payment

    payment = Payment(
        company_id=company.id,
        store_id=store.id,
        order_id=order.id,
        customer_id=customer.id,
        payment_number=payment_number,
        method="mobile_money",
        operator=operator,
        amount_xof=order.total_xof,
        status=status,
        transaction_ref=transaction_ref,
        sender_phone=customer.phone,
    )
    db.add(payment)
    await db.commit()
    return payment


@pytest_asyncio.fixture
async def payment(db: AsyncSession, order, customer, store, company):
    return await _create_payment_record(
        db, order, customer, store, company, "PAY-2026-00001", "pending"
    )


@pytest_asyncio.fixture
async def payment_submitted(db: AsyncSession, order, customer, store, company):
    order.status = "payment_submitted"
    await db.commit()
    return await _create_payment_record(
        db,
        order,
        customer,
        store,
        company,
        "PAY-2026-00002",
        "pending_verification",
        transaction_ref="WAVE-TX-SUBMITTED",
    )


async def _create_confirmed_payment(
    db: AsyncSession,
    customer,
    store,
    company,
    product,
    order_number: str,
    payment_number: str,
):
    from apps.payments.models import Payment

    order = await _create_order_record(
        db, customer, store, company, product, order_number, status="confirmed"
    )
    from datetime import datetime, timezone
    payment = Payment(
        company_id=company.id,
        store_id=store.id,
        order_id=order.id,
        customer_id=customer.id,
        payment_number=payment_number,
        method="mobile_money",
        operator="wave",
        amount_xof=order.total_xof,
        status="confirmed",
        transaction_ref=f"TX-{payment_number}",
        sender_phone=customer.phone,
        confirmed_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    await db.commit()
    return payment


@pytest_asyncio.fixture
async def payment_confirmed(db: AsyncSession, customer, store, company, product):
    return await _create_confirmed_payment(
        db, customer, store, company, product, "SC-2026-00003", "PAY-2026-00003"
    )


@pytest_asyncio.fixture
async def payment_confirmed_1(db: AsyncSession, customer, store, company, product):
    return await _create_confirmed_payment(
        db, customer, store, company, product, "SC-2026-00004", "PAY-2026-00004"
    )


@pytest_asyncio.fixture
async def payment_confirmed_2(db: AsyncSession, customer, store, company, product):
    return await _create_confirmed_payment(
        db, customer, store, company, product, "SC-2026-00005", "PAY-2026-00005"
    )


@pytest_asyncio.fixture
async def receipt(db: AsyncSession, payment_confirmed):
    from apps.receipts.service import ReceiptService
    from apps.orders.models import Order

    order = await db.get(Order, payment_confirmed.order_id)
    order.status = "delivered"
    await db.commit()

    service = ReceiptService(db)
    receipt = await service.generate_receipt(payment_confirmed.id)
    await db.commit()
    return receipt


async def create_order_with_payment(client: AsyncClient, customer, store, company):
    from apps.catalog.models import Product

    add_headers = auth_headers(customer)
    if _ACTIVE_TEST_DB is None:
        raise RuntimeError("Test DB session is not initialized")

    product = Product(
        company_id=company.id,
        store_id=store.id,
        name="Produit Helper",
        price_xof=1500,
        unit="piece",
        barcode=f"helper-{company.id}",
        is_available=True,
        track_stock=False,
        stock_quantity=10,
    )
    _ACTIVE_TEST_DB.add(product)
    await _ACTIVE_TEST_DB.commit()

    payload = {
        "store_id": str(store.id),
        "company_id": str(company.id),
        "order_type": "click_collect",
    }

    await client.post(
        f"/api/v1/orders/cart/items?store_id={store.id}&company_id={company.id}",
        json={"product_id": str(product.id), "quantity": 1},
        headers=add_headers,
    )
    order_response = await client.post("/api/v1/orders/", json=payload, headers=add_headers)
    order_id = order_response.json()["id"]
    payment_response = await client.post(
        "/api/v1/payments/",
        json={"order_id": order_id, "operator": "wave"},
        headers=add_headers,
    )

    order = SimpleNamespace(id=order_id)
    payment = SimpleNamespace(id=payment_response.json()["id"])
    return order, payment
