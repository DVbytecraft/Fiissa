"""
Reports router — Dashboard, résumé analytique, exports CSV / Excel / PDF.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from apps.companies.models import Company
from apps.reports.service import ReportService
from core.database import get_db
from core.dependencies import get_tenant_context, TenantContext, require_permission
from sqlalchemy import select

router = APIRouter(prefix="/reports", tags=["Rapports"])


@router.get("/dashboard", summary="KPIs du jour (dashboard marchand)")
async def get_dashboard_stats(
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("reports.read")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.get_dashboard(ctx.company_id)


@router.get("/summary", summary="Résumé statistiques par période")
async def get_summary(
    period: str = Query(default="month", description="today|week|month|year|custom"),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("reports.read")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.get_summary(ctx.company_id, period, date_from, date_to)


@router.get("/sales", summary="Ventes agrégées par jour")
async def get_sales_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("reports.read")),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    from sqlalchemy import func
    from apps.payments.models import Payment
    from apps.orders.models import Order

    start = datetime.combine(date_from, datetime.min.time()).replace(tzinfo=timezone.utc)
    end = datetime.combine(date_to, datetime.max.time()).replace(tzinfo=timezone.utc)

    result = await db.execute(
        select(
            func.date(Payment.confirmed_at).label("sale_date"),
            func.count(Payment.id).label("transactions"),
            func.coalesce(func.sum(Payment.amount_xof), 0).label("total_xof"),
        )
        .join(Order, Payment.order_id == Order.id)
        .where(
            Order.company_id == ctx.company_id,
            Payment.status == "confirmed",
            Payment.confirmed_at.between(start, end),
        )
        .group_by(func.date(Payment.confirmed_at))
        .order_by(func.date(Payment.confirmed_at).asc())
    )
    return [
        {"date": str(row.sale_date), "transactions": row.transactions, "total_xof": row.total_xof}
        for row in result.all()
    ]


@router.get("/export/csv", summary="Export CSV des commandes")
async def export_csv(
    period: str = Query(default="month"),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("reports.export")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    content = await service.export_csv(ctx.company_id, period, date_from, date_to)
    filename = f"fiissa_rapport_{period}.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/excel", summary="Export Excel des commandes")
async def export_excel(
    period: str = Query(default="month"),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("reports.export")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    content = await service.export_excel(ctx.company_id, period, date_from, date_to)
    filename = f"fiissa_rapport_{period}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/pdf", summary="Export PDF des commandes")
async def export_pdf(
    period: str = Query(default="month"),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("reports.export")),
    db: AsyncSession = Depends(get_db),
):
    company_result = await db.execute(select(Company).where(Company.id == ctx.company_id))
    company = company_result.scalar_one_or_none()
    company_name = company.name if company else str(ctx.company_id)

    service = ReportService(db)
    content = await service.export_pdf(ctx.company_id, company_name, period, date_from, date_to)
    filename = f"fiissa_rapport_{period}.pdf"
    media_type = "application/pdf" if content[:4] == b"%PDF" else "text/html"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# Rétrocompatibilité export CSV (ancienne URL)
@router.get("/export/sales.csv", include_in_schema=False)
async def export_sales_csv_legacy(
    date_from: date = Query(...),
    date_to: date = Query(...),
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("reports.export")),
    db: AsyncSession = Depends(get_db),
):
    return await export_csv(period="custom", date_from=date_from, date_to=date_to, ctx=ctx, current_user=current_user, db=db)
