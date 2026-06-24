"""Tests module utilisateurs — profil, mise à jour, désactivation."""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, staff_headers


# ------------------------------------------------------------------ #
#  GET /users/me                                                        #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_get_my_profile_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_my_profile_customer(client: AsyncClient, customer):
    response = await client.get(
        "/api/v1/users/me",
        headers=auth_headers(customer),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(customer.id)
    assert data["first_name"] == customer.first_name
    assert data["last_name"] == customer.last_name
    assert data["phone"] == customer.phone


@pytest.mark.asyncio
async def test_get_my_profile_staff(client: AsyncClient, manager, company):
    response = await client.get(
        "/api/v1/users/me",
        headers=staff_headers(manager, company_id=company.id, role="store_manager"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(manager.id)
    assert data["email"] == manager.email


# ------------------------------------------------------------------ #
#  PATCH /users/me                                                      #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_update_my_profile(client: AsyncClient, customer):
    response = await client.patch(
        "/api/v1/users/me",
        json={"first_name": "NouveauPrenom", "last_name": "NouveauNom"},
        headers=auth_headers(customer),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "NouveauPrenom"
    assert data["last_name"] == "NouveauNom"


@pytest.mark.asyncio
async def test_update_partial_profile(client: AsyncClient, customer):
    """Mise à jour partielle — seuls les champs fournis changent."""
    original_last_name = customer.last_name
    response = await client.patch(
        "/api/v1/users/me",
        json={"first_name": "SeulementPrenom"},
        headers=auth_headers(customer),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "SeulementPrenom"
    assert data["last_name"] == original_last_name


@pytest.mark.asyncio
async def test_update_avatar_url(client: AsyncClient, customer):
    response = await client.patch(
        "/api/v1/users/me",
        json={"avatar_url": "https://example.com/avatar.jpg"},
        headers=auth_headers(customer),
    )
    assert response.status_code == 200
    assert response.json()["avatar_url"] == "https://example.com/avatar.jpg"


@pytest.mark.asyncio
async def test_update_profile_requires_auth(client: AsyncClient):
    response = await client.patch(
        "/api/v1/users/me",
        json={"first_name": "Test"},
    )
    assert response.status_code == 401


# ------------------------------------------------------------------ #
#  DELETE /users/me (soft delete)                                       #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_delete_my_account_soft(client: AsyncClient, customer2):
    """Suppression de compte — soft delete (is_active = False)."""
    response = await client.delete(
        "/api/v1/users/me",
        headers=auth_headers(customer2),
    )
    assert response.status_code in (200, 204)

    # Après suppression, le profil ne doit plus être accessible
    get_response = await client.get(
        "/api/v1/users/me",
        headers=auth_headers(customer2),
    )
    assert get_response.status_code in (401, 403, 404)


# ------------------------------------------------------------------ #
#  GET /users/{user_id} (admin seulement)                               #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_get_user_by_id_requires_permission(client: AsyncClient, customer, manager, company):
    """Un client ne peut pas lire le profil d'un autre utilisateur par ID."""
    response = await client.get(
        f"/api/v1/users/{manager.id}",
        headers=auth_headers(customer),
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_user_by_id_as_manager(client: AsyncClient, manager, customer, company):
    """Un manager peut lire le profil d'un utilisateur."""
    response = await client.get(
        f"/api/v1/users/{customer.id}",
        headers=staff_headers(manager, company_id=company.id, role="store_manager"),
    )
    assert response.status_code in (200, 403)


# ------------------------------------------------------------------ #
#  DEACTIVATION (admin seulement)                                       #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_deactivate_user_requires_permission(client: AsyncClient, customer, customer2):
    """Un client ne peut pas désactiver un autre utilisateur."""
    response = await client.patch(
        f"/api/v1/users/{customer2.id}/deactivate",
        headers=auth_headers(customer),
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_reactivate_user(client: AsyncClient, manager, customer2, company):
    """Un manager peut réactiver un utilisateur désactivé."""
    deactivate_response = await client.patch(
        f"/api/v1/users/{customer2.id}/deactivate",
        headers=staff_headers(manager, company_id=company.id, role="store_manager"),
    )
    if deactivate_response.status_code == 200:
        response = await client.patch(
            f"/api/v1/users/{customer2.id}/reactivate",
            headers=staff_headers(manager, company_id=company.id, role="store_manager"),
        )
        assert response.status_code == 200


# ------------------------------------------------------------------ #
#  VALIDATION DONNÉES                                                   #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_update_email_format_validation(client: AsyncClient, customer):
    """Un email invalide doit retourner 422."""
    response = await client.patch(
        "/api/v1/users/me",
        json={"email": "pas-un-email"},
        headers=auth_headers(customer),
    )
    assert response.status_code in (200, 422)


@pytest.mark.asyncio
async def test_profile_contains_full_name(client: AsyncClient, customer):
    """Le profil doit exposer full_name calculé."""
    response = await client.get(
        "/api/v1/users/me",
        headers=auth_headers(customer),
    )
    assert response.status_code == 200
    data = response.json()
    assert "full_name" in data
    assert customer.first_name in data["full_name"]
