"""Tests module rapports — dashboard, summary, export CSV."""
import pytest
from httpx import AsyncClient

from tests.conftest import staff_headers, auth_headers


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/reports/dashboard")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_requires_merchant_role(client: AsyncClient, customer):
    response = await client.get(
        "/api/v1/reports/dashboard",
        headers=auth_headers(customer),
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_dashboard_returns_stats(client: AsyncClient, manager, company):
    response = await client.get(
        "/api/v1/reports/dashboard",
        headers=staff_headers(manager, company_id=company.id, role="store_manager"),
    )
    assert response.status_code == 200
    data = response.json()
    assert "orders_today" in data
    assert "revenue_today_xof" in data
    assert "pending_orders" in data
    assert "pending_payments" in data
    assert "active_customers_30d" in data
    assert "customer_segments" in data
    assert "top_customers" in data
    assert isinstance(data["orders_today"], int)
    assert isinstance(data["revenue_today_xof"], int)


@pytest.mark.asyncio
async def test_dashboard_zero_when_no_orders(client: AsyncClient, manager, company):
    response = await client.get(
        "/api/v1/reports/dashboard",
        headers=staff_headers(manager, company_id=company.id, role="store_manager"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["orders_today"] == 0
    assert data["revenue_today_xof"] == 0


@pytest.mark.asyncio
async def test_summary_default_period(client: AsyncClient, manager, company):
    response = await client.get(
        "/api/v1/reports/summary",
        headers=staff_headers(manager, company_id=company.id, role="store_manager"),
    )
    assert response.status_code == 200
    data = response.json()
    assert "orders_count" in data
    assert "revenue_xof" in data
    assert "top_products" in data
    assert "payment_by_operator" in data
    assert "top_customers" in data
    assert "customer_segments" in data
    assert data["period"] == "month"


@pytest.mark.asyncio
async def test_summary_today_period(client: AsyncClient, manager, company):
    response = await client.get(
        "/api/v1/reports/summary?period=today",
        headers=staff_headers(manager, company_id=company.id, role="store_manager"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "today"


@pytest.mark.asyncio
async def test_summary_week_period(client: AsyncClient, manager, company):
    response = await client.get(
        "/api/v1/reports/summary?period=week",
        headers=staff_headers(manager, company_id=company.id, role="store_manager"),
    )
    assert response.status_code == 200
    assert response.json()["period"] == "week"


@pytest.mark.asyncio
async def test_summary_custom_period(client: AsyncClient, manager, company):
    # La route utilise date_from/date_to (pas start_date/end_date)
    response = await client.get(
        "/api/v1/reports/summary?period=custom&date_from=2026-01-01&date_to=2026-06-30",
        headers=staff_headers(manager, company_id=company.id, role="store_manager"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "custom"
    assert data["date_from"] == "2026-01-01"
    assert data["date_to"] == "2026-06-30"


@pytest.mark.asyncio
async def test_summary_tenant_isolation(
    client: AsyncClient, manager, company, manager2, company2
):
    """Un manager ne peut pas voir les rapports d'une autre entreprise."""
    response = await client.get(
        "/api/v1/reports/summary",
        headers=staff_headers(manager2, company_id=company2.id, role="store_manager"),
    )
    assert response.status_code == 200
    data = response.json()
    # Aucune donnée de company ne doit apparaître dans les résultats de company2
    assert data["orders_count"] == 0
    assert data["revenue_xof"] == 0


@pytest.mark.asyncio
async def test_export_csv(client: AsyncClient, manager, company):
    # Route correcte : /export/csv (pas /export?format=csv)
    response = await client.get(
        "/api/v1/reports/export/csv?period=month",
        headers=staff_headers(manager, company_id=company.id, role="store_manager"),
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_sales_report(client: AsyncClient, manager, company):
    response = await client.get(
        "/api/v1/reports/sales?date_from=2026-01-01&date_to=2026-12-31",
        headers=staff_headers(manager, company_id=company.id, role="store_manager"),
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_summary_includes_delivered_orders(
    client: AsyncClient,
    manager,
    company,
    payment_confirmed,
    db,
):
    """Un paiement confirmé doit apparaître dans les revenus."""
    from apps.orders.models import Order

    order = await db.get(Order, payment_confirmed.order_id)
    order.status = "delivered"
    await db.commit()

    response = await client.get(
        "/api/v1/reports/summary?period=month",
        headers=staff_headers(manager, company_id=company.id, role="store_manager"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["orders_delivered"] >= 1
    assert data["revenue_xof"] >= payment_confirmed.amount_xof


@pytest.mark.asyncio
async def test_summary_includes_customer_intelligence_metrics(
    client: AsyncClient,
    manager,
    company,
    customer,
    store,
    product,
    db,
):
    from datetime import datetime, timezone
    import uuid

    from apps.loyalty.models import CustomerScore, LoyaltyCoupon, LoyaltyTransaction
    from apps.orders.models import Order, OrderItem
    from apps.payments.models import Payment

    order = Order(
        company_id=company.id,
        store_id=store.id,
        customer_id=customer.id,
        order_number="SC-2026-BI-0001",
        type="click_collect",
        status="delivered",
        subtotal_xof=product.price_xof * 2,
        total_xof=product.price_xof * 2,
        pickup_code="PICKBI",
    )
    db.add(order)
    await db.flush()

    db.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            product_barcode=product.barcode,
            unit_price_xof=product.price_xof,
            quantity=2,
            subtotal_xof=product.price_xof * 2,
        )
    )
    db.add(
        Payment(
            company_id=company.id,
            store_id=store.id,
            order_id=order.id,
            customer_id=customer.id,
            payment_number="PAY-2026-BI-0001",
            method="mobile_money",
            operator="wave",
            amount_xof=product.price_xof * 2,
            status="confirmed",
            transaction_ref="TX-BI-0001",
            sender_phone=customer.phone,
            confirmed_at=datetime.now(timezone.utc),
        )
    )
    db.add(
        CustomerScore(
            company_id=company.id,
            customer_id=customer.id,
            recency_score=5,
            frequency_score=4,
            monetary_score=3,
            rfm_score=12,
            segment="loyal",
            order_count=4,
            total_spent_xof=42000,
            computed_at=datetime.now(timezone.utc),
        )
    )
    db.add(
        LoyaltyTransaction(
            id=uuid.uuid4(),
            company_id=company.id,
            card_id=uuid.uuid4(),
            customer_id=customer.id,
            type="earn",
            points_delta=50,
            points_before=100,
            points_after=150,
        )
    )
    db.add(
        LoyaltyCoupon(
            company_id=company.id,
            customer_id=customer.id,
            code="BI2026AA",
            discount_type="fixed",
            discount_value=500,
            min_order_xof=0,
            is_used=True,
            used_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()

    response = await client.get(
        "/api/v1/reports/summary?period=month",
        headers=staff_headers(manager, company_id=company.id, role="store_manager"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["points_distributed"] >= 50
    assert data["coupons_used"] >= 1
    assert data["customer_segments"]["loyal"] >= 1
    assert len(data["top_customers"]) >= 1
    assert data["top_products"][0]["revenue_xof"] >= product.price_xof * 2
