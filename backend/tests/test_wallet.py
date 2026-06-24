import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, staff_headers


@pytest.mark.asyncio
async def test_customer_can_create_and_list_wallet_method(
    client: AsyncClient,
    customer,
    company,
):
    create_response = await client.post(
        "/api/v1/wallet/methods",
        json={
            "company_id": str(company.id),
            "method_type": "mobile_money",
            "operator": "wave",
            "phone_number": "+221771234567",
            "display_name": "Wave perso",
            "is_default": True,
            "metadata": {"label": "principal"},
        },
        headers=auth_headers(customer),
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["display_name"] == "Wave perso"
    assert created["metadata"] == {"label": "principal"}

    list_response = await client.get("/api/v1/wallet/methods", headers=auth_headers(customer))
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["is_default"] is True
    assert items[0]["operator"] == "wave"


@pytest.mark.asyncio
async def test_wallet_disables_bank_card_in_v1(
    client: AsyncClient,
    customer,
):
    response = await client.post(
        "/api/v1/wallet/methods",
        json={
            "method_type": "bank_card",
            "display_name": "Carte perso",
        },
        headers=auth_headers(customer),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "wallet_method_disabled"


@pytest.mark.asyncio
async def test_customer_default_method_is_unique(
    client: AsyncClient,
    customer,
):
    first_response = await client.post(
        "/api/v1/wallet/methods",
        json={
            "method_type": "mobile_money",
            "operator": "wave",
            "phone_number": "+221771234567",
            "display_name": "Wave",
            "is_default": True,
        },
        headers=auth_headers(customer),
    )
    second_response = await client.post(
        "/api/v1/wallet/methods",
        json={
            "method_type": "mobile_money",
            "operator": "orange_money",
            "phone_number": "+221778889900",
            "display_name": "Orange",
            "is_default": True,
        },
        headers=auth_headers(customer),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    list_response = await client.get("/api/v1/wallet/methods", headers=auth_headers(customer))
    items = list_response.json()
    defaults = [item for item in items if item["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["display_name"] == "Orange"


@pytest.mark.asyncio
async def test_staff_can_list_company_wallet_methods(
    client: AsyncClient,
    customer,
    manager,
    company,
):
    await client.post(
        "/api/v1/wallet/methods",
        json={
            "company_id": str(company.id),
            "method_type": "mobile_money",
            "operator": "wave",
            "phone_number": "+221771234567",
            "display_name": "Wave entreprise",
        },
        headers=auth_headers(customer),
    )

    response = await client.get(
        "/api/v1/wallet/company-methods",
        headers=staff_headers(manager, company_id=company.id, role="store_manager"),
    )
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["company_id"] == str(company.id)
