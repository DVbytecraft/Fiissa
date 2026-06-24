"""Tests module authentification."""

import pytest
from httpx import AsyncClient


def _register_payload(phone: str, email: str):
    return {
        "phone": phone,
        "email": email,
        "password": "StrongPass123!",
        "first_name": "Fatou",
        "last_name": "Diallo",
    }


@pytest.mark.asyncio
async def test_register_customer(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json=_register_payload("+221771234567", "fatou@example.com"))
    assert response.status_code == 200
    data = response.json()
    assert data["destination"] == "fatou@example.com"
    assert "debug_code" in data


@pytest.mark.asyncio
async def test_register_requires_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"phone": "+221771234568", "password": "StrongPass123!", "first_name": "Test", "last_name": "User"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_requires_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"phone": "+221771234569", "email": "test@example.com", "first_name": "Test", "last_name": "User"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_phone(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "phone": "abc",
            "email": "test@example.com",
            "password": "StrongPass123!",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_verify_otp(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json=_register_payload("+221779876543", "moussa@example.com"))
    assert reg.status_code == 200
    debug_code = reg.json()["debug_code"]

    verify = await client.post("/api/v1/auth/login/verify-otp", json={"email": "moussa@example.com", "code": debug_code})
    assert verify.status_code == 200
    data = verify.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_request_otp_with_email_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=_register_payload("+221771111111", "login@example.com"))
    response = await client.post(
        "/api/v1/auth/login/request-otp",
        json={"email": "login@example.com", "password": "StrongPass123!"},
    )
    assert response.status_code == 200
    assert response.json()["destination"] == "login@example.com"


@pytest.mark.asyncio
async def test_verify_wrong_otp(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=_register_payload("+221771111112", "wrong@example.com"))
    response = await client.post("/api/v1/auth/login/verify-otp", json={"email": "wrong@example.com", "code": "000000"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_otp"


@pytest.mark.asyncio
async def test_staff_login(client: AsyncClient, manager):
    response = await client.post("/api/v1/auth/staff/login", json={"email": "manager@test.com", "password": "Manager1234!"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "store_manager"


@pytest.mark.asyncio
async def test_staff_wrong_password(client: AsyncClient, manager):
    response = await client.post("/api/v1/auth/staff/login", json={"email": "manager@test.com", "password": "wrongpassword"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient, customer):
    from tests.conftest import auth_headers

    response = await client.get("/api/v1/auth/me", headers=auth_headers(customer))
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "+221771234567"
    assert "email_verified" in data
    assert "preferred_language" in data


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json=_register_payload("+221773333333", "refresh@example.com"))
    code = reg.json()["debug_code"]
    login = await client.post("/api/v1/auth/login/verify-otp", json={"email": "refresh@example.com", "code": code})
    refresh_token = login.json()["refresh_token"]

    refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh.status_code == 200
    new_data = refresh.json()
    assert "access_token" in new_data
    assert new_data["refresh_token"] != refresh_token

    second = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert second.status_code == 401
