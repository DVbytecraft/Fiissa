import pytest
from httpx import AsyncClient

from tests.conftest import staff_headers


@pytest.mark.asyncio
async def test_register_sends_customer_welcome_email(client: AsyncClient, monkeypatch):
    sent: dict[str, str] = {}

    async def fake_send_customer_welcome(*, email: str, first_name: str):
        sent["email"] = email
        sent["first_name"] = first_name

    monkeypatch.setattr(
        "apps.notifications.service.EmailService.send_customer_welcome",
        fake_send_customer_welcome,
    )

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "phone": "+221778888881",
            "email": "welcome-customer@test.com",
            "password": "StrongPass123!",
            "first_name": "Awa",
            "last_name": "Fall",
        },
    )

    assert response.status_code == 200
    assert sent == {
        "email": "welcome-customer@test.com",
        "first_name": "Awa",
    }


@pytest.mark.asyncio
async def test_create_company_sends_merchant_welcome_email(
    client: AsyncClient,
    super_admin,
    monkeypatch,
):
    sent: dict[str, str] = {}

    async def fake_send_merchant_welcome(*, email: str, first_name: str, company_name: str):
        sent["email"] = email
        sent["first_name"] = first_name
        sent["company_name"] = company_name

    monkeypatch.setattr(
        "apps.notifications.service.EmailService.send_merchant_welcome",
        fake_send_merchant_welcome,
    )

    response = await client.post(
        "/api/v1/companies/",
        json={
            "name": "Boutique Demo",
            "type": "retail",
            "country": "SN",
            "currency": "XOF",
            "contact_email": "owner@demo.test",
        },
        headers=staff_headers(super_admin, role="super_admin"),
    )

    assert response.status_code == 200
    assert sent == {
        "email": "admin@test.com",
        "first_name": "Super",
        "company_name": "Boutique Demo",
    }
