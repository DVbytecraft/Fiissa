"""
Tests Sprint 1 - Identite client et flux email.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers


def _register_payload(phone: str, email: str, **overrides):
    payload = {
        "phone": phone,
        "email": email,
        "password": "StrongPass123!",
        "first_name": "Test",
        "last_name": "User",
        "preferred_language": "fr",
        "marketing_opt_in": False,
    }
    payload.update(overrides)
    return payload


async def _register_and_login(client: AsyncClient, phone: str, email: str):
    reg = await client.post("/api/v1/auth/register", json=_register_payload(phone, email))
    assert reg.status_code == 200, reg.text
    code = reg.json()["debug_code"]
    verify = await client.post("/api/v1/auth/login/verify-otp", json={"email": email, "code": code})
    assert verify.status_code == 200, verify.text
    token = verify.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_requires_email(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": "+221779999991", "password": "StrongPass123!", "first_name": "A", "last_name": "B"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_with_email_ok(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json=_register_payload("+221779999992", "new@test.com"))
    assert resp.status_code == 200
    assert resp.json()["destination"] == "new@test.com"
    assert "debug_code" in resp.json()


@pytest.mark.asyncio
async def test_register_duplicate_email_conflict(client: AsyncClient):
    r1 = await client.post("/api/v1/auth/register", json=_register_payload("+221779000001", "conflict@test.com"))
    assert r1.status_code == 200

    r2 = await client.post("/api/v1/auth/register", json=_register_payload("+221779000002", "conflict@test.com"))
    assert r2.status_code == 409
    assert r2.json()["code"] == "email_taken"


@pytest.mark.asyncio
async def test_register_stores_preferred_language(client: AsyncClient):
    r = await client.post(
        "/api/v1/auth/register",
        json=_register_payload(
            "+221779000003",
            "lang@test.com",
            preferred_language="wo",
            marketing_opt_in=True,
        ),
    )
    assert r.status_code == 200

    code = r.json()["debug_code"]
    v = await client.post("/api/v1/auth/login/verify-otp", json={"email": "lang@test.com", "code": code})
    headers = {"Authorization": f"Bearer {v.json()['access_token']}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["preferred_language"] == "wo"
    assert me.json()["marketing_opt_in"] is True


@pytest.mark.asyncio
async def test_me_includes_identity_fields(client: AsyncClient, customer):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(customer))
    assert resp.status_code == 200
    data = resp.json()
    assert "email_verified" in data
    assert "phone_verified" in data
    assert "preferred_language" in data
    assert "marketing_opt_in" in data


@pytest.mark.asyncio
async def test_update_profile_name(client: AsyncClient, customer, db: AsyncSession):
    headers = auth_headers(customer)
    resp = await client.patch("/api/v1/auth/me", json={"first_name": "Aminata"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Aminata"


@pytest.mark.asyncio
async def test_update_profile_language(client: AsyncClient, customer, db: AsyncSession):
    headers = auth_headers(customer)
    resp = await client.patch("/api/v1/auth/me", json={"preferred_language": "en", "marketing_opt_in": True}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["preferred_language"] == "en"
    assert resp.json()["marketing_opt_in"] is True


@pytest.mark.asyncio
async def test_request_email_verification_ok(client: AsyncClient, customer):
    headers = auth_headers(customer)
    resp = await client.post("/api/v1/auth/request-email-verification", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["debug_token"] is not None


@pytest.mark.asyncio
async def test_verify_email_flow(client: AsyncClient, customer):
    headers = auth_headers(customer)
    r1 = await client.post("/api/v1/auth/request-email-verification", headers=headers)
    token = r1.json()["debug_token"]
    r2 = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert r2.status_code == 200
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["email_verified"] is True


@pytest.mark.asyncio
async def test_verify_email_invalid_token(client: AsyncClient):
    resp = await client.post("/api/v1/auth/verify-email", json={"token": "totally-invalid-token"})
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_or_expired_token"


@pytest.mark.asyncio
async def test_verify_email_token_reuse(client: AsyncClient, customer):
    headers = auth_headers(customer)
    r = await client.post("/api/v1/auth/request-email-verification", headers=headers)
    token = r.json()["debug_token"]
    await client.post("/api/v1/auth/verify-email", json={"token": token})
    resp = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_forgot_password_returns_200_always(client: AsyncClient):
    resp = await client.post("/api/v1/auth/forgot-password", json={"email": "doesnotexist@nowhere.com"})
    assert resp.status_code == 200
    assert resp.json()["debug_token"] is None


@pytest.mark.asyncio
async def test_forgot_password_with_valid_email(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=_register_payload("+221770010001", "reset@test.com"))
    resp = await client.post("/api/v1/auth/forgot-password", json={"email": "reset@test.com"})
    assert resp.status_code == 200
    assert resp.json()["debug_token"] is not None


@pytest.mark.asyncio
async def test_reset_password_flow(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=_register_payload("+221770010002", "resetflow@test.com"))
    r1 = await client.post("/api/v1/auth/forgot-password", json={"email": "resetflow@test.com"})
    token = r1.json()["debug_token"]
    r2 = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "NewPass5678!"})
    assert r2.status_code == 200

    r3 = await client.post("/api/v1/auth/login/request-otp", json={"email": "resetflow@test.com", "password": "NewPass5678!"})
    assert r3.status_code == 200

    r4 = await client.post("/api/v1/auth/login/request-otp", json={"email": "resetflow@test.com", "password": "StrongPass123!"})
    assert r4.status_code == 401


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client: AsyncClient):
    resp = await client.post("/api/v1/auth/reset-password", json={"token": "badtoken", "new_password": "NewPass5678!"})
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_or_expired_token"


@pytest.mark.asyncio
async def test_reset_password_too_short(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=_register_payload("+221770010003", "shortpwd@test.com"))
    r = await client.post("/api/v1/auth/forgot-password", json={"email": "shortpwd@test.com"})
    token = r.json()["debug_token"]

    r2 = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "short"})
    assert r2.status_code == 422

    r3 = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "ValidPass123!"})
    assert r3.status_code == 200


@pytest.mark.asyncio
async def test_reset_token_single_use(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=_register_payload("+221770010004", "singleuse@test.com"))
    r = await client.post("/api/v1/auth/forgot-password", json={"email": "singleuse@test.com"})
    token = r.json()["debug_token"]

    await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "NewPass5678!"})
    resp = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "AnotherPass999!"})
    assert resp.status_code == 400
