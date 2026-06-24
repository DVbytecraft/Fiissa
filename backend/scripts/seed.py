#!/usr/bin/env python3
"""
Fiissa — Seed data pour démo / tests d'intégration.

Lance : cd backend && python -m scripts.seed
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Charger l'environnement avant les imports métier
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://fiissa:fiissa@localhost:5432/fiissa")
os.environ.setdefault("SECRET_KEY", "seed-secret-key-change-in-production")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from core.config import settings
from core.database import Base
from core.security import hash_password, generate_pickup_code, generate_verification_code


PRODUCTS_SEED = [
    # (name, barcode, price_xof, category, unit, stock)
    ("Riz parfumé 5kg",         "6111242390673", 3500,  "Alimentation",  "sac",    80),
    ("Riz brisé 25kg",          "6111242390674", 12500, "Alimentation",  "sac",    30),
    ("Huile végétale 5L",       "6111242390675", 4200,  "Alimentation",  "bouteille", 50),
    ("Sucre raffiné 1kg",       "6111242390676", 800,   "Alimentation",  "paquet", 120),
    ("Farine de blé 50kg",      "6111242390677", 22000, "Alimentation",  "sac",    20),
    ("Savon Omo 500g",          "6111242390678", 650,   "Hygiène",       "piece",  200),
    ("Eau minérale 1.5L",       "6111242390679", 300,   "Boissons",      "bouteille", 300),
    ("Jus orange 1L",           "6111242390680", 750,   "Boissons",      "bouteille", 100),
    ("Lait Soja 500ml",         "6111242390681", 550,   "Boissons",      "bouteille", 80),
    ("Pain de sucre 2kg",       "6111242390682", 1400,  "Alimentation",  "paquet", 60),
    ("Maïs grain 5kg",          "6111242390683", 2200,  "Alimentation",  "sac",    40),
    ("Mil 5kg",                 "6111242390684", 1800,  "Alimentation",  "sac",    35),
    ("Tomate concentrée 400g",  "6111242390685", 450,   "Alimentation",  "boite",  150),
    ("Sardine SIFCA 200g",      "6111242390686", 650,   "Alimentation",  "boite",  200),
    ("Savon de marseille",      "6111242390687", 350,   "Hygiène",       "piece",  180),
    ("Shampoing 400ml",         "6111242390688", 1200,  "Hygiène",       "bouteille", 60),
    ("Dentifrice 75ml",         "6111242390689", 600,   "Hygiène",       "tube",   90),
    ("Lessive liquide 2L",      "6111242390690", 2500,  "Hygiène",       "bouteille", 45),
    ("Bougie 12 pièces",        "6111242390691", 500,   "Maison",        "paquet", 100),
    ("Huile de palme 1L",       "6111242390692", 1100,  "Alimentation",  "bouteille", 70),
]


async def run_seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        print("━" * 60)
        print("  Fiissa — Seed data")
        print("━" * 60)

        # ── 1. Entreprise ──────────────────────────────────────────
        from apps.companies.models import Company, Subscription, CompanySetting
        from sqlalchemy import select

        result = await db.execute(select(Company).where(Company.slug == "supermarche-demo"))
        company = result.scalar_one_or_none()

        if not company:
            company = Company(
                name="Supermarché Fiissa Démo",
                slug="supermarche-demo",
                type="supermarket",
                country="SN",
                currency="XOF",
                contact_email="demo@fiissa.com",
                contact_phone="+221771234567",
                is_active=True,
            )
            db.add(company)
            await db.flush()

            subscription = Subscription(
                company_id=company.id,
                plan="pro",
                status="active",
                started_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            )
            db.add(subscription)

            setting = CompanySetting(
                company_id=company.id,
                currency="XOF",
                timezone="Africa/Dakar",
                language="fr",
                catalog_mode="internal",
                payment_mode="manual",
                delivery_mode="click_collect",
            )
            db.add(setting)
            print(f"  ✓ Entreprise créée : {company.name} [{company.id}]")
        else:
            print(f"  · Entreprise existante : {company.name}")

        # ── 2. Magasin ─────────────────────────────────────────────
        from apps.stores.models import Store

        result = await db.execute(select(Store).where(Store.company_id == company.id))
        store = result.scalar_one_or_none()

        if not store:
            store = Store(
                company_id=company.id,
                name="Magasin Central Dakar",
                slug="magasin-central-dakar",
                address={"rue": "Avenue Bourguiba", "ville": "Dakar", "pays": "SN"},
                phone="+221771234567",
                mobile_money_info={
                    "operator": "wave",
                    "number": "77 123 45 67",
                    "account_name": "Supermarché Fiissa Démo",
                },
                click_collect_enabled=True,
                delivery_enabled=True,
                scan_go_enabled=True,
                delivery_fee_xof=500,
                free_delivery_threshold_xof=10000,
                opening_hours={
                    "lun": "08:00-21:00", "mar": "08:00-21:00", "mer": "08:00-21:00",
                    "jeu": "08:00-21:00", "ven": "08:00-21:00", "sam": "08:00-22:00",
                    "dim": "09:00-18:00",
                },
                is_active=True,
            )
            db.add(store)
            await db.flush()
            print(f"  ✓ Magasin créé : {store.name} [{store.id}]")
        else:
            print(f"  · Magasin existant : {store.name}")

        # ── 3. Catalogue (20 produits) ─────────────────────────────
        from apps.catalog.models import Category, Product

        categories: dict[str, Category] = {}
        products_created = 0

        for name, barcode, price_xof, cat_name, unit, stock in PRODUCTS_SEED:
            # Catégorie
            if cat_name not in categories:
                cat_slug = cat_name.lower().replace(" ", "-")
                result = await db.execute(
                    select(Category).where(
                        Category.company_id == company.id,
                        Category.slug == cat_slug,
                    )
                )
                cat = result.scalar_one_or_none()
                if not cat:
                    cat = Category(
                        company_id=company.id,
                        store_id=store.id,
                        name=cat_name,
                        slug=cat_slug,
                        is_active=True,
                    )
                    db.add(cat)
                    await db.flush()
                categories[cat_name] = cat

            # Produit
            result = await db.execute(
                select(Product).where(
                    Product.company_id == company.id,
                    Product.barcode == barcode,
                )
            )
            existing = result.scalar_one_or_none()
            if not existing:
                product = Product(
                    company_id=company.id,
                    store_id=store.id,
                    category_id=categories[cat_name].id,
                    name=name,
                    barcode=barcode,
                    unit=unit,
                    price_xof=price_xof,
                    is_available=True,
                    track_stock=True,
                    stock_quantity=stock,
                    stock_alert_qty=max(5, stock // 10),
                    source_type="internal",
                )
                db.add(product)
                products_created += 1

        await db.flush()
        print(f"  ✓ Catalogue : {products_created} produits créés / {len(PRODUCTS_SEED)} total")

        # ── 4. Utilisateurs ────────────────────────────────────────
        from apps.users.models import User, UserCompanyRole

        # Client
        result = await db.execute(select(User).where(User.phone == "+221770000001"))
        customer = result.scalar_one_or_none()
        if not customer:
            customer = User(
                phone="+221770000001",
                first_name="Fatou",
                last_name="Diallo",
                is_active=True,
                is_verified=True,
            )
            db.add(customer)
            await db.flush()
            db.add(UserCompanyRole(user_id=customer.id, role="customer"))
            print(f"  ✓ Client créé : {customer.first_name} {customer.last_name}")
        else:
            print(f"  · Client existant : {customer.first_name}")

        # Propriétaire
        result = await db.execute(select(User).where(User.email == "owner@fiissa-demo.com"))
        owner = result.scalar_one_or_none()
        if not owner:
            owner = User(
                email="owner@fiissa-demo.com",
                phone="+221770000002",
                first_name="Mamadou",
                last_name="Sow",
                password_hash=hash_password("Demo1234!"),
                is_active=True,
                is_verified=True,
            )
            db.add(owner)
            await db.flush()
            db.add(UserCompanyRole(
                user_id=owner.id,
                company_id=company.id,
                role="company_owner",
            ))
            print(f"  ✓ Propriétaire créé : {owner.first_name} (email: owner@fiissa-demo.com, pw: Demo1234!)")
        else:
            print(f"  · Propriétaire existant : {owner.first_name}")

        # Manager
        result = await db.execute(select(User).where(User.email == "manager@fiissa-demo.com"))
        manager = result.scalar_one_or_none()
        if not manager:
            manager = User(
                email="manager@fiissa-demo.com",
                phone="+221770000003",
                first_name="Aissatou",
                last_name="Ba",
                password_hash=hash_password("Demo1234!"),
                is_active=True,
                is_verified=True,
            )
            db.add(manager)
            await db.flush()
            db.add(UserCompanyRole(
                user_id=manager.id,
                company_id=company.id,
                role="store_manager",
            ))
            print(f"  ✓ Manager créé : {manager.first_name} (email: manager@fiissa-demo.com, pw: Demo1234!)")
        else:
            print(f"  · Manager existant : {manager.first_name}")

        await db.flush()

        # ── 5. Commande ────────────────────────────────────────────
        from apps.orders.models import Order, OrderItem, Pickup, OrderQRCode

        result = await db.execute(
            select(Order).where(
                Order.company_id == company.id,
                Order.customer_id == customer.id,
            )
        )
        existing_order = result.scalar_one_or_none()

        if not existing_order:
            result = await db.execute(
                select(Product).where(
                    Product.company_id == company.id,
                    Product.is_available == True,
                ).limit(3)
            )
            demo_products = result.scalars().all()

            subtotal = sum(p.price_xof for p in demo_products)
            order = Order(
                company_id=company.id,
                store_id=store.id,
                customer_id=customer.id,
                order_number="SC-2026-00001",
                type="click_collect",
                status="confirmed",
                subtotal_xof=subtotal,
                delivery_fee_xof=0,
                total_xof=subtotal,
                pickup_code=generate_pickup_code(),
                payment_expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
            )
            db.add(order)
            await db.flush()

            for p in demo_products:
                db.add(OrderItem(
                    order_id=order.id,
                    product_id=p.id,
                    product_name=p.name,
                    product_barcode=p.barcode,
                    unit_price_xof=p.price_xof,
                    quantity=1,
                    subtotal_xof=p.price_xof,
                ))

            db.add(Pickup(
                company_id=company.id,
                order_id=order.id,
                pickup_code=order.pickup_code,
            ))
            db.add(OrderQRCode(
                company_id=company.id,
                order_id=order.id,
                code=generate_verification_code(16),
                type="pickup",
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            ))
            print(f"  ✓ Commande créée : {order.order_number} — {order.total_xof} XOF")
        else:
            order = existing_order
            print(f"  · Commande existante : {order.order_number}")

        # ── 6. Paiement ────────────────────────────────────────────
        from apps.payments.models import Payment

        result = await db.execute(
            select(Payment).where(Payment.order_id == order.id)
        )
        existing_payment = result.scalar_one_or_none()

        if not existing_payment:
            payment = Payment(
                company_id=company.id,
                store_id=store.id,
                order_id=order.id,
                customer_id=customer.id,
                payment_number="PAY-2026-00001",
                method="mobile_money",
                operator="wave",
                amount_xof=order.total_xof,
                status="confirmed",
                transaction_ref="WAVE-SEED-TX-001",
                sender_phone=customer.phone,
                confirmed_at=datetime.now(timezone.utc),
            )
            db.add(payment)
            await db.flush()
            print(f"  ✓ Paiement créé : {payment.payment_number} — {payment.amount_xof} XOF [confirmé]")
        else:
            payment = existing_payment
            print(f"  · Paiement existant : {payment.payment_number}")

        # ── 7. Reçu ───────────────────────────────────────────────
        from apps.receipts.models import Receipt

        result = await db.execute(
            select(Receipt).where(Receipt.order_id == order.id)
        )
        existing_receipt = result.scalar_one_or_none()

        if not existing_receipt:
            from apps.receipts.service import ReceiptService
            order.status = "delivered"
            await db.flush()
            try:
                receipt_service = ReceiptService(db)
                receipt = await receipt_service.generate_receipt(payment.id)
                print(f"  ✓ Reçu généré : {receipt.receipt_number} — {receipt.amount_xof} XOF")
            except Exception as e:
                print(f"  ⚠ Reçu non généré (service): {e}")
        else:
            print(f"  · Reçu existant : {existing_receipt.receipt_number}")

        await db.commit()
        print()
        print("━" * 60)
        print("  SEED TERMINÉ")
        print("━" * 60)
        print(f"  Entreprise    : {company.name}")
        print(f"  Magasin       : {store.name}")
        print(f"  Produits      : {len(PRODUCTS_SEED)} référence(s)")
        print(f"  Client        : {customer.phone}")
        print(f"  Propriétaire  : owner@fiissa-demo.com / Demo1234!")
        print(f"  Manager       : manager@fiissa-demo.com / Demo1234!")
        print(f"  Commande      : {order.order_number} ({order.status})")
        print(f"  Paiement      : {payment.payment_number} ({payment.status})")
        print("━" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_seed())
