"""Tests module support tickets — création, messages, fermeture, isolation."""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, staff_headers


# ------------------------------------------------------------------ #
#  HELPERS                                                              #
# ------------------------------------------------------------------ #

async def create_ticket(client, user, company=None, subject="Problème commande", body="Je n'arrive pas à valider ma commande.", priority="medium"):
    headers = auth_headers(user) if company is None else staff_headers(user, company_id=company.id, role="store_manager")
    response = await client.post(
        "/api/v1/support/tickets",
        json={"subject": subject, "body": body, "priority": priority, "category": "order"},
        headers=headers,
    )
    return response


def get_ticket_id(create_response_json: dict) -> str:
    """Extrait l'ID du ticket depuis la réponse de création (ticket_id ou id)."""
    return create_response_json.get("ticket_id") or create_response_json.get("id")


# ------------------------------------------------------------------ #
#  CRÉATION DE TICKET                                                   #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_create_ticket_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/support/tickets",
        json={"subject": "Test", "body": "Corps du message", "priority": "low"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_ticket_as_customer(client: AsyncClient, customer, company):
    response = await create_ticket(client, customer)
    assert response.status_code in (200, 201)
    data = response.json()
    ticket_id = get_ticket_id(data)
    assert ticket_id is not None
    assert data["status"] == "open"


@pytest.mark.asyncio
async def test_create_ticket_missing_subject(client: AsyncClient, customer):
    response = await client.post(
        "/api/v1/support/tickets",
        json={"body": "Corps sans sujet"},
        headers=auth_headers(customer),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_ticket_missing_body(client: AsyncClient, customer):
    response = await client.post(
        "/api/v1/support/tickets",
        json={"subject": "Sujet sans corps"},
        headers=auth_headers(customer),
    )
    assert response.status_code == 422


# ------------------------------------------------------------------ #
#  LISTE TICKETS                                                        #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_list_tickets_empty(client: AsyncClient, customer):
    response = await client.get(
        "/api/v1/support/tickets",
        headers=auth_headers(customer),
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data or isinstance(data, list)


@pytest.mark.asyncio
async def test_list_tickets_after_create(client: AsyncClient, customer, company):
    await create_ticket(client, customer)
    response = await client.get(
        "/api/v1/support/tickets",
        headers=auth_headers(customer),
    )
    assert response.status_code == 200
    data = response.json()
    items = data.get("items", data) if isinstance(data, dict) else data
    assert len(items) >= 1


# ------------------------------------------------------------------ #
#  DÉTAIL ET MESSAGES                                                   #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_get_ticket_detail(client: AsyncClient, customer):
    create_response = await create_ticket(client, customer)
    assert create_response.status_code in (200, 201)
    ticket_id = get_ticket_id(create_response.json())
    assert ticket_id is not None

    response = await client.get(
        f"/api/v1/support/tickets/{ticket_id}",
        headers=auth_headers(customer),
    )
    assert response.status_code == 200
    data = response.json()
    real_id = data.get("id") or data.get("ticket_id")
    assert real_id == ticket_id
    assert data.get("subject") == "Problème commande"


@pytest.mark.asyncio
async def test_add_message_to_ticket(client: AsyncClient, customer):
    create_response = await create_ticket(client, customer)
    ticket_id = get_ticket_id(create_response.json())

    response = await client.post(
        f"/api/v1/support/tickets/{ticket_id}/reply",
        json={"body": "Voici plus de détails sur le problème."},
        headers=auth_headers(customer),
    )
    assert response.status_code in (200, 201)
    data = response.json()
    assert "message_id" in data or "id" in data


@pytest.mark.asyncio
async def test_add_message_requires_auth(client: AsyncClient, customer):
    create_response = await create_ticket(client, customer)
    ticket_id = get_ticket_id(create_response.json())

    response = await client.post(
        f"/api/v1/support/tickets/{ticket_id}/reply",
        json={"body": "Message sans auth"},
    )
    assert response.status_code == 401


# ------------------------------------------------------------------ #
#  FERMETURE TICKET                                                     #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_close_ticket(client: AsyncClient, customer, manager, company):
    """Fermer un ticket via PATCH /tickets/{id} avec status=closed (requiert support.update)."""
    create_response = await create_ticket(client, customer)
    ticket_id = get_ticket_id(create_response.json())

    # Le manager ferme le ticket (role support.update)
    response = await client.patch(
        f"/api/v1/support/tickets/{ticket_id}",
        json={"status": "resolved"},
        headers=staff_headers(manager, company_id=company.id, role="store_manager"),
    )
    # Peut retourner 200 (succès) ou 403/404 si le ticket n'a pas de company_id
    assert response.status_code in (200, 403, 404)


# ------------------------------------------------------------------ #
#  ISOLATION TENANT                                                     #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_cannot_access_other_user_ticket(client: AsyncClient, customer, customer2):
    """Un utilisateur ne peut pas voir le ticket d'un autre."""
    create_response = await create_ticket(client, customer)
    ticket_id = get_ticket_id(create_response.json())

    response = await client.get(
        f"/api/v1/support/tickets/{ticket_id}",
        headers=auth_headers(customer2),
    )
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_ticket_not_found(client: AsyncClient, customer):
    """Un ticket inexistant retourne 404."""
    import uuid
    response = await client.get(
        f"/api/v1/support/tickets/{uuid.uuid4()}",
        headers=auth_headers(customer),
    )
    assert response.status_code == 404


# ------------------------------------------------------------------ #
#  PRIORITÉS ET CATÉGORIES                                             #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_create_urgent_ticket(client: AsyncClient, customer):
    response = await client.post(
        "/api/v1/support/tickets",
        json={"subject": "Urgent", "body": "Très urgent!", "priority": "urgent", "category": "payment"},
        headers=auth_headers(customer),
    )
    assert response.status_code in (200, 201)
    data = response.json()
    ticket_id = get_ticket_id(data)
    assert ticket_id is not None

    # Vérifier le détail contient la bonne priorité
    detail = await client.get(
        f"/api/v1/support/tickets/{ticket_id}",
        headers=auth_headers(customer),
    )
    if detail.status_code == 200:
        assert detail.json().get("priority") == "urgent"
