"""
Loyalty Engine Service — Sprint 2

Services :
  LoyaltyProgramService  — CRUD programmes fidélité (jamais auto-créé)
  LoyaltyTierService     — CRUD niveaux
  CardTemplateService    — CRUD templates de carte
  LoyaltyCardService     — Émission native + import externe
  LoyaltyTransactionService — Earn/redeem (ledger append-only)
  LoyaltyRewardService   — CRUD récompenses
  LoyaltyCouponService   — Émission et application de coupons

Règles absolues :
  - Fiissa ne crée JAMAIS automatiquement un programme ou une carte.
  - loyalty_enabled = False tant que le commerçant n'active pas explicitement.
  - loyalty_transactions : append-only (pas d'update/delete).
  - points_balance : valeur commerciale du marchand, pas un solde monétaire Fiissa.
  - Multi-tenant : toutes les requêtes filtrent par company_id.
"""

import secrets
import string
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.loyalty.models import (
    CardTemplate,
    CustomerScore,
    LoyaltyCard,
    LoyaltyCoupon,
    LoyaltyProgram,
    LoyaltyReward,
    LoyaltyTier,
    LoyaltyTransaction,
)
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.users.models import User
from core.exceptions import BadRequestError, ConflictError, NotFoundError


# ── helpers ────────────────────────────────────────────────────────────────────

def _card_number() -> str:
    """Génère un numéro de carte unique à 16 chiffres formaté XXXX-XXXX-XXXX-XXXX."""
    digits = "".join(secrets.choice(string.digits) for _ in range(16))
    return f"{digits[:4]}-{digits[4:8]}-{digits[8:12]}-{digits[12:]}"


def _coupon_code() -> str:
    """Code coupon alphanumérique lisible de 8 chars (ex : FIISSA12)."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


# ── LoyaltyProgramService ──────────────────────────────────────────────────────

class LoyaltyProgramService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, company_id: UUID, data: dict) -> LoyaltyProgram:
        existing = await self.db.execute(
            select(LoyaltyProgram).where(
                LoyaltyProgram.company_id == company_id,
                LoyaltyProgram.name == data["name"],
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError("Un programme avec ce nom existe déjà", "program_name_taken")

        program = LoyaltyProgram(
            company_id=company_id,
            name=data["name"],
            description=data.get("description"),
            points_per_xof=data.get("points_per_xof", 0.01),
            min_spend_xof=data.get("min_spend_xof", 0),
            expiry_months=data.get("expiry_months"),
            loyalty_enabled=False,
            is_active=False,
        )
        self.db.add(program)
        await self.db.flush()
        await self.db.refresh(program)
        return program

    async def get(self, company_id: UUID, program_id: UUID) -> LoyaltyProgram:
        result = await self.db.execute(
            select(LoyaltyProgram).where(
                LoyaltyProgram.id == program_id,
                LoyaltyProgram.company_id == company_id,
            )
        )
        program = result.scalar_one_or_none()
        if not program:
            raise NotFoundError("Programme fidélité")
        return program

    async def list(self, company_id: UUID) -> list[LoyaltyProgram]:
        result = await self.db.execute(
            select(LoyaltyProgram)
            .where(LoyaltyProgram.company_id == company_id)
            .order_by(LoyaltyProgram.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, company_id: UUID, program_id: UUID, data: dict) -> LoyaltyProgram:
        program = await self.get(company_id, program_id)
        allowed = {"name", "description", "points_per_xof", "min_spend_xof", "expiry_months"}
        for key, value in data.items():
            if key in allowed and value is not None:
                setattr(program, key, value)
        await self.db.flush()
        await self.db.refresh(program)
        return program

    async def activate(self, company_id: UUID, program_id: UUID) -> LoyaltyProgram:
        """Active le programme et active loyalty_enabled."""
        program = await self.get(company_id, program_id)
        program.is_active = True
        program.loyalty_enabled = True
        await self.db.flush()
        await self.db.refresh(program)
        return program

    async def deactivate(self, company_id: UUID, program_id: UUID) -> LoyaltyProgram:
        program = await self.get(company_id, program_id)
        program.is_active = False
        await self.db.flush()
        await self.db.refresh(program)
        return program


# ── LoyaltyTierService ─────────────────────────────────────────────────────────

class LoyaltyTierService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, company_id: UUID, program_id: UUID, data: dict) -> LoyaltyTier:
        tier = LoyaltyTier(
            program_id=program_id,
            company_id=company_id,
            name=data["name"],
            min_points=data.get("min_points", 0),
            multiplier=data.get("multiplier", 1.0),
            benefits=data.get("benefits"),
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(tier)
        await self.db.flush()
        await self.db.refresh(tier)
        return tier

    async def list(self, company_id: UUID, program_id: UUID) -> list[LoyaltyTier]:
        result = await self.db.execute(
            select(LoyaltyTier)
            .where(LoyaltyTier.program_id == program_id, LoyaltyTier.company_id == company_id)
            .order_by(LoyaltyTier.sort_order)
        )
        return list(result.scalars().all())


# ── CardTemplateService ────────────────────────────────────────────────────────

class CardTemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, company_id: UUID, data: dict) -> CardTemplate:
        template = CardTemplate(
            company_id=company_id,
            tier_id=data.get("tier_id"),
            name=data["name"],
            background_color=data.get("background_color", "#1A1A2E"),
            text_color=data.get("text_color", "#FFFFFF"),
            logo_url=data.get("logo_url"),
            background_image_url=data.get("background_image_url"),
            is_default=data.get("is_default", False),
        )
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def list(self, company_id: UUID) -> list[CardTemplate]:
        result = await self.db.execute(
            select(CardTemplate)
            .where(CardTemplate.company_id == company_id)
            .order_by(CardTemplate.created_at.desc())
        )
        return list(result.scalars().all())


# ── LoyaltyCardService ─────────────────────────────────────────────────────────

class LoyaltyCardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _unique_card_number(self, company_id: UUID) -> str:
        for _ in range(10):
            candidate = _card_number()
            result = await self.db.execute(
                select(LoyaltyCard).where(
                    LoyaltyCard.company_id == company_id,
                    LoyaltyCard.card_number == candidate,
                )
            )
            if not result.scalar_one_or_none():
                return candidate
        raise RuntimeError("Impossible de générer un numéro de carte unique")

    async def issue_native(
        self,
        company_id: UUID,
        customer_id: UUID,
        program_id: UUID,
        card_template_id: Optional[UUID] = None,
    ) -> LoyaltyCard:
        """
        Émet une carte native pour un client.
        Le programme DOIT être actif (loyalty_enabled=True).
        Fiissa ne crée jamais automatiquement une carte.
        """
        prog_result = await self.db.execute(
            select(LoyaltyProgram).where(
                LoyaltyProgram.id == program_id,
                LoyaltyProgram.company_id == company_id,
            )
        )
        program = prog_result.scalar_one_or_none()
        if not program:
            raise NotFoundError("Programme fidélité")
        if not program.is_active or not program.loyalty_enabled:
            raise BadRequestError(
                "Le programme fidélité doit être actif pour émettre une carte",
                "program_not_active",
            )

        # Une seule carte native active par (client, programme)
        existing = await self.db.execute(
            select(LoyaltyCard).where(
                LoyaltyCard.customer_id == customer_id,
                LoyaltyCard.program_id == program_id,
                LoyaltyCard.card_type == "native",
                LoyaltyCard.status == "active",
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                "Ce client possède déjà une carte active pour ce programme",
                "card_already_exists",
            )

        card_number = await self._unique_card_number(company_id)
        card = LoyaltyCard(
            company_id=company_id,
            customer_id=customer_id,
            program_id=program_id,
            card_template_id=card_template_id,
            card_number=card_number,
            card_type="native",
            status="active",
        )
        self.db.add(card)
        await self.db.flush()
        await self.db.refresh(card)
        return card

    async def import_external(
        self,
        company_id: UUID,
        customer_id: UUID,
        external_issuer: str,
        external_ref: str,
        card_template_id: Optional[UUID] = None,
    ) -> LoyaltyCard:
        card_number = await self._unique_card_number(company_id)
        card = LoyaltyCard(
            company_id=company_id,
            customer_id=customer_id,
            card_number=card_number,
            card_type="external",
            external_issuer=external_issuer,
            external_ref=external_ref,
            card_template_id=card_template_id,
            status="active",
        )
        self.db.add(card)
        await self.db.flush()
        await self.db.refresh(card)
        return card

    async def get(self, company_id: UUID, card_id: UUID) -> LoyaltyCard:
        result = await self.db.execute(
            select(LoyaltyCard).where(
                LoyaltyCard.id == card_id,
                LoyaltyCard.company_id == company_id,
            )
        )
        card = result.scalar_one_or_none()
        if not card:
            raise NotFoundError("Carte fidélité")
        return card

    async def list_for_customer(
        self, company_id: UUID, customer_id: UUID
    ) -> list[LoyaltyCard]:
        result = await self.db.execute(
            select(LoyaltyCard)
            .where(
                LoyaltyCard.company_id == company_id,
                LoyaltyCard.customer_id == customer_id,
            )
            .order_by(LoyaltyCard.issued_at.desc())
        )
        return list(result.scalars().all())

    async def list_own(self, customer_id: UUID) -> list[LoyaltyCard]:
        """Toutes les cartes du client, toutes entreprises confondues."""
        result = await self.db.execute(
            select(LoyaltyCard)
            .where(LoyaltyCard.customer_id == customer_id)
            .order_by(LoyaltyCard.issued_at.desc())
        )
        return list(result.scalars().all())


# ── LoyaltyTransactionService ──────────────────────────────────────────────────

class LoyaltyTransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_active_card(self, company_id: UUID, card_id: UUID) -> LoyaltyCard:
        result = await self.db.execute(
            select(LoyaltyCard).where(
                LoyaltyCard.id == card_id,
                LoyaltyCard.company_id == company_id,
            )
        )
        card = result.scalar_one_or_none()
        if not card:
            raise NotFoundError("Carte fidélité")
        if card.status != "active":
            raise BadRequestError("La carte n'est pas active", "card_not_active")
        return card

    async def earn(
        self,
        company_id: UUID,
        card_id: UUID,
        amount_xof: int,
        order_id: Optional[UUID] = None,
        description: Optional[str] = None,
    ) -> LoyaltyTransaction:
        """
        Calcule et crédite les points en fonction de amount_xof et du taux du programme.
        Crédit minimum : 1 point.
        """
        card = await self._get_active_card(company_id, card_id)

        points_to_earn = 0
        if card.program_id:
            prog = await self.db.get(LoyaltyProgram, card.program_id)
            if prog and prog.is_active:
                if amount_xof >= prog.min_spend_xof:
                    multiplier = 1.0
                    if card.tier_id:
                        tier = await self.db.get(LoyaltyTier, card.tier_id)
                        if tier:
                            multiplier = float(tier.multiplier)
                    points_to_earn = max(1, int(amount_xof * float(prog.points_per_xof) * multiplier))

        before = card.points_balance
        card.points_balance += points_to_earn
        after = card.points_balance

        if card.program_id and points_to_earn > 0:
            tier_result = await self.db.execute(
                select(LoyaltyTier)
                .where(
                    LoyaltyTier.program_id == card.program_id,
                    LoyaltyTier.company_id == card.company_id,
                    LoyaltyTier.min_points <= card.points_balance,
                )
                .order_by(LoyaltyTier.min_points.desc())
                .limit(1)
            )
            best_tier = tier_result.scalar_one_or_none()
            if best_tier and card.tier_id != best_tier.id:
                card.tier_id = best_tier.id

        tx = LoyaltyTransaction(
            company_id=company_id,
            card_id=card.id,
            customer_id=card.customer_id,
            order_id=order_id,
            type="earn",
            points_delta=points_to_earn,
            points_before=before,
            points_after=after,
            description=description or f"Achat {amount_xof} XOF",
        )
        self.db.add(tx)
        await self.db.flush()
        await self.db.refresh(tx)
        return tx

    async def redeem(
        self,
        company_id: UUID,
        card_id: UUID,
        points: int,
        order_id: Optional[UUID] = None,
        description: Optional[str] = None,
    ) -> LoyaltyTransaction:
        card = await self._get_active_card(company_id, card_id)
        if card.points_balance < points:
            raise BadRequestError(
                f"Solde insuffisant : {card.points_balance} points disponibles",
                "insufficient_points",
            )

        before = card.points_balance
        card.points_balance -= points
        after = card.points_balance

        tx = LoyaltyTransaction(
            company_id=company_id,
            card_id=card.id,
            customer_id=card.customer_id,
            order_id=order_id,
            type="redeem",
            points_delta=-points,
            points_before=before,
            points_after=after,
            description=description or f"Utilisation de {points} points",
        )
        self.db.add(tx)
        await self.db.flush()
        await self.db.refresh(tx)
        return tx

    async def list_for_card(
        self, company_id: UUID, card_id: UUID, limit: int = 50
    ) -> list[LoyaltyTransaction]:
        result = await self.db.execute(
            select(LoyaltyTransaction)
            .where(
                LoyaltyTransaction.card_id == card_id,
                LoyaltyTransaction.company_id == company_id,
            )
            .order_by(LoyaltyTransaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


# ── LoyaltyRewardService ───────────────────────────────────────────────────────

class LoyaltyRewardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, company_id: UUID, program_id: UUID, data: dict) -> LoyaltyReward:
        reward = LoyaltyReward(
            company_id=company_id,
            program_id=program_id,
            name=data["name"],
            description=data.get("description"),
            points_cost=data["points_cost"],
            reward_type=data["reward_type"],
            value=data.get("value", 0),
            max_redemptions=data.get("max_redemptions"),
            valid_from=data.get("valid_from"),
            valid_until=data.get("valid_until"),
        )
        self.db.add(reward)
        await self.db.flush()
        await self.db.refresh(reward)
        return reward

    async def list(self, company_id: UUID, program_id: UUID) -> list[LoyaltyReward]:
        result = await self.db.execute(
            select(LoyaltyReward)
            .where(
                LoyaltyReward.company_id == company_id,
                LoyaltyReward.program_id == program_id,
                LoyaltyReward.is_active == True,
            )
            .order_by(LoyaltyReward.points_cost)
        )
        return list(result.scalars().all())

    async def get(self, company_id: UUID, reward_id: UUID) -> LoyaltyReward:
        result = await self.db.execute(
            select(LoyaltyReward).where(
                LoyaltyReward.id == reward_id,
                LoyaltyReward.company_id == company_id,
            )
        )
        reward = result.scalar_one_or_none()
        if not reward:
            raise NotFoundError("Récompense")
        return reward


# ── LoyaltyCouponService ───────────────────────────────────────────────────────

class LoyaltyCouponService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _unique_code(self) -> str:
        for _ in range(10):
            candidate = _coupon_code()
            result = await self.db.execute(
                select(LoyaltyCoupon).where(LoyaltyCoupon.code == candidate)
            )
            if not result.scalar_one_or_none():
                return candidate
        raise RuntimeError("Impossible de générer un code coupon unique")

    async def issue(self, company_id: UUID, data: dict) -> LoyaltyCoupon:
        code = await self._unique_code()
        coupon = LoyaltyCoupon(
            company_id=company_id,
            customer_id=data["customer_id"],
            reward_id=data.get("reward_id"),
            code=code,
            discount_type=data["discount_type"],
            discount_value=data["discount_value"],
            min_order_xof=data.get("min_order_xof", 0),
            expires_at=data.get("expires_at"),
        )
        self.db.add(coupon)
        await self.db.flush()
        await self.db.refresh(coupon)
        return coupon

    async def get_by_code(self, company_id: UUID, code: str) -> LoyaltyCoupon:
        result = await self.db.execute(
            select(LoyaltyCoupon).where(
                LoyaltyCoupon.company_id == company_id,
                LoyaltyCoupon.code == code,
            )
        )
        coupon = result.scalar_one_or_none()
        if not coupon:
            raise NotFoundError("Coupon")
        return coupon

    async def list_for_customer(self, company_id: UUID, customer_id: UUID) -> list[LoyaltyCoupon]:
        result = await self.db.execute(
            select(LoyaltyCoupon)
            .where(
                LoyaltyCoupon.company_id == company_id,
                LoyaltyCoupon.customer_id == customer_id,
            )
            .order_by(LoyaltyCoupon.created_at.desc())
        )
        return list(result.scalars().all())

    async def apply(self, company_id: UUID, code: str, order_id: UUID) -> LoyaltyCoupon:
        coupon = await self.get_by_code(company_id, code)
        if coupon.is_used:
            raise BadRequestError("Ce coupon a déjà été utilisé", "coupon_already_used")
        now = datetime.now(timezone.utc)
        if coupon.expires_at and coupon.expires_at < now:
            raise BadRequestError("Ce coupon a expiré", "coupon_expired")
        coupon.is_used = True
        coupon.used_at = now
        coupon.order_id = order_id
        await self.db.flush()
        await self.db.refresh(coupon)
        return coupon


class CustomerIntelligenceService:
    """Calcule et persiste les scores RFM des clients d'une entreprise."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _recency_score(self, days_since_last_order: int) -> int:
        if days_since_last_order <= 7:
            return 5
        if days_since_last_order <= 30:
            return 4
        if days_since_last_order <= 60:
            return 3
        if days_since_last_order <= 120:
            return 2
        return 1

    def _frequency_score(self, orders_count: int) -> int:
        if orders_count >= 12:
            return 5
        if orders_count >= 8:
            return 4
        if orders_count >= 5:
            return 3
        if orders_count >= 2:
            return 2
        return 1

    def _monetary_score(self, total_spent_xof: int) -> int:
        if total_spent_xof >= 250_000:
            return 5
        if total_spent_xof >= 100_000:
            return 4
        if total_spent_xof >= 50_000:
            return 3
        if total_spent_xof >= 20_000:
            return 2
        return 1

    def _segment(self, days_since_last_order: int, orders_count: int, rfm_score: int) -> str:
        if orders_count <= 1 and days_since_last_order <= 30:
            return "new"
        if rfm_score >= 13:
            return "vip"
        if rfm_score >= 10:
            return "loyal"
        if days_since_last_order <= 45:
            return "active"
        if days_since_last_order <= 120:
            return "at_risk"
        return "inactive"

    async def recompute_company_scores(self, company_id: UUID) -> dict:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(
                Payment.customer_id,
                func.count(Payment.id).label("orders_count"),
                func.coalesce(func.sum(Payment.amount_xof), 0).label("total_spent_xof"),
                func.max(Payment.confirmed_at).label("last_order_date"),
                User.first_name,
                User.last_name,
            )
            .join(Order, Order.id == Payment.order_id)
            .join(User, User.id == Payment.customer_id)
            .where(
                Order.company_id == company_id,
                Payment.status == "confirmed",
                Payment.confirmed_at.is_not(None),
            )
            .group_by(Payment.customer_id, User.first_name, User.last_name)
        )

        computed = 0
        for row in result.all():
            last_order_date = row.last_order_date or now
            days_since_last_order = max(0, (now - last_order_date).days)
            recency_score = self._recency_score(days_since_last_order)
            frequency_score = self._frequency_score(int(row.orders_count or 0))
            monetary_score = self._monetary_score(int(row.total_spent_xof or 0))
            rfm_score = recency_score + frequency_score + monetary_score
            segment = self._segment(days_since_last_order, int(row.orders_count or 0), rfm_score)

            existing = await self.db.execute(
                select(CustomerScore).where(
                    CustomerScore.company_id == company_id,
                    CustomerScore.customer_id == row.customer_id,
                )
            )
            score = existing.scalar_one_or_none()
            if not score:
                score = CustomerScore(company_id=company_id, customer_id=row.customer_id)
                self.db.add(score)

            score.recency_score = recency_score
            score.frequency_score = frequency_score
            score.monetary_score = monetary_score
            score.rfm_score = rfm_score
            score.segment = segment
            score.last_order_date = last_order_date
            score.order_count = int(row.orders_count or 0)
            score.total_spent_xof = int(row.total_spent_xof or 0)
            score.computed_at = now
            computed += 1

        await self.db.flush()
        return {
            "company_id": str(company_id),
            "computed_customers": computed,
            "computed_at": now.isoformat(),
        }

    async def get_by_segment(
        self,
        company_id: UUID,
        segment: Optional[str] = None,
        limit: int = 50,
    ) -> list[CustomerScore]:
        q = select(CustomerScore).where(CustomerScore.company_id == company_id)
        if segment:
            q = q.where(CustomerScore.segment == segment)
        q = q.order_by(CustomerScore.rfm_score.desc()).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_customer_profile(self, company_id: UUID, customer_id: UUID) -> dict:
        user = await self.db.get(User, customer_id)
        if not user:
            raise NotFoundError("Client")

        score_result = await self.db.execute(
            select(CustomerScore).where(
                CustomerScore.company_id == company_id,
                CustomerScore.customer_id == customer_id,
            )
        )
        score = score_result.scalar_one_or_none()

        cards_result = await self.db.execute(
            select(LoyaltyCard)
            .where(
                LoyaltyCard.company_id == company_id,
                LoyaltyCard.customer_id == customer_id,
            )
            .order_by(LoyaltyCard.issued_at.desc())
        )
        cards = list(cards_result.scalars().all())

        return {
            "customer_id": customer_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": getattr(user, "phone", None),
            "score": score,
            "cards": cards,
            "total_spent_xof": score.total_spent_xof if score else 0,
            "order_count": score.order_count if score else 0,
            "segment": score.segment if score else None,
        }
