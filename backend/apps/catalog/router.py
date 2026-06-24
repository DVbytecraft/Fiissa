import os
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.catalog.models import Category, CatalogImportError, CatalogImportJob, Product, StockMovement
from apps.catalog.service import CatalogResolutionService
from apps.notifications.models import AuditLog
from apps.stores.models import Store
from core.database import get_db
from core.dependencies import TenantContext, get_tenant_context, require_permission
from core.exceptions import BadRequestError, NotFoundError
from core.pagination import PaginatedResponse


class ProductCreate(BaseModel):
    name: str
    category_id: Optional[UUID] = None
    description: Optional[str] = None
    barcode: Optional[str] = None
    sku: Optional[str] = None
    unit: str = "piece"
    price_xof: int
    compare_price_xof: Optional[int] = None
    is_available: bool = True
    track_stock: bool = False
    stock_quantity: int = 0
    stock_alert_qty: int = 5


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[UUID] = None
    price_xof: Optional[int] = None
    barcode: Optional[str] = None
    unit: Optional[str] = None
    is_available: Optional[bool] = None
    track_stock: Optional[bool] = None
    stock_quantity: Optional[int] = None
    stock_alert_qty: Optional[int] = None
    description: Optional[str] = None


class StockAdjustRequest(BaseModel):
    quantity_change: int
    notes: Optional[str] = None


router = APIRouter(prefix="/catalog", tags=["Catalogue"])


@router.get("/stores/{store_id}/categories")
async def get_categories(
    store_id: UUID,
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Category)
        .where(
            Category.company_id == company_id,
            Category.is_active == True,
        )
        .order_by(Category.position.asc(), Category.name.asc())
    )
    categories = result.scalars().all()
    return [
        {"id": str(category.id), "name": category.name, "slug": category.slug, "image_url": category.image_url}
        for category in categories
    ]


@router.get("/stores/{store_id}/products")
async def get_products(
    store_id: UUID,
    company_id: UUID = Query(...),
    category_id: Optional[UUID] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(
        Product.company_id == company_id,
        Product.is_available == True,
        Product.is_deleted == False,
    )

    if category_id:
        query = query.where(Product.category_id == category_id)

    if search:
        query = query.where(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.barcode == search,
            )
        )

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0
    result = await db.execute(
        query.order_by(Product.name.asc()).offset((page - 1) * page_size).limit(page_size)
    )
    products = result.scalars().all()

    return PaginatedResponse.create(
        items=[
            {
                "id": str(product.id),
                "name": product.name,
                "description": product.description,
                "barcode": product.barcode,
                "price_xof": product.price_xof,
                "compare_price_xof": product.compare_price_xof,
                "unit": product.unit,
                "image_url": product.image_url,
                "is_available": product.is_available,
                "stock_available": product.stock_available if product.track_stock else None,
            }
            for product in products
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/products/barcode/{barcode}")
async def find_by_barcode(
    barcode: str,
    company_id: Optional[UUID] = Query(default=None),
    store_id: Optional[UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not company_id and store_id:
        store_result = await db.execute(select(Store).where(Store.id == store_id))
        store = store_result.scalar_one_or_none()
        if not store:
            raise NotFoundError("Magasin")
        company_id = store.company_id

    if not company_id:
        raise BadRequestError("company_id ou store_id est requis")

    service = CatalogResolutionService(db)
    return await service.resolve_product_by_barcode(company_id, store_id, barcode)


@router.post("/products")
async def create_product(
    data: ProductCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("products.create")),
    db: AsyncSession = Depends(get_db),
):
    product = Product(
        company_id=ctx.company_id,
        source_type="internal",
        **data.model_dump(),
    )
    db.add(product)
    db.add(
        AuditLog(
            company_id=ctx.company_id,
            user_id=current_user.id,
            action="product.created",
            resource_type="product",
            new_data={"name": data.name, "price_xof": data.price_xof},
        )
    )
    await db.flush()
    return {"id": str(product.id), "name": product.name}


@router.patch("/products/{product_id}")
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("products.update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.company_id == ctx.company_id,
            Product.is_deleted == False,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError("Produit")

    old_data = {"name": product.name, "price_xof": product.price_xof}
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    db.add(
        AuditLog(
            company_id=ctx.company_id,
            user_id=current_user.id,
            action="product.updated",
            resource_type="product",
            resource_id=product.id,
            old_data=old_data,
            new_data=update_data,
        )
    )
    return {"id": str(product.id), "message": "Produit mis a jour"}


@router.post("/products/{product_id}/stock")
async def adjust_stock(
    product_id: UUID,
    data: StockAdjustRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("stock.update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.company_id == ctx.company_id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError("Produit")

    before = product.stock_quantity
    product.stock_quantity = max(0, product.stock_quantity + data.quantity_change)

    db.add(
        StockMovement(
            company_id=ctx.company_id,
            product_id=product.id,
            type="adjustment",
            quantity_change=data.quantity_change,
            quantity_before=before,
            quantity_after=product.stock_quantity,
            created_by_id=current_user.id,
            notes=data.notes,
        )
    )
    return {"product_id": str(product.id), "new_stock": product.stock_quantity}


@router.get("/categories", summary="Categories marchand")
async def get_merchant_categories(
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("products.read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Category)
        .where(Category.company_id == ctx.company_id)
        .order_by(Category.position.asc(), Category.name.asc())
    )
    categories = result.scalars().all()
    return {
        "items": [
            {"id": str(category.id), "name": category.name, "slug": category.slug, "is_active": category.is_active}
            for category in categories
        ]
    }


@router.get("/products", summary="Produits marchand")
async def get_merchant_products(
    search: Optional[str] = Query(default=None),
    category_id: Optional[UUID] = Query(default=None),
    stock_filter: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=40, le=100),
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("products.read")),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(
        Product.company_id == ctx.company_id,
        Product.is_deleted == False,
    )
    if search:
        query = query.where(
            or_(Product.name.ilike(f"%{search}%"), Product.barcode == search)
        )
    if category_id:
        query = query.where(Product.category_id == category_id)
    if stock_filter == "out":
        query = query.where(Product.track_stock == True, Product.stock_quantity == 0)
    elif stock_filter == "low":
        query = query.where(
            Product.track_stock == True,
            Product.stock_alert_qty.isnot(None),
            Product.stock_quantity <= Product.stock_alert_qty,
            Product.stock_quantity > 0,
        )

    count_q = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_q.scalar() or 0
    result = await db.execute(
        query.options(selectinload(Product.category)).order_by(Product.name.asc()).offset((page - 1) * page_size).limit(page_size)
    )
    products = result.scalars().all()

    return PaginatedResponse.create(
        items=[
            {
                "id": str(product.id),
                "name": product.name,
                "barcode": product.barcode,
                "price_xof": product.price_xof,
                "image_url": product.image_url,
                "category_id": str(product.category_id) if product.category_id else None,
                "category_name": product.category.name if product.category else None,
                "description": product.description,
                "unit": product.unit,
                "is_active": not product.is_deleted,
                "is_available": product.is_available,
                "track_stock": product.track_stock,
                "stock_quantity": product.stock_quantity,
                "stock_reserved": product.stock_reserved,
                "stock_available": product.stock_available if product.track_stock else None,
                "stock_alert_qty": product.stock_alert_qty,
                "source_type": product.source_type,
            }
            for product in products
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/products/{product_id}", summary="Supprimer un produit")
async def delete_product(
    product_id: UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("products.delete")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.company_id == ctx.company_id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError("Produit")

    product.is_deleted = True
    db.add(
        AuditLog(
            company_id=ctx.company_id,
            user_id=current_user.id,
            action="product.deleted",
            resource_type="product",
            resource_id=product.id,
            old_data={"name": product.name},
        )
    )
    return {"message": "Produit supprime"}


_MAX_CSV_SIZE = 5 * 1024 * 1024  # 5 Mo
_ALLOWED_MIME_TYPES = {"text/csv", "application/csv", "text/plain", "application/vnd.ms-excel"}
_ALLOWED_CSV_EXTENSIONS = {".csv"}


@router.post("/products/import", summary="Import CSV produits")
@router.post("/products/import-csv")
async def import_products_csv(
    file: UploadFile = File(...),
    store_id: Optional[UUID] = Query(default=None),
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("products.create")),
    db: AsyncSession = Depends(get_db),
):
    # Validation extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_CSV_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Extension invalide. Seuls les fichiers .csv sont acceptés.")

    # Validation MIME
    if file.content_type and file.content_type.split(";")[0].strip() not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier invalide: {file.content_type}. Utilisez un fichier CSV.",
        )

    # Lecture bornée — protection contre les fichiers volumineux
    content = await file.read(_MAX_CSV_SIZE + 1)
    if len(content) > _MAX_CSV_SIZE:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux. Taille maximum : 5 Mo.")

    service = CatalogResolutionService(db)
    job = await service.import_csv_catalog(
        company_id=ctx.company_id,
        store_id=store_id,
        created_by_id=current_user.id,
        file_name=file.filename or "catalog.csv",
        content=content,
    )
    return {
        "job_id": str(job.id),
        "status": job.status,
        "total_rows": job.total_rows,
        "created_count": job.created_count,
        "updated_count": job.updated_count,
        "error_count": job.error_count,
        "error_report": job.error_report,
    }


@router.get("/import-jobs", summary="Historique imports catalogue")
async def list_import_jobs(
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("products.read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CatalogImportJob)
        .where(CatalogImportJob.company_id == ctx.company_id)
        .order_by(CatalogImportJob.created_at.desc())
    )
    jobs = result.scalars().all()
    return {
        "items": [
            {
                "id": str(job.id),
                "file_name": job.file_name,
                "status": job.status,
                "total_rows": job.total_rows,
                "created_count": job.created_count,
                "updated_count": job.updated_count,
                "error_count": job.error_count,
                "error_report": job.error_report,
            }
            for job in jobs
        ]
    }


@router.get("/import-jobs/{job_id}/errors", summary="Erreurs import catalogue")
async def get_import_job_errors(
    job_id: UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user=Depends(require_permission("products.read")),
    db: AsyncSession = Depends(get_db),
):
    job_result = await db.execute(
        select(CatalogImportJob).where(
            CatalogImportJob.id == job_id,
            CatalogImportJob.company_id == ctx.company_id,
        )
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise NotFoundError("Import")

    error_result = await db.execute(
        select(CatalogImportError)
        .where(CatalogImportError.job_id == job.id)
        .order_by(CatalogImportError.row_number.asc())
    )
    errors = error_result.scalars().all()
    return {
        "job_id": str(job.id),
        "errors": [
            {
                "row_number": error.row_number,
                "field_name": error.field_name,
                "message": error.message,
                "raw_row": error.raw_row,
            }
            for error in errors
        ],
        "error_report": job.error_report,
    }
