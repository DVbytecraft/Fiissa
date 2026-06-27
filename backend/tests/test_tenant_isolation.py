"""
Tests d'isolation multi-tenant.
Règle absolue : un marchand ne voit JAMAIS les données d'un autre marchand.
"""
import pytest
from httpx import AsyncClient
from tests.conftest import staff_headers, auth_headers, build_auth_headers


@pytest.mark.asyncio
async def test_manager_cannot_see_other_company_orders(
    client: AsyncClient, db, company, store, customer, product
):
    """Un manager ne peut voir que les commandes de sa propre entreprise."""
    from apps.companies.models import Company, Subscription
    from apps.users.models import User, UserCompanyRole
    from core.security import hash_password

    # Créer une deuxième entreprise
    company2 = Company(name="Autre Commerce", slug="autre-commerce", type="restaurant", is_active=True)
    db.add(company2)
    await db.flush()
    sub2 = Subscription(company_id=company2.id, status="active", plan="starter")
    db.add(sub2)

    # Manager de la deuxième entreprise
    manager2 = User(
        email="manager2@test.com",
        password_hash=hash_password("Test1234!"),
        first_name="Ali",
        last_name="Manager2",
        is_active=True,
        is_verified=True,
    )
    db.add(manager2)
    await db.flush()

    role2 = UserCompanyRole(user_id=manager2.id, company_id=company2.id, role="store_manager")
    db.add(role2)
    await db.commit()

    # Manager2 essaie de voir les paiements de la company1
    from apps.payments.models import Payment
    from apps.orders.models import Order

    # Créer un paiement pour company1
    order = Order(
        company_id=company.id,
        store_id=store.id,
        customer_id=customer.id,
        order_number="SC-2024-00001",
        type="click_collect",
        status="payment_submitted",
        total_xof=5000,
    )
    db.add(order)
    await db.flush()

    payment = Payment(
        company_id=company.id,
        store_id=store.id,
        order_id=order.id,
        customer_id=customer.id,
        payment_number="PAY-2024-00001",
        method="mobile_money",
        operator="wave",
        amount_xof=5000,
        status="pending_verification",
        transaction_ref="WV123456",
    )
    db.add(payment)
    await db.commit()

    # Manager2 essaie de confirmer le paiement de company1
    headers2 = staff_headers(manager2, company2.id)
    response = await client.post(
        f"/api/v1/payments/{payment.id}/confirm",
        json={"confirmed": True},
        headers=headers2,
    )
    # Doit être refusé (TenantAccessDenied ou 403)
    assert response.status_code in (403, 404), (
        f"SÉCURITÉ CRITIQUE : Manager2 a pu accéder aux paiements de company1! "
        f"Status: {response.status_code}"
    )


@pytest.mark.asyncio
async def test_customer_cannot_see_other_customer_orders(
    client: AsyncClient, db, company, store, product
):
    """Un client ne peut voir que ses propres commandes."""
    from apps.users.models import User, UserCompanyRole
    from apps.orders.models import Order

    customer1 = User(phone="+221771111111", first_name="Client1", last_name="Test", is_active=True)
    customer2 = User(phone="+221772222222", first_name="Client2", last_name="Test", is_active=True)
    db.add_all([customer1, customer2])
    await db.flush()

    for c in [customer1, customer2]:
        db.add(UserCompanyRole(user_id=c.id, role="customer"))

    order1 = Order(
        company_id=company.id,
        store_id=store.id,
        customer_id=customer1.id,
        order_number="SC-2024-00002",
        type="click_collect",
        status="confirmed",
        total_xof=3500,
    )
    db.add(order1)
    await db.commit()

    # Client2 essaie d'accéder à la commande de Client1
    response = await client.get(
        f"/api/v1/orders/{order1.id}",
        headers=auth_headers(customer2),
    )
    assert response.status_code in (403, 404), (
        f"SÉCURITÉ : Client2 a pu voir la commande de Client1! Status: {response.status_code}"
    )


@pytest.mark.asyncio
async def test_duplicate_payment_ref_rejected(
    client: AsyncClient, db, company, store, customer, product
):
    """Une même référence de transaction ne peut pas être utilisée deux fois."""
    from apps.orders.models import Order
    from apps.payments.models import Payment

    order = Order(
        company_id=company.id,
        store_id=store.id,
        customer_id=customer.id,
        order_number="SC-2024-00010",
        type="click_collect",
        status="awaiting_payment",
        total_xof=5000,
    )
    db.add(order)
    await db.flush()

    payment = Payment(
        company_id=company.id,
        store_id=store.id,
        order_id=order.id,
        customer_id=customer.id,
        payment_number="PAY-2024-00010",
        method="mobile_money",
        operator="wave",
        amount_xof=5000,
        status="pending_verification",
        transaction_ref="WV_UNIQUE_REF_001",
    )
    db.add(payment)
    await db.commit()

    # Essayer d'utiliser la même référence pour un autre paiement
    order2 = Order(
        company_id=company.id,
        store_id=store.id,
        customer_id=customer.id,
        order_number="SC-2024-00011",
        type="click_collect",
        status="awaiting_payment",
        total_xof=3500,
    )
    db.add(order2)
    await db.flush()

    payment2 = Payment(
        company_id=company.id,
        store_id=store.id,
        order_id=order2.id,
        customer_id=customer.id,
        payment_number="PAY-2024-00011",
        method="mobile_money",
        operator="wave",
        amount_xof=3500,
        status="pending",
    )
    db.add(payment2)
    await db.commit()

    response = await client.post(
        f"/api/v1/payments/{payment2.id}/submit-proof",
        json={
            "transaction_ref": "WV_UNIQUE_REF_001",  # Même référence !
            "sender_phone": "+221771234567",
        },
        headers=auth_headers(customer),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "duplicate_payment_ref"


@pytest.mark.asyncio
async def test_payment_already_confirmed_rejected(
    client: AsyncClient, db, company, store, customer, product, manager
):
    """Un paiement confirmé ne peut pas être re-confirmé."""
    from apps.orders.models import Order
    from apps.payments.models import Payment
    from tests.conftest import staff_headers

    order = Order(
        company_id=company.id,
        store_id=store.id,
        customer_id=customer.id,
        order_number="SC-2024-00020",
        type="click_collect",
        status="confirmed",
        total_xof=5000,
    )
    db.add(order)
    await db.flush()

    payment = Payment(
        company_id=company.id,
        store_id=store.id,
        order_id=order.id,
        customer_id=customer.id,
        payment_number="PAY-2024-00020",
        method="mobile_money",
        operator="wave",
        amount_xof=5000,
        status="confirmed",  # Déjà confirmé
        transaction_ref="WV_CONFIRMED_001",
    )
    db.add(payment)
    await db.commit()

    headers = staff_headers(manager, company.id)
    response = await client.post(
        f"/api/v1/payments/{payment.id}/confirm",
        json={"confirmed": True},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "payment_already_confirmed"


@pytest.mark.asyncio
async def test_company_owner_cannot_update_other_company(
    client: AsyncClient, db, company, company2
):
    """FIX #1 — Un company_owner ne peut pas modifier l'entreprise d'un autre tenant."""
    from apps.users.models import User, UserCompanyRole
    from core.security import hash_password

    # Créer un company_owner rattaché à company (pas à company2)
    owner_a = User(
        email="owner_a_tenant@test.com",
        password_hash=hash_password("Owner1234!"),
        first_name="OwnerA",
        last_name="Tenant",
        is_active=True,
        is_verified=True,
    )
    db.add(owner_a)
    await db.flush()
    db.add(UserCompanyRole(user_id=owner_a.id, company_id=company.id, role="company_owner"))
    await db.commit()
    await db.refresh(owner_a, attribute_names=["company_roles"])

    # Le owner de company A tente de modifier company B
    headers = build_auth_headers(owner_a, role="company_owner", company_id=company.id)
    response = await client.patch(
        f"/api/v1/companies/{company2.id}",
        headers=headers,
        json={"name": "Hacked Name"},
    )
    assert response.status_code == 403, (
        f"SÉCURITÉ CRITIQUE : company_owner A a pu modifier company B ! "
        f"Status: {response.status_code}, body: {response.json()}"
    )
