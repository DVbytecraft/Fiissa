"""Routes Loyalty Engine — Sprint 2"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.loyalty.schemas import (
    CardTemplateResponse,
    CouponResponse,
    CreateCardTemplateRequest,
    CreateProgramRequest,
    CreateRewardRequest,
    CreateTierRequest,
    CustomerProfileResponse,
    CustomerScoreResponse,
    EarnPointsRequest,
    ImportExternalCardRequest,
    IssueCouponRequest,
    IssueNativeCardRequest,
    LoyaltyCardResponse,
    LoyaltyTransactionResponse,
    ProgramResponse,
    RedeemPointsRequest,
    RewardResponse,
    TierResponse,
    UpdateProgramRequest,
)
from sqlalchemy import select
from apps.loyalty.service import (
    CardTemplateService,
    CustomerIntelligenceService,
    LoyaltyCardService,
    LoyaltyCouponService,
    LoyaltyProgramService,
    LoyaltyRewardService,
    LoyaltyTierService,
    LoyaltyTransactionService,
)
from apps.orders.models import Order as OrderModel
from core.database import get_db
from core.dependencies import require_permission
from core.exceptions import NotFoundError, TenantAccessDenied

router = APIRouter(prefix="/loyalty", tags=["Fidélité"])


# ── Programmes ─────────────────────────────────────────────────────────────────

@router.post("/programs", response_model=ProgramResponse)
async def create_program(
    data: CreateProgramRequest,
    current_user=Depends(require_permission("loyalty.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Crée un programme fidélité. loyalty_enabled=False par défaut."""
    company_id = current_user._active_company_id
    service = LoyaltyProgramService(db)
    return await service.create(company_id, data.model_dump())


@router.get("/programs", response_model=list[ProgramResponse])
async def list_programs(
    current_user=Depends(require_permission("loyalty.read")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = LoyaltyProgramService(db)
    return await service.list(company_id)


@router.get("/programs/{program_id}", response_model=ProgramResponse)
async def get_program(
    program_id: UUID,
    current_user=Depends(require_permission("loyalty.read")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = LoyaltyProgramService(db)
    return await service.get(company_id, program_id)


@router.patch("/programs/{program_id}", response_model=ProgramResponse)
async def update_program(
    program_id: UUID,
    data: UpdateProgramRequest,
    current_user=Depends(require_permission("loyalty.manage")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = LoyaltyProgramService(db)
    return await service.update(company_id, program_id, data.model_dump(exclude_none=True))


@router.post("/programs/{program_id}/activate", response_model=ProgramResponse)
async def activate_program(
    program_id: UUID,
    current_user=Depends(require_permission("loyalty.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Active le programme et positionne loyalty_enabled=True."""
    company_id = current_user._active_company_id
    service = LoyaltyProgramService(db)
    return await service.activate(company_id, program_id)


@router.post("/programs/{program_id}/deactivate", response_model=ProgramResponse)
async def deactivate_program(
    program_id: UUID,
    current_user=Depends(require_permission("loyalty.manage")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = LoyaltyProgramService(db)
    return await service.deactivate(company_id, program_id)


# ── Niveaux (tiers) ────────────────────────────────────────────────────────────

@router.post("/programs/{program_id}/tiers", response_model=TierResponse)
async def create_tier(
    program_id: UUID,
    data: CreateTierRequest,
    current_user=Depends(require_permission("loyalty.manage")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = LoyaltyTierService(db)
    return await service.create(company_id, program_id, data.model_dump())


@router.get("/programs/{program_id}/tiers", response_model=list[TierResponse])
async def list_tiers(
    program_id: UUID,
    current_user=Depends(require_permission("loyalty.read")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = LoyaltyTierService(db)
    return await service.list(company_id, program_id)


# ── Récompenses ────────────────────────────────────────────────────────────────

@router.post("/programs/{program_id}/rewards", response_model=RewardResponse)
async def create_reward(
    program_id: UUID,
    data: CreateRewardRequest,
    current_user=Depends(require_permission("loyalty.manage")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = LoyaltyRewardService(db)
    return await service.create(company_id, program_id, data.model_dump())


@router.get("/programs/{program_id}/rewards", response_model=list[RewardResponse])
async def list_rewards(
    program_id: UUID,
    current_user=Depends(require_permission("loyalty.rewards.read")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = LoyaltyRewardService(db)
    return await service.list(company_id, program_id)


# ── Templates de carte ─────────────────────────────────────────────────────────

@router.post("/card-templates", response_model=CardTemplateResponse)
async def create_card_template(
    data: CreateCardTemplateRequest,
    current_user=Depends(require_permission("loyalty.manage")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = CardTemplateService(db)
    return await service.create(company_id, data.model_dump())


@router.get("/card-templates", response_model=list[CardTemplateResponse])
async def list_card_templates(
    current_user=Depends(require_permission("loyalty.read")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = CardTemplateService(db)
    return await service.list(company_id)


# ── Cartes ─────────────────────────────────────────────────────────────────────

@router.get("/cards/scan/{card_number}", response_model=LoyaltyCardResponse)
async def scan_card(
    card_number: str,
    current_user=Depends(require_permission("loyalty.read_own")),
    db: AsyncSession = Depends(get_db),
):
    """
    Client scanne une carte physique (QR code ou numéro).
    Si la carte existe et n'est pas déjà liée à un compte, l'importe dans le compte du client.
    Si déjà liée, retourne la carte existante (anti-duplication).
    """
    service = LoyaltyCardService(db)
    return await service.import_by_scan(current_user.id, card_number)


@router.get("/card-for-company/{company_id}")
async def get_card_for_company(
    company_id: UUID,
    current_user=Depends(require_permission("loyalty.read_own")),
    db: AsyncSession = Depends(get_db),
):
    """
    Vérifie si le client a une carte de fidélité chez une entreprise spécifique.
    Retourne la carte avec les points, le tier, et le programme si actif.
    """
    service = LoyaltyCardService(db)
    return await service.get_card_for_company(current_user.id, company_id)


@router.post("/cards/issue", response_model=LoyaltyCardResponse)
async def issue_native_card(
    data: IssueNativeCardRequest,
    current_user=Depends(require_permission("loyalty.cards.issue")),
    db: AsyncSession = Depends(get_db),
):
    """Émet une carte native. Le programme DOIT être actif."""
    company_id = current_user._active_company_id
    service = LoyaltyCardService(db)
    return await service.issue_native(
        company_id, data.customer_id, data.program_id, data.card_template_id
    )


@router.post("/cards/import", response_model=LoyaltyCardResponse)
async def import_external_card(
    data: ImportExternalCardRequest,
    current_user=Depends(require_permission("loyalty.cards.issue")),
    db: AsyncSession = Depends(get_db),
):
    """Importe une carte fidélité externe."""
    company_id = current_user._active_company_id
    service = LoyaltyCardService(db)
    return await service.import_external(
        company_id,
        data.customer_id,
        data.external_issuer,
        data.external_ref,
        data.card_template_id,
    )


@router.get("/cards/mine", response_model=list[LoyaltyCardResponse])
async def my_cards(
    current_user=Depends(require_permission("loyalty.read_own")),
    db: AsyncSession = Depends(get_db),
):
    """Client : toutes ses cartes fidélité (toutes enseignes)."""
    service = LoyaltyCardService(db)
    return await service.list_own(current_user.id)


@router.get("/customers/{customer_id}/cards", response_model=list[LoyaltyCardResponse])
async def customer_cards(
    customer_id: UUID,
    current_user=Depends(require_permission("loyalty.cards.read")),
    db: AsyncSession = Depends(get_db),
):
    """Marchand : cartes d'un client pour son entreprise."""
    company_id = current_user._active_company_id
    service = LoyaltyCardService(db)
    return await service.list_for_customer(company_id, customer_id)


@router.get("/cards/{card_id}", response_model=LoyaltyCardResponse)
async def get_card(
    card_id: UUID,
    current_user=Depends(require_permission("loyalty.cards.read")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = LoyaltyCardService(db)
    return await service.get(company_id, card_id)


# ── Points ─────────────────────────────────────────────────────────────────────

@router.post("/cards/{card_id}/earn", response_model=LoyaltyTransactionResponse)
async def earn_points(
    card_id: UUID,
    data: EarnPointsRequest,
    current_user=Depends(require_permission("loyalty.cards.issue")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = LoyaltyTransactionService(db)
    return await service.earn(
        company_id, card_id, data.amount_xof, data.order_id, data.description
    )


@router.post("/cards/{card_id}/redeem", response_model=LoyaltyTransactionResponse)
async def redeem_points(
    card_id: UUID,
    data: RedeemPointsRequest,
    current_user=Depends(require_permission("loyalty.cards.issue")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = LoyaltyTransactionService(db)
    return await service.redeem(
        company_id, card_id, data.points, data.order_id, data.description
    )


@router.get("/cards/{card_id}/transactions", response_model=list[LoyaltyTransactionResponse])
async def card_transactions(
    card_id: UUID,
    current_user=Depends(require_permission("loyalty.cards.read")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = LoyaltyTransactionService(db)
    return await service.list_for_card(company_id, card_id)


# ── Coupons ────────────────────────────────────────────────────────────────────

@router.post("/coupons/issue", response_model=CouponResponse)
async def issue_coupon(
    data: IssueCouponRequest,
    current_user=Depends(require_permission("loyalty.coupons.issue")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = LoyaltyCouponService(db)
    return await service.issue(company_id, data.model_dump())


@router.get("/coupons/customer/{customer_id}", response_model=list[CouponResponse])
async def customer_coupons(
    customer_id: UUID,
    current_user=Depends(require_permission("loyalty.coupons.issue")),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_user._active_company_id
    service = LoyaltyCouponService(db)
    return await service.list_for_customer(company_id, customer_id)


@router.post("/coupons/{code}/apply", response_model=CouponResponse)
async def apply_coupon(
    code: str,
    order_id: UUID,
    current_user=Depends(require_permission("loyalty.coupons.issue")),
    db: AsyncSession = Depends(get_db),
):
    """
    Applique un coupon de fidélité côté marchand.
    La commande peut être déjà persistée ou simplement référencée par son UUID.
    """
    service = LoyaltyCouponService(db)
    return await service.apply(current_user._active_company_id, code, order_id)


# ── Intelligence clients (Sprint 5) ───────────────────────────────────────────

@router.get("/intelligence/customers", response_model=list[CustomerScoreResponse])
async def intelligence_customers(
    segment: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_permission("loyalty.read")),
    db: AsyncSession = Depends(get_db),
):
    """Segments RFM — liste les clients scorés par ordre de score décroissant."""
    company_id = current_user._active_company_id
    service = CustomerIntelligenceService(db)
    return await service.get_by_segment(company_id, segment, limit)


@router.post("/intelligence/recompute")
async def intelligence_recompute(
    current_user=Depends(require_permission("loyalty.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Recalcule immédiatement les scores RFM pour l'entreprise."""
    company_id = current_user._active_company_id
    service = CustomerIntelligenceService(db)
    result = await service.recompute_company_scores(company_id)
    await db.commit()
    return result


@router.get("/customers/{customer_id}/profile", response_model=CustomerProfileResponse)
async def get_customer_profile(
    customer_id: UUID,
    current_user=Depends(require_permission("loyalty.cards.read")),
    db: AsyncSession = Depends(get_db),
):
    """Profil enrichi d'un client : score RFM, cartes fidélité, stats achats."""
    company_id = current_user._active_company_id
    service = CustomerIntelligenceService(db)
    return await service.get_customer_profile(company_id, customer_id)
