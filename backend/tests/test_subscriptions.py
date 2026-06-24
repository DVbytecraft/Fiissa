"""
Tests du cycle de vie des abonnements :
- Création trial automatique
- Changement de plan
- Auto-suspension en cas d'expiration
- Réactivation après paiement de facture
"""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_subscription_creates_trial_if_missing(db, company, manager, staff_headers, client):
    """GET /me/subscription crée un abonnement trial si absent."""
    headers = staff_headers(manager)
    response = await client.get("/api/v1/companies/me/subscription", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("trial", "active")


@pytest.mark.asyncio
async def test_subscription_service_get_or_create(db, company):
    from apps.companies.service import SubscriptionService
    from apps.companies.models import Subscription
    from sqlalchemy import select

    # Supprimer l'abonnement existant créé par le fixture
    result = await db.execute(select(Subscription).where(Subscription.company_id == company.id))
    existing = result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.commit()

    service = SubscriptionService(db)
    sub = await service.get_or_create_subscription(company.id)
    await db.commit()

    assert sub.status == "trial"
    assert sub.plan == "starter"
    assert sub.trial_ends_at is not None
    assert sub.trial_ends_at > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_change_plan_creates_invoice(db, company):
    from apps.companies.models import Plan, SubscriptionInvoice
    from apps.companies.service import SubscriptionService
    from sqlalchemy import select

    plan = Plan(
        code="pro_monthly",
        name="Pro Mensuel",
        billing_cycle="monthly",
        amount_xof=25000,
        commission_rate=0.015,
        is_active=True,
    )
    db.add(plan)
    await db.commit()

    service = SubscriptionService(db)
    sub = await service.change_plan(company.id, "pro_monthly")
    await db.commit()

    assert sub.status == "active"
    assert sub.plan == "pro_monthly"
    assert sub.amount_xof == 25000

    result = await db.execute(
        select(SubscriptionInvoice).where(SubscriptionInvoice.company_id == company.id)
    )
    invoices = result.scalars().all()
    assert len(invoices) >= 1
    assert invoices[-1].amount_xof == 25000
    assert invoices[-1].status == "issued"


@pytest.mark.asyncio
async def test_invoice_number_is_sequential_and_unique(db, company):
    from apps.companies.models import Plan, SubscriptionInvoice
    from apps.companies.service import SubscriptionService
    from sqlalchemy import select

    # Les codes de plan DOIVENT correspondre aux valeurs de l'enum subscription_plan_enum
    # (starter, pro, enterprise) car Subscription.plan est un champ enum SQLAlchemy
    for code, name, amount in [("starter", "Starter Mensuel", 5000), ("enterprise", "Enterprise Mensuel", 50000)]:
        plan = Plan(
            code=code,
            name=name,
            billing_cycle="monthly",
            amount_xof=amount,
            commission_rate=0.01,
            is_active=True,
        )
        db.add(plan)
    await db.commit()

    service = SubscriptionService(db)
    await service.change_plan(company.id, "starter")
    await db.commit()
    await service.change_plan(company.id, "enterprise")
    await db.commit()

    result = await db.execute(
        select(SubscriptionInvoice).where(SubscriptionInvoice.company_id == company.id)
    )
    invoices = result.scalars().all()
    numbers = [inv.invoice_number for inv in invoices]
    assert len(numbers) == len(set(numbers)), "Numéros de factures dupliqués !"


@pytest.mark.asyncio
async def test_suspend_expired_subscriptions(db, company):
    """Les abonnements dont current_period_end est passé doivent être suspendus."""
    from apps.companies.models import Subscription, Company
    from apps.companies.service import SubscriptionService
    from sqlalchemy import select

    result = await db.execute(select(Subscription).where(Subscription.company_id == company.id))
    sub = result.scalar_one_or_none()
    if not sub:
        sub = Subscription(company_id=company.id, plan="starter", status="active")
        db.add(sub)
        await db.flush()

    # Mettre l'expiration dans le passé
    sub.status = "active"
    sub.current_period_end = datetime.now(timezone.utc) - timedelta(days=1)
    await db.commit()

    count = await SubscriptionService.suspend_expired_subscriptions(db)
    assert count >= 1

    await db.refresh(sub)
    assert sub.status == "suspended"

    result2 = await db.execute(select(Company).where(Company.id == company.id))
    company_refreshed = result2.scalar_one_or_none()
    assert company_refreshed.is_suspended is True


@pytest.mark.asyncio
async def test_mark_invoice_paid_reactivates_company(db, company):
    """Payer une facture doit réactiver une company suspendue."""
    from apps.companies.models import Subscription, SubscriptionInvoice, Company
    from apps.companies.service import SubscriptionService
    from sqlalchemy import select

    # Setup: suspension
    result = await db.execute(select(Subscription).where(Subscription.company_id == company.id))
    sub = result.scalar_one_or_none()
    if not sub:
        sub = Subscription(company_id=company.id, plan="starter", status="suspended")
        db.add(sub)
        await db.flush()
    else:
        sub.status = "suspended"
        sub.billing_cycle = "monthly"

    company.is_suspended = True
    company.is_active = False

    invoice = SubscriptionInvoice(
        company_id=company.id,
        subscription_id=sub.id,
        invoice_number="INV-2026-REACTIVATE",
        status="issued",
        amount_xof=25000,
        tax_xof=0,
        total_xof=25000,
    )
    db.add(invoice)
    await db.commit()

    service = SubscriptionService(db)
    paid_invoice = await service.mark_invoice_paid(company.id, invoice.id)
    await db.commit()

    assert paid_invoice.status == "paid"
    assert paid_invoice.paid_at is not None

    await db.refresh(sub)
    assert sub.status == "active"

    result2 = await db.execute(select(Company).where(Company.id == company.id))
    c = result2.scalar_one_or_none()
    assert c.is_suspended is False
    assert c.is_active is True


@pytest.mark.asyncio
async def test_cancel_subscription(db, company):
    from apps.companies.service import SubscriptionService

    service = SubscriptionService(db)
    sub = await service.cancel_subscription(company.id)
    await db.commit()

    assert sub.status == "cancelled"
    assert sub.cancelled_at is not None


@pytest.mark.asyncio
async def test_subscription_list_invoices_api(client, db, company, manager, staff_headers):
    from apps.companies.models import Plan
    plan = Plan(code="pro_api", name="Pro API", billing_cycle="monthly", amount_xof=15000, commission_rate=0.01, is_active=True)
    db.add(plan)
    await db.commit()

    from apps.companies.service import SubscriptionService
    service = SubscriptionService(db)
    await service.change_plan(company.id, "pro_api")
    await db.commit()

    headers = staff_headers(manager)
    response = await client.get("/api/v1/companies/me/subscription/invoices", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1
