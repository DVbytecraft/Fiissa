from datetime import date, datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.orders.models import Order
from apps.payments.models import Payment
from apps.receipts.models import Receipt
from apps.receipts.service import ReceiptService
from core.database import get_db
from core.dependencies import get_current_user, get_tenant_context, require_permission
from core.exceptions import NotFoundError, TenantAccessDenied

router = APIRouter(prefix="/receipts", tags=["Reçus"])


async def _get_receipt_with_access(
    receipt_id: UUID,
    current_user,
    db: AsyncSession,
) -> Receipt:
    result = await db.execute(
        select(Receipt)
        .options(
            selectinload(Receipt.order).selectinload(Order.items),
            selectinload(Receipt.store),
        )
        .where(Receipt.id == receipt_id)
    )
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise NotFoundError("Reçu")

    if receipt.customer_id == current_user.id:
        return receipt

    from apps.users.models import UserCompanyRole

    role_result = await db.execute(
        select(UserCompanyRole).where(
            UserCompanyRole.user_id == current_user.id,
            UserCompanyRole.company_id == receipt.company_id,
            UserCompanyRole.is_active == True,
        )
    )
    role = role_result.scalar_one_or_none()
    if not role:
        raise TenantAccessDenied()
    return receipt


def _serialize_receipt(receipt: Receipt) -> dict:
    return {
        "id": str(receipt.id),
        "receipt_number": receipt.receipt_number,
        "verification_code": receipt.verification_code,
        "amount_xof": receipt.amount_xof,
        "total_xof": receipt.amount_xof,
        "issued_at": receipt.issued_at.isoformat(),
        "created_at": receipt.issued_at.isoformat(),
        "pdf_url": receipt.pdf_url,
        "html_content": receipt.html_content,
        "store_name": receipt.store.name if receipt.store else None,
        "order_id": str(receipt.order_id),
        "order_number": receipt.order.order_number if receipt.order else None,
        "is_verified": receipt.is_verified,
    }


@router.get("/verify/{verification_code}")
async def verify_receipt_public(
    verification_code: str,
    db: AsyncSession = Depends(get_db),
):
    service = ReceiptService(db)
    return await service.verify_receipt(verification_code)


@router.get("/merchant")
async def get_merchant_receipts(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("receipts.read")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Receipt)
        .options(selectinload(Receipt.order), selectinload(Receipt.store))
        .where(Receipt.company_id == tenant.company_id)
        .order_by(Receipt.issued_at.desc())
    )
    if date_from:
        stmt = stmt.where(Receipt.issued_at >= date_from)
    if date_to:
        stmt = stmt.where(Receipt.issued_at < datetime.combine(date_to, datetime.max.time()))
    if search:
        stmt = stmt.where(Receipt.receipt_number.ilike(f"%{search}%"))

    receipts_result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    receipts = receipts_result.scalars().all()

    return {
        "items": [_serialize_receipt(receipt) for receipt in receipts],
        "page": page,
        "page_size": page_size,
    }


@router.get("/my")
async def get_my_receipts(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Receipt)
        .options(selectinload(Receipt.order), selectinload(Receipt.store))
        .where(Receipt.customer_id == current_user.id)
        .order_by(Receipt.issued_at.desc())
    )
    receipts = result.scalars().all()
    return [_serialize_receipt(receipt) for receipt in receipts]


@router.get("/order/{order_id}")
async def get_receipt_by_order(
    order_id: UUID,
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("receipts.read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Receipt)
        .options(selectinload(Receipt.order), selectinload(Receipt.store))
        .where(Receipt.order_id == order_id, Receipt.company_id == tenant.company_id)
    )
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise NotFoundError("Reçu")
    return _serialize_receipt(receipt)


@router.post("/generate/{payment_id}")
async def generate_receipt(
    payment_id: UUID,
    tenant=Depends(get_tenant_context),
    current_user=Depends(require_permission("receipts.generate")),
    db: AsyncSession = Depends(get_db),
):
    payment_result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = payment_result.scalar_one_or_none()
    if not payment:
        raise NotFoundError("Paiement")
    if payment.company_id != tenant.company_id:
        raise TenantAccessDenied()

    service = ReceiptService(db)
    receipt = await service.generate_receipt(payment_id)
    return _serialize_receipt(receipt)


@router.get("/{receipt_id}")
async def get_receipt(
    receipt_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    receipt = await _get_receipt_with_access(receipt_id, current_user, db)
    return _serialize_receipt(receipt)


@router.get("/{receipt_id}/html")
async def get_receipt_html(
    receipt_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    receipt = await _get_receipt_with_access(receipt_id, current_user, db)
    return Response(content=receipt.html_content, media_type="text/html")


@router.get("/{receipt_id}/qr")
async def get_receipt_qr(
    receipt_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    receipt = await _get_receipt_with_access(receipt_id, current_user, db)
    return {
        "receipt_id": str(receipt.id),
        "verification_code": receipt.verification_code,
        "verification_url": f"/api/v1/receipts/verify/{receipt.verification_code}",
    }
