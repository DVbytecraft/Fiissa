"""
Tests Sprint 2 — Loyalty Engine

Couvre :
- Création programme (loyalty_enabled=False par défaut)
- Programme inactif → carte impossible
- Activation programme → loyalty_enabled=True
- Émission carte native (programme actif requis)
- Doublon carte native → 409
- Import carte externe
- Gain de points (earn) + ledger append-only
- Rachat de points (redeem) + solde insuffisant → 400
- Transactions visibles dans l'historique
- Création tier + récompense
- Émission + application coupon
- Multi-tenant : un marchand ne voit que ses données
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import staff_headers, auth_headers


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _create_program(client: AsyncClient, manager) -> dict:
    resp = await client.post(
        "/api/v1/loyalty/programs",
        json={"name": "Programme Test", "points_per_xof": 0.01, "min_spend_xof": 500},
        headers=staff_headers(manager),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _activate_program(client: AsyncClient, manager, program_id: str) -> dict:
    resp = await client.post(
        f"/api/v1/loyalty/programs/{program_id}/activate",
        headers=staff_headers(manager),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── Programme ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_program_loyalty_disabled_by_default(
    client: AsyncClient, manager, db: AsyncSession
):
    """Un programme créé a loyalty_enabled=False et is_active=False par défaut."""
    prog = await _create_program(client, manager)
    assert prog["loyalty_enabled"] is False
    assert prog["is_active"] is False


@pytest.mark.asyncio
async def test_activate_program(client: AsyncClient, manager, db: AsyncSession):
    """Activer un programme positionne loyalty_enabled=True et is_active=True."""
    prog = await _create_program(client, manager)
    active = await _activate_program(client, manager, prog["id"])
    assert active["is_active"] is True
    assert active["loyalty_enabled"] is True


@pytest.mark.asyncio
async def test_list_programs(client: AsyncClient, manager, db: AsyncSession):
    """GET /loyalty/programs retourne les programmes de l'entreprise."""
    await _create_program(client, manager)
    resp = await client.get("/api/v1/loyalty/programs", headers=staff_headers(manager))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_program(client: AsyncClient, manager, db: AsyncSession):
    prog = await _create_program(client, manager)
    resp = await client.patch(
        f"/api/v1/loyalty/programs/{prog['id']}",
        json={"name": "Nouveau Nom"},
        headers=staff_headers(manager),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Nouveau Nom"


@pytest.mark.asyncio
async def test_duplicate_program_name_conflict(client: AsyncClient, manager, db: AsyncSession):
    """Deux programmes avec le même nom pour la même entreprise → 409."""
    await _create_program(client, manager)
    resp = await client.post(
        "/api/v1/loyalty/programs",
        json={"name": "Programme Test"},
        headers=staff_headers(manager),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "program_name_taken"


# ── Cartes ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cannot_issue_card_if_program_inactive(
    client: AsyncClient, manager, customer, db: AsyncSession
):
    """Émettre une carte pour un programme inactif → 400."""
    prog = await _create_program(client, manager)
    resp = await client.post(
        "/api/v1/loyalty/cards/issue",
        json={"customer_id": str(customer.id), "program_id": prog["id"]},
        headers=staff_headers(manager),
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "program_not_active"


@pytest.mark.asyncio
async def test_issue_native_card_ok(client: AsyncClient, manager, customer, db: AsyncSession):
    """Émettre une carte native quand le programme est actif → 200."""
    prog = await _create_program(client, manager)
    await _activate_program(client, manager, prog["id"])

    resp = await client.post(
        "/api/v1/loyalty/cards/issue",
        json={"customer_id": str(customer.id), "program_id": prog["id"]},
        headers=staff_headers(manager),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["card_type"] == "native"
    assert data["status"] == "active"
    assert data["points_balance"] == 0
    assert data["customer_id"] == str(customer.id)


@pytest.mark.asyncio
async def test_duplicate_native_card_conflict(
    client: AsyncClient, manager, customer, db: AsyncSession
):
    """Deux cartes natives actives pour le même (client, programme) → 409."""
    prog = await _create_program(client, manager)
    await _activate_program(client, manager, prog["id"])

    payload = {"customer_id": str(customer.id), "program_id": prog["id"]}
    r1 = await client.post("/api/v1/loyalty/cards/issue", json=payload, headers=staff_headers(manager))
    assert r1.status_code == 200

    r2 = await client.post("/api/v1/loyalty/cards/issue", json=payload, headers=staff_headers(manager))
    assert r2.status_code == 409
    assert r2.json()["code"] == "card_already_exists"


@pytest.mark.asyncio
async def test_import_external_card(client: AsyncClient, manager, customer, db: AsyncSession):
    """Importer une carte externe (pas besoin de programme actif)."""
    resp = await client.post(
        "/api/v1/loyalty/cards/import",
        json={
            "customer_id": str(customer.id),
            "external_issuer": "Auchan Sénégal",
            "external_ref": "AUC-123456",
        },
        headers=staff_headers(manager),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["card_type"] == "external"
    assert data["external_issuer"] == "Auchan Sénégal"


@pytest.mark.asyncio
async def test_list_customer_cards(client: AsyncClient, manager, customer, db: AsyncSession):
    """GET /loyalty/customers/{id}/cards retourne les cartes d'un client."""
    prog = await _create_program(client, manager)
    await _activate_program(client, manager, prog["id"])
    await client.post(
        "/api/v1/loyalty/cards/issue",
        json={"customer_id": str(customer.id), "program_id": prog["id"]},
        headers=staff_headers(manager),
    )
    resp = await client.get(
        f"/api/v1/loyalty/customers/{customer.id}/cards",
        headers=staff_headers(manager),
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ── Points ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_earn_points(client: AsyncClient, manager, customer, db: AsyncSession):
    """Gain de points sur achat — vérifie le delta et le solde."""
    prog = await _create_program(client, manager)
    await _activate_program(client, manager, prog["id"])
    card_resp = await client.post(
        "/api/v1/loyalty/cards/issue",
        json={"customer_id": str(customer.id), "program_id": prog["id"]},
        headers=staff_headers(manager),
    )
    card_id = card_resp.json()["id"]

    earn_resp = await client.post(
        f"/api/v1/loyalty/cards/{card_id}/earn",
        json={"card_id": card_id, "amount_xof": 10000},
        headers=staff_headers(manager),
    )
    assert earn_resp.status_code == 200
    tx = earn_resp.json()
    assert tx["type"] == "earn"
    assert tx["points_delta"] > 0
    assert tx["points_before"] == 0
    assert tx["points_after"] == tx["points_delta"]


@pytest.mark.asyncio
async def test_redeem_points_ok(client: AsyncClient, manager, customer, db: AsyncSession):
    """Rachat de points — solde décrémenté."""
    prog = await _create_program(client, manager)
    await _activate_program(client, manager, prog["id"])
    card_resp = await client.post(
        "/api/v1/loyalty/cards/issue",
        json={"customer_id": str(customer.id), "program_id": prog["id"]},
        headers=staff_headers(manager),
    )
    card_id = card_resp.json()["id"]

    # Créditer 100 points via earn (10 000 XOF × 0.01)
    await client.post(
        f"/api/v1/loyalty/cards/{card_id}/earn",
        json={"card_id": card_id, "amount_xof": 10000},
        headers=staff_headers(manager),
    )

    redeem_resp = await client.post(
        f"/api/v1/loyalty/cards/{card_id}/redeem",
        json={"card_id": card_id, "points": 50},
        headers=staff_headers(manager),
    )
    assert redeem_resp.status_code == 200
    tx = redeem_resp.json()
    assert tx["type"] == "redeem"
    assert tx["points_delta"] == -50


@pytest.mark.asyncio
async def test_redeem_insufficient_points(
    client: AsyncClient, manager, customer, db: AsyncSession
):
    """Rachat supérieur au solde → 400 insufficient_points."""
    prog = await _create_program(client, manager)
    await _activate_program(client, manager, prog["id"])
    card_resp = await client.post(
        "/api/v1/loyalty/cards/issue",
        json={"customer_id": str(customer.id), "program_id": prog["id"]},
        headers=staff_headers(manager),
    )
    card_id = card_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/loyalty/cards/{card_id}/redeem",
        json={"card_id": card_id, "points": 999},
        headers=staff_headers(manager),
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "insufficient_points"


@pytest.mark.asyncio
async def test_transaction_history(client: AsyncClient, manager, customer, db: AsyncSession):
    """L'historique des transactions est append-only et lisible."""
    prog = await _create_program(client, manager)
    await _activate_program(client, manager, prog["id"])
    card_resp = await client.post(
        "/api/v1/loyalty/cards/issue",
        json={"customer_id": str(customer.id), "program_id": prog["id"]},
        headers=staff_headers(manager),
    )
    card_id = card_resp.json()["id"]

    await client.post(
        f"/api/v1/loyalty/cards/{card_id}/earn",
        json={"card_id": card_id, "amount_xof": 5000},
        headers=staff_headers(manager),
    )
    await client.post(
        f"/api/v1/loyalty/cards/{card_id}/earn",
        json={"card_id": card_id, "amount_xof": 3000},
        headers=staff_headers(manager),
    )

    hist = await client.get(
        f"/api/v1/loyalty/cards/{card_id}/transactions",
        headers=staff_headers(manager),
    )
    assert hist.status_code == 200
    txs = hist.json()
    assert len(txs) == 2
    # Les deux sont des gains
    assert all(tx["type"] == "earn" for tx in txs)
    # Le ledger contient un snapshot points_before=0 (premier gain) et un autre > 0 (second)
    all_before = {tx["points_before"] for tx in txs}
    assert 0 in all_before


# ── Niveaux + récompenses ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_tier(client: AsyncClient, manager, db: AsyncSession):
    prog = await _create_program(client, manager)
    resp = await client.post(
        f"/api/v1/loyalty/programs/{prog['id']}/tiers",
        json={"name": "Or", "min_points": 500, "multiplier": 2.0},
        headers=staff_headers(manager),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Or"
    assert resp.json()["multiplier"] == 2.0


@pytest.mark.asyncio
async def test_create_reward(client: AsyncClient, manager, db: AsyncSession):
    prog = await _create_program(client, manager)
    resp = await client.post(
        f"/api/v1/loyalty/programs/{prog['id']}/rewards",
        json={
            "name": "Réduction 10%",
            "points_cost": 200,
            "reward_type": "discount_pct",
            "value": 10.0,
        },
        headers=staff_headers(manager),
    )
    assert resp.status_code == 200
    assert resp.json()["points_cost"] == 200


# ── Coupons ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_issue_and_apply_coupon(client: AsyncClient, manager, customer, db: AsyncSession):
    """Émettre un coupon et l'appliquer à une commande fictive."""
    import uuid

    resp = await client.post(
        "/api/v1/loyalty/coupons/issue",
        json={
            "customer_id": str(customer.id),
            "discount_type": "fixed",
            "discount_value": 1000,
            "min_order_xof": 5000,
        },
        headers=staff_headers(manager),
    )
    assert resp.status_code == 200
    coupon = resp.json()
    assert len(coupon["code"]) == 8
    assert coupon["is_used"] is False

    # Appliquer à une commande fictive
    fake_order_id = str(uuid.uuid4())
    apply = await client.post(
        f"/api/v1/loyalty/coupons/{coupon['code']}/apply?order_id={fake_order_id}",
        headers=staff_headers(manager),
    )
    assert apply.status_code == 200
    assert apply.json()["is_used"] is True


@pytest.mark.asyncio
async def test_coupon_double_use_rejected(client: AsyncClient, manager, customer, db: AsyncSession):
    """Utiliser un coupon déjà utilisé → 400 coupon_already_used."""
    import uuid

    resp = await client.post(
        "/api/v1/loyalty/coupons/issue",
        json={
            "customer_id": str(customer.id),
            "discount_type": "pct",
            "discount_value": 5,
        },
        headers=staff_headers(manager),
    )
    code = resp.json()["code"]
    fake_order = str(uuid.uuid4())

    await client.post(
        f"/api/v1/loyalty/coupons/{code}/apply?order_id={fake_order}",
        headers=staff_headers(manager),
    )
    r2 = await client.post(
        f"/api/v1/loyalty/coupons/{code}/apply?order_id={fake_order}",
        headers=staff_headers(manager),
    )
    assert r2.status_code == 400
    assert r2.json()["code"] == "coupon_already_used"


# ── Templates de carte ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_card_template(client: AsyncClient, manager, db: AsyncSession):
    resp = await client.post(
        "/api/v1/loyalty/card-templates",
        json={
            "name": "Carte Or",
            "background_color": "#FFD700",
            "text_color": "#000000",
        },
        headers=staff_headers(manager),
    )
    assert resp.status_code == 200
    assert resp.json()["background_color"] == "#FFD700"


# ── Tier auto-promotion (Sprint 3) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tier_multiplier_applies_after_promotion(
    client: AsyncClient, manager, customer, db: AsyncSession
):
    """Tier 2x : après promotion auto, le gain suivant est doublé."""
    prog = await _create_program(client, manager)
    await _activate_program(client, manager, prog["id"])

    # Tier Or : min_points=0 → affecté dès le premier gain
    tier_resp = await client.post(
        f"/api/v1/loyalty/programs/{prog['id']}/tiers",
        json={"name": "Or", "min_points": 0, "multiplier": 2.0},
        headers=staff_headers(manager),
    )
    assert tier_resp.status_code == 200

    card_resp = await client.post(
        "/api/v1/loyalty/cards/issue",
        json={"customer_id": str(customer.id), "program_id": prog["id"]},
        headers=staff_headers(manager),
    )
    card_id = card_resp.json()["id"]

    # Premier gain sans tier encore → multiplier=1.0 → 10000×0.01=100 pts
    first = await client.post(
        f"/api/v1/loyalty/cards/{card_id}/earn",
        json={"card_id": card_id, "amount_xof": 10000},
        headers=staff_headers(manager),
    )
    assert first.status_code == 200
    assert first.json()["points_delta"] == 100

    # Auto-promotion a eu lieu (min_points=0 ≤ 100)
    card = await client.get(f"/api/v1/loyalty/cards/{card_id}", headers=staff_headers(manager))
    assert card.json()["tier_id"] is not None

    # Deuxième gain avec multiplier=2.0 → 10000×0.01×2.0=200 pts
    second = await client.post(
        f"/api/v1/loyalty/cards/{card_id}/earn",
        json={"card_id": card_id, "amount_xof": 10000},
        headers=staff_headers(manager),
    )
    assert second.status_code == 200
    assert second.json()["points_delta"] == 200


@pytest.mark.asyncio
async def test_tier_auto_promotion_on_earn(
    client: AsyncClient, manager, customer, db: AsyncSession
):
    """Franchir le seuil min_points d'un tier déclenche la promotion automatique."""
    prog = await _create_program(client, manager)
    await _activate_program(client, manager, prog["id"])

    # Tier Argent : seuil 50 pts, multiplier 1.5
    tier_resp = await client.post(
        f"/api/v1/loyalty/programs/{prog['id']}/tiers",
        json={"name": "Argent", "min_points": 50, "multiplier": 1.5},
        headers=staff_headers(manager),
    )
    tier_id = tier_resp.json()["id"]

    card_resp = await client.post(
        "/api/v1/loyalty/cards/issue",
        json={"customer_id": str(customer.id), "program_id": prog["id"]},
        headers=staff_headers(manager),
    )
    card_id = card_resp.json()["id"]
    assert card_resp.json()["tier_id"] is None

    # Earn 5000 XOF = 50 pts → balance=50 ≥ 50 → promotion Argent
    await client.post(
        f"/api/v1/loyalty/cards/{card_id}/earn",
        json={"card_id": card_id, "amount_xof": 5000},
        headers=staff_headers(manager),
    )

    card = await client.get(f"/api/v1/loyalty/cards/{card_id}", headers=staff_headers(manager))
    assert card.json()["tier_id"] == tier_id


# ── Multi-tenant isolation ─────────────────────────────────────────────────────

# ── Intelligence RFM (Sprint 5) ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_intelligence_list_empty(client: AsyncClient, manager, db: AsyncSession):
    """Avant recompute : aucun score client."""
    resp = await client.get(
        "/api/v1/loyalty/intelligence/customers",
        headers=staff_headers(manager),
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_intelligence_recompute(client: AsyncClient, manager, db: AsyncSession):
    """POST /intelligence/recompute retourne les stats (0 clients sans paiements confirmés)."""
    resp = await client.post(
        "/api/v1/loyalty/intelligence/recompute",
        headers=staff_headers(manager),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "computed_customers" in data
    assert "computed_at" in data
    assert data["computed_customers"] == 0


@pytest.mark.asyncio
async def test_customer_profile(client: AsyncClient, manager, customer, db: AsyncSession):
    """GET /loyalty/customers/{id}/profile retourne le profil enrichi."""
    resp = await client.get(
        f"/api/v1/loyalty/customers/{customer.id}/profile",
        headers=staff_headers(manager),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["customer_id"] == str(customer.id)
    assert data["score"] is None
    assert data["cards"] == []
    assert data["total_spent_xof"] == 0
    assert data["order_count"] == 0
    assert data["segment"] is None


# ── Multi-tenant isolation ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_loyalty_tenant_isolation(
    client: AsyncClient, manager, manager2, customer, db: AsyncSession
):
    """Un manager ne voit que les programmes de son entreprise."""
    # manager crée un programme
    await _create_program(client, manager)

    # manager2 ne doit pas voir les programmes de manager
    resp = await client.get("/api/v1/loyalty/programs", headers=staff_headers(manager2))
    assert resp.status_code == 200
    assert len(resp.json()) == 0
