"""
Script de seed : crée le super-admin initial et les données de démo.
Usage : python scripts/seed.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")

from core.database import AsyncSessionLocal
from core.config import settings
from core.security import hash_password


async def create_superadmin():
    async with AsyncSessionLocal() as db:
        from apps.users.models import User, UserCompanyRole
        from sqlalchemy import select

        result = await db.execute(
            select(User).where(User.email == settings.SUPERADMIN_EMAIL)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"[SEED] Super-admin existe déjà : {settings.SUPERADMIN_EMAIL}")
            return

        user = User(
            email=settings.SUPERADMIN_EMAIL,
            phone=settings.SUPERADMIN_PHONE,
            password_hash=hash_password(settings.SUPERADMIN_PASSWORD),
            first_name="Super",
            last_name="Admin",
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.flush()

        role = UserCompanyRole(
            user_id=user.id,
            role="super_admin",
        )
        db.add(role)
        await db.commit()
        print(f"[SEED] Super-admin créé : {settings.SUPERADMIN_EMAIL}")


async def create_demo_data():
    """Données de démonstration pour le développement."""
    async with AsyncSessionLocal() as db:
        from apps.companies.models import Company, Subscription
        from apps.stores.models import Store
        from apps.users.models import User, UserCompanyRole
        from apps.catalog.models import Category, Product
        from sqlalchemy import select

        # Vérifier si les données de démo existent déjà
        result = await db.execute(select(Company).where(Company.slug == "supermarche-demo"))
        if result.scalar_one_or_none():
            print("[SEED] Données de démo déjà présentes")
            return

        # Entreprise
        company = Company(
            name="Supermarché Fatou",
            slug="supermarche-fatou",
            type="supermarket",
            country="SN",
            currency="XOF",
            is_active=True,
            contact_phone="+221771234567",
        )
        db.add(company)
        await db.flush()

        sub = Subscription(
            company_id=company.id,
            plan="pro",
            status="active",
            amount_xof=25000,
            commission_rate=0.015,
        )
        db.add(sub)

        # Magasin
        store = Store(
            company_id=company.id,
            name="Fatou Centre-Ville",
            slug="fatou-centre",
            is_active=True,
            delivery_enabled=True,
            click_collect_enabled=True,
            delivery_fee_xof=500,
            mobile_money_info={
                "operator": "wave",
                "number": "77 123 45 67",
                "account_name": "Supermarché Fatou",
            },
            address={"city": "Dakar", "quartier": "Plateau"},
        )
        db.add(store)
        await db.flush()

        # Gérant
        manager = User(
            email="gerant@fatou.sn",
            password_hash=hash_password("Demo1234!"),
            first_name="Fatou",
            last_name="Ndiaye",
            phone="+221771234567",
            is_active=True,
            is_verified=True,
        )
        db.add(manager)
        await db.flush()

        db.add(UserCompanyRole(user_id=manager.id, company_id=company.id, role="company_owner"))

        # Catégories
        cat_alimentation = Category(
            company_id=company.id, name="Alimentation", slug="alimentation", position=1
        )
        cat_boissons = Category(
            company_id=company.id, name="Boissons", slug="boissons", position=2
        )
        db.add_all([cat_alimentation, cat_boissons])
        await db.flush()

        # Produits
        products = [
            Product(company_id=company.id, store_id=store.id, category_id=cat_alimentation.id,
                    name="Riz Brisé 5kg", price_xof=3500, barcode="1234567890123",
                    track_stock=True, stock_quantity=150, unit="sac"),
            Product(company_id=company.id, store_id=store.id, category_id=cat_alimentation.id,
                    name="Huile Végétale 1L", price_xof=1200, barcode="9876543210987",
                    track_stock=True, stock_quantity=80, unit="bouteille"),
            Product(company_id=company.id, store_id=store.id, category_id=cat_alimentation.id,
                    name="Sucre 1kg", price_xof=750, track_stock=True, stock_quantity=200, unit="kg"),
            Product(company_id=company.id, store_id=store.id, category_id=cat_boissons.id,
                    name="Eau minérale 1.5L", price_xof=500, barcode="1111111111111",
                    track_stock=True, stock_quantity=500, unit="bouteille"),
            Product(company_id=company.id, store_id=store.id, category_id=cat_boissons.id,
                    name="Jus de Bissap 33cl", price_xof=350, track_stock=False, unit="canette"),
            Product(company_id=company.id, store_id=store.id, category_id=cat_alimentation.id,
                    name="Pain de mie", price_xof=650, track_stock=False, unit="paquet"),
        ]
        db.add_all(products)

        await db.commit()
        print(f"[SEED] Données démo créées : {company.name}")
        print(f"       Gérant : gerant@fatou.sn / Demo1234!")
        print(f"       Magasin ID : {store.id}")


async def main():
    print("=== SmartCheckout — Initialisation base de données ===")
    await create_superadmin()
    if settings.ENVIRONMENT != "production":
        await create_demo_data()
    print("=== Terminé ===")


if __name__ == "__main__":
    asyncio.run(main())
