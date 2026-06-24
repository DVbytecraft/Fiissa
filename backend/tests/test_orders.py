"""Tests module commandes — stock, machine à états."""
import pytest
from httpx import AsyncClient
from tests.conftest import auth_headers, staff_headers


@pytest.mark.asyncio
async def test_add_to_cart(client: AsyncClient, customer, store, company, product):
    response = await client.post(
        f"/api/v1/orders/cart/items?store_id={store.id}&company_id={company.id}",
        json={"product_id": str(product.id), "quantity": 2},
        headers=auth_headers(customer),
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_order(client: AsyncClient, customer, store, company, product):
    # Ajouter au panier
    await client.post(
        f"/api/v1/orders/cart/items?store_id={store.id}&company_id={company.id}",
        json={"product_id": str(product.id), "quantity": 3},
        headers=auth_headers(customer),
    )

    # Créer la commande
    response = await client.post(
        "/api/v1/orders/",
        json={
            "store_id": str(store.id),
            "company_id": str(company.id),
            "order_type": "click_collect",
        },
        headers=auth_headers(customer),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["total_xof"] == 3500 * 3


@pytest.mark.asyncio
async def test_insufficient_stock_blocks_order(client: AsyncClient, customer, store, company, db):
    """Le système doit bloquer si le stock est insuffisant."""
    from apps.catalog.models import Product

    # Produit avec stock limité
    low_stock = Product(
        company_id=company.id,
        store_id=store.id,
        name="Produit Rare",
        price_xof=1000,
        is_available=True,
        track_stock=True,
        stock_quantity=2,  # Seulement 2 en stock
    )
    db.add(low_stock)
    await db.commit()

    # Essayer de commander 5
    await client.post(
        f"/api/v1/orders/cart/items?store_id={store.id}&company_id={company.id}",
        json={"product_id": str(low_stock.id), "quantity": 5},
        headers=auth_headers(customer),
    )

    response = await client.post(
        "/api/v1/orders/",
        json={
            "store_id": str(store.id),
            "company_id": str(company.id),
            "order_type": "click_collect",
        },
        headers=auth_headers(customer),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "insufficient_stock"


@pytest.mark.asyncio
async def test_empty_cart_blocked(client: AsyncClient, customer, store, company):
    """Commande avec panier vide impossible."""
    response = await client.post(
        "/api/v1/orders/",
        json={
            "store_id": str(store.id),
            "company_id": str(company.id),
            "order_type": "click_collect",
        },
        headers=auth_headers(customer),
    )
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_customer_sees_own_orders(client: AsyncClient, customer, store, company, product):
    """Le client ne voit que ses propres commandes."""
    await client.post(
        f"/api/v1/orders/cart/items?store_id={store.id}&company_id={company.id}",
        json={"product_id": str(product.id), "quantity": 1},
        headers=auth_headers(customer),
    )
    await client.post(
        "/api/v1/orders/",
        json={"store_id": str(store.id), "company_id": str(company.id), "order_type": "click_collect"},
        headers=auth_headers(customer),
    )

    response = await client.get("/api/v1/orders/my", headers=auth_headers(customer))
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert all(item for item in data["items"])


@pytest.mark.asyncio
async def test_invalid_order_transition(client: AsyncClient, customer, store, company, product, manager, db):
    """Les transitions d'état invalides sont bloquées."""
    from apps.orders.models import Order

    order = Order(
        company_id=company.id,
        store_id=store.id,
        customer_id=customer.id,
        order_number="SC-2024-99001",
        type="click_collect",
        status="draft",
        total_xof=3500,
    )
    db.add(order)
    await db.commit()

    # Essayer de passer directement de draft à delivered (transition invalide)
    response = await client.patch(
        f"/api/v1/orders/{order.id}/status",
        json={"status": "delivered"},
        headers=staff_headers(manager, company.id),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_order_transition"
