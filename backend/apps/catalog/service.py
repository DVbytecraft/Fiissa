from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.catalog.models import (
    CatalogImportError,
    CatalogImportJob,
    CatalogSource,
    Category,
    Product,
    ProductHistory,
)
from apps.companies.models import CompanySetting
from apps.integrations.models import (
    ApiCallLog,
    ApiCredential,
    ApiIntegration,
    ExternalProductCache,
)
from core.exceptions import BadRequestError, InsufficientStock, NotFoundError
from core.secrets import decrypt_secret, encrypt_secret, mask_secret


REQUIRED_IMPORT_COLUMNS = {
    "barcode",
    "name",
    "price_xof",
    "stock_quantity",
    "category",
    "unit",
    "is_available",
}


class CatalogResolutionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_product_by_barcode(
        self, company_id: UUID, store_id: Optional[UUID], barcode: str
    ) -> dict[str, Any]:
        source = await self._get_catalog_source(company_id, store_id)
        mode = source.mode

        if mode == "internal":
            return await self._resolve_internal_product(company_id, barcode)
        if mode == "csv_import":
            return await self._resolve_csv_product(company_id, barcode)
        if mode == "external_api":
            return await self._resolve_external_product(company_id, barcode)
        if mode == "hybrid":
            try:
                return await self._resolve_external_product(company_id, barcode)
            except Exception as exc:
                await self._log_external_failure(company_id, source, barcode, str(exc))
                try:
                    return await self._resolve_internal_product(company_id, barcode)
                except NotFoundError:
                    raise NotFoundError("Produit")

        raise BadRequestError("Mode catalogue non supporte")

    async def get_or_create_catalog_source(
        self, company_id: UUID, store_id: Optional[UUID] = None
    ) -> CatalogSource:
        result = await self.db.execute(
            select(CatalogSource).where(
                CatalogSource.company_id == company_id,
                CatalogSource.store_id == store_id,
            )
        )
        source = result.scalar_one_or_none()
        if source:
            return source

        source = CatalogSource(company_id=company_id, store_id=store_id, mode="internal")
        self.db.add(source)
        await self.db.flush()
        return source

    async def import_csv_catalog(
        self,
        *,
        company_id: UUID,
        store_id: Optional[UUID],
        created_by_id: UUID,
        file_name: str,
        content: bytes,
    ) -> CatalogImportJob:
        job = CatalogImportJob(
            company_id=company_id,
            store_id=store_id,
            created_by_id=created_by_id,
            file_name=file_name,
            status="processing",
            source_format="csv",
        )
        self.db.add(job)
        await self.db.flush()

        decoded = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))
        headers = set(reader.fieldnames or [])
        missing_columns = sorted(REQUIRED_IMPORT_COLUMNS - headers)
        if missing_columns:
            job.status = "failed"
            job.error_count = len(missing_columns)
            job.error_report = "\n".join(f"Missing column: {col}" for col in missing_columns)
            for idx, column in enumerate(missing_columns, start=1):
                self.db.add(
                    CatalogImportError(
                        job_id=job.id,
                        row_number=0,
                        field_name=column,
                        message=f"Colonne obligatoire manquante: {column}",
                    )
                )
            raise BadRequestError("Colonnes obligatoires manquantes", code="invalid_import_columns")

        rows = list(reader)
        job.total_rows = len(rows)
        errors_csv: list[str] = []

        for row_number, row in enumerate(rows, start=2):
            try:
                normalized = self._normalize_import_row(row)
                category = await self._get_or_create_category(company_id, store_id, normalized["category"])
                product = await self._find_existing_import_product(
                    company_id, normalized["barcode"], normalized.get("sku")
                )
                if product:
                    old_data = {
                        "price_xof": product.price_xof,
                        "stock_quantity": product.stock_quantity,
                        "is_available": product.is_available,
                    }
                    product.name = normalized["name"]
                    product.description = normalized.get("description")
                    product.brand = normalized.get("brand")
                    product.origin_country = normalized.get("origin_country")
                    product.price_xof = normalized["price_xof"]
                    product.compare_price_xof = normalized.get("compare_price_xof")
                    product.tax_rate = normalized.get("tax_rate")
                    product.stock_quantity = normalized["stock_quantity"]
                    product.category_id = category.id if category else None
                    product.unit = normalized["unit"]
                    product.weight_g = normalized.get("weight_g")
                    product.volume_ml = normalized.get("volume_ml")
                    product.is_available = normalized["is_available"]
                    product.tags = normalized.get("tags") or []
                    product.attributes = normalized.get("attributes") or {}
                    product.store_id = store_id
                    product.source_type = "csv_import"
                    if normalized.get("sku"):
                        product.sku = normalized["sku"]
                    self.db.add(
                        ProductHistory(
                            company_id=company_id,
                            product_id=product.id,
                            changed_by_id=created_by_id,
                            change_type="metadata",
                            old_data=old_data,
                            new_data=normalized,
                        )
                    )
                    job.updated_count += 1
                else:
                    product = Product(
                        company_id=company_id,
                        store_id=store_id,
                        category_id=category.id if category else None,
                        name=normalized["name"],
                        description=normalized.get("description"),
                        brand=normalized.get("brand"),
                        origin_country=normalized.get("origin_country"),
                        barcode=normalized["barcode"],
                        sku=normalized.get("sku"),
                        unit=normalized["unit"],
                        weight_g=normalized.get("weight_g"),
                        volume_ml=normalized.get("volume_ml"),
                        price_xof=normalized["price_xof"],
                        compare_price_xof=normalized.get("compare_price_xof"),
                        tax_rate=normalized.get("tax_rate"),
                        stock_quantity=normalized["stock_quantity"],
                        track_stock=True,
                        is_available=normalized["is_available"],
                        tags=normalized.get("tags") or [],
                        attributes=normalized.get("attributes") or {},
                        source_type="csv_import",
                    )
                    self.db.add(product)
                    await self.db.flush()
                    self.db.add(
                        ProductHistory(
                            company_id=company_id,
                            product_id=product.id,
                            changed_by_id=created_by_id,
                            change_type="metadata",
                            new_data=normalized,
                        )
                    )
                    job.created_count += 1
            except Exception as exc:
                job.error_count += 1
                self.db.add(
                    CatalogImportError(
                        job_id=job.id,
                        row_number=row_number,
                        message=str(exc),
                        raw_row=row,
                    )
                )
                errors_csv.append(f"{row_number},{str(exc)}")

        job.status = "completed" if job.error_count == 0 else "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.error_report = "row,error\n" + "\n".join(errors_csv) if errors_csv else None

        source = await self.get_or_create_catalog_source(company_id, store_id)
        if source.mode == "internal":
            source.mode = "csv_import"

        return job

    async def upsert_api_integration(
        self,
        *,
        company_id: UUID,
        store_id: Optional[UUID],
        mode: str,
        endpoint_url: str,
        http_method: str,
        api_key: Optional[str],
        api_secret: Optional[str],
        headers: Optional[dict],
        response_mapping: Optional[dict],
        timeout_seconds: int,
        cache_ttl_seconds: int,
        fallback_to_internal: bool,
    ) -> ApiIntegration:
        result = await self.db.execute(
            select(ApiIntegration).where(ApiIntegration.company_id == company_id)
        )
        integration = result.scalar_one_or_none()
        if not integration:
            integration = ApiIntegration(
                company_id=company_id,
                name="catalog_api",
                integration_type="catalog",
                endpoint_url=endpoint_url,
            )
            self.db.add(integration)
            await self.db.flush()

        integration.endpoint_url = endpoint_url
        integration.http_method = http_method
        integration.request_headers = headers
        integration.response_mapping = response_mapping
        integration.timeout_seconds = timeout_seconds
        integration.cache_ttl_seconds = cache_ttl_seconds
        integration.fallback_to_internal = fallback_to_internal
        integration.is_active = True
        integration.status = "active"

        if api_key:
            await self._upsert_credential(integration.id, "api_key", "X-API-Key", api_key)
        if api_secret:
            await self._upsert_credential(integration.id, "bearer", "Authorization", api_secret)

        source = await self.get_or_create_catalog_source(company_id, store_id)
        source.mode = mode
        source.config = {
            "endpoint_url": endpoint_url,
            "http_method": http_method,
            "timeout_seconds": timeout_seconds,
            "cache_ttl_seconds": cache_ttl_seconds,
            "fallback_to_internal": fallback_to_internal,
        }

        result = await self.db.execute(
            select(CompanySetting).where(CompanySetting.company_id == company_id)
        )
        setting = result.scalar_one_or_none()
        if not setting:
            setting = CompanySetting(company_id=company_id, catalog_mode=mode)
            self.db.add(setting)
        else:
            setting.catalog_mode = mode

        return integration

    async def get_catalog_configuration(
        self, company_id: UUID, store_id: Optional[UUID]
    ) -> dict[str, Any]:
        source = await self._get_catalog_source(company_id, store_id)
        integration_result = await self.db.execute(
            select(ApiIntegration).where(
                ApiIntegration.company_id == company_id,
                ApiIntegration.integration_type == "catalog",
            )
        )
        integration = integration_result.scalar_one_or_none()
        credentials: list[ApiCredential] = []
        if integration:
            credentials = (
                await self.db.execute(
                    select(ApiCredential).where(ApiCredential.integration_id == integration.id)
                )
            ).scalars().all()

        masked_credentials = {cred.credential_type: cred.masked_preview for cred in credentials}
        return {
            "mode": source.mode,
            "store_id": str(source.store_id) if source.store_id else None,
            "config": source.config or {},
            "integration": {
                "id": str(integration.id) if integration else None,
                "endpoint_url": integration.endpoint_url if integration else None,
                "http_method": integration.http_method if integration else "GET",
                "headers": integration.request_headers if integration else None,
                "response_mapping": integration.response_mapping if integration else None,
                "timeout_seconds": integration.timeout_seconds if integration else 10,
                "cache_ttl_seconds": integration.cache_ttl_seconds if integration else 300,
                "fallback_to_internal": integration.fallback_to_internal if integration else True,
                "masked_credentials": masked_credentials,
                "is_active": integration.is_active if integration else False,
            },
        }

    async def update_catalog_mode(
        self, company_id: UUID, store_id: Optional[UUID], mode: str
    ) -> CatalogSource:
        source = await self.get_or_create_catalog_source(company_id, store_id)
        source.mode = mode

        result = await self.db.execute(
            select(CompanySetting).where(CompanySetting.company_id == company_id)
        )
        setting = result.scalar_one_or_none()
        if not setting:
            setting = CompanySetting(company_id=company_id, catalog_mode=mode)
            self.db.add(setting)
        else:
            setting.catalog_mode = mode

        return source

    async def sync_products_from_api(
        self,
        company_id: UUID,
        products: list[dict],
        replace_all: bool = False,
    ) -> dict:
        """
        Synchronise des produits poussés par le système externe du marchand via sa clé API Fiissa.
        source_type = "external_sync". Si replace_all=True, supprime les produits non inclus dans le batch.
        """
        from sqlalchemy import update as sa_update

        created = updated = errors = 0

        if replace_all:
            await self.db.execute(
                sa_update(Product)
                .where(
                    Product.company_id == company_id,
                    Product.source_type == "external_sync",
                    Product.is_deleted.is_(False),
                )
                .values(is_deleted=True)
            )

        for item in products:
            try:
                barcode = str(item.get("barcode", "")).strip()
                name = str(item.get("name", "")).strip()
                if not barcode or not name:
                    errors += 1
                    continue
                price_xof = item.get("price_xof")
                if price_xof is None:
                    errors += 1
                    continue

                result = await self.db.execute(
                    select(Product).where(
                        Product.company_id == company_id,
                        Product.barcode == barcode,
                        Product.is_deleted.is_(False),
                    )
                )
                product = result.scalar_one_or_none()

                category = None
                if item.get("category"):
                    category = await self._get_or_create_category(company_id, None, item["category"])

                stock_qty = item.get("stock_quantity")

                if product:
                    product.name = name
                    product.price_xof = int(price_xof)
                    product.compare_price_xof = item.get("compare_price_xof")
                    product.weight_g = item.get("weight_g")
                    product.volume_ml = item.get("volume_ml")
                    product.image_url = item.get("image_url")
                    product.images = item.get("images") or []
                    product.description = item.get("description")
                    product.brand = item.get("brand")
                    product.unit = item.get("unit") or "pièce"
                    product.stock_quantity = int(stock_qty) if stock_qty is not None else product.stock_quantity
                    product.track_stock = stock_qty is not None
                    product.is_available = item.get("is_available", True)
                    product.attributes = item.get("attributes") or {}
                    product.tags = item.get("tags") or []
                    if item.get("sku"):
                        product.sku = item["sku"]
                    if category:
                        product.category_id = category.id
                    product.source_type = "external_sync"
                    product.is_deleted = False
                    updated += 1
                else:
                    product = Product(
                        company_id=company_id,
                        name=name,
                        barcode=barcode,
                        sku=item.get("sku"),
                        price_xof=int(price_xof),
                        compare_price_xof=item.get("compare_price_xof"),
                        weight_g=item.get("weight_g"),
                        volume_ml=item.get("volume_ml"),
                        image_url=item.get("image_url"),
                        images=item.get("images") or [],
                        description=item.get("description"),
                        brand=item.get("brand"),
                        unit=item.get("unit") or "pièce",
                        stock_quantity=int(stock_qty) if stock_qty is not None else 0,
                        track_stock=stock_qty is not None,
                        is_available=item.get("is_available", True),
                        attributes=item.get("attributes") or {},
                        tags=item.get("tags") or [],
                        category_id=category.id if category else None,
                        source_type="external_sync",
                    )
                    self.db.add(product)
                    await self.db.flush()
                    created += 1
            except Exception:
                errors += 1

        return {"created": created, "updated": updated, "errors": errors, "total": created + updated + errors}

    async def list_products_via_api_key(
        self,
        company_id: UUID,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """
        Liste les produits via clé API Fiissa.
        - Mode external_api/hybrid : Fiissa appelle l'ERP du marchand en temps réel et retourne sa réponse.
        - Mode internal/csv_import/external_sync : retourne les produits stockés dans Fiissa.
        """
        from sqlalchemy import func as sa_func, or_ as sa_or

        source = await self._get_catalog_source(company_id, None)

        if source.mode in ("external_api", "hybrid"):
            return await self._list_external_products_live(company_id, search, page, page_size)

        query = select(Product).where(
            Product.company_id == company_id,
            Product.is_available,
            Product.is_deleted.is_(False),
        )
        if search:
            query = query.where(
                sa_or(Product.name.ilike(f"%{search}%"), Product.barcode == search)
            )

        count_result = await self.db.execute(select(sa_func.count()).select_from(query.subquery()))
        total = count_result.scalar() or 0

        result = await self.db.execute(
            query.order_by(Product.name.asc()).offset((page - 1) * page_size).limit(page_size)
        )
        products = result.scalars().all()

        return {
            "items": [self._serialize_product(p, source=p.source_type) for p in products],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def _list_external_products_live(
        self,
        company_id: UUID,
        search: Optional[str],
        page: int,
        page_size: int,
    ) -> dict:
        """Appelle l'API ERP du marchand pour lister ses produits en temps réel."""
        result = await self.db.execute(
            select(ApiIntegration).where(
                ApiIntegration.company_id == company_id,
                ApiIntegration.integration_type == "catalog",
                ApiIntegration.is_active,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

        headers = dict(integration.request_headers or {})
        credentials = (
            await self.db.execute(
                select(ApiCredential).where(
                    ApiCredential.integration_id == integration.id,
                    ApiCredential.is_active,
                )
            )
        ).scalars().all()
        for cred in credentials:
            decrypted = decrypt_secret(cred.encrypted_secret)
            if cred.credential_type == "api_key":
                headers[cred.key_name or "X-API-Key"] = decrypted
            elif cred.credential_type == "bearer":
                headers[cred.key_name or "Authorization"] = f"Bearer {decrypted}"

        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if search:
            params["search"] = search

        try:
            async with httpx.AsyncClient(timeout=integration.timeout_seconds) as client:
                response = await client.get(integration.endpoint_url, params=params, headers=headers)

            if response.status_code >= 400:
                return {"items": [], "total": 0, "page": page, "page_size": page_size}

            raw = self._safe_json(response)
            mapping = integration.response_mapping or {}

            items_raw: Any = raw
            if isinstance(raw, dict):
                for key in ("items", "data", "products", "results"):
                    if key in raw and isinstance(raw[key], list):
                        items_raw = raw[key]
                        break

            if not isinstance(items_raw, list):
                return {"items": [], "total": 0, "page": page, "page_size": page_size}

            items = []
            for item in items_raw:
                try:
                    normalized = self._normalize_external_payload(item, mapping)
                    items.append(normalized)
                except Exception:
                    pass

            total = raw.get("total", len(items)) if isinstance(raw, dict) else len(items)
            return {"items": items, "total": total, "page": page, "page_size": page_size}

        except httpx.RequestError:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

    async def _upsert_credential(
        self, integration_id: UUID, credential_type: str, key_name: str, raw_secret: str
    ) -> ApiCredential:
        result = await self.db.execute(
            select(ApiCredential).where(
                ApiCredential.integration_id == integration_id,
                ApiCredential.credential_type == credential_type,
            )
        )
        credential = result.scalar_one_or_none()
        if not credential:
            credential = ApiCredential(
                integration_id=integration_id,
                credential_type=credential_type,
                key_name=key_name,
                encrypted_secret=encrypt_secret(raw_secret),
                masked_preview=mask_secret(raw_secret),
            )
            self.db.add(credential)
        else:
            credential.key_name = key_name
            credential.encrypted_secret = encrypt_secret(raw_secret)
            credential.masked_preview = mask_secret(raw_secret)
            credential.is_active = True
        return credential

    async def _get_catalog_source(self, company_id: UUID, store_id: Optional[UUID]) -> CatalogSource:
        result = await self.db.execute(
            select(CatalogSource)
            .where(CatalogSource.company_id == company_id, CatalogSource.store_id == store_id)
        )
        source = result.scalar_one_or_none()
        if source:
            return source

        if store_id is not None:
            result = await self.db.execute(
                select(CatalogSource)
                .where(CatalogSource.company_id == company_id, CatalogSource.store_id.is_(None))
            )
            source = result.scalar_one_or_none()
            if source:
                return source

        result = await self.db.execute(
            select(CompanySetting).where(CompanySetting.company_id == company_id)
        )
        setting = result.scalar_one_or_none()
        mode = setting.catalog_mode if setting else "internal"
        source = CatalogSource(company_id=company_id, store_id=store_id, mode=mode)
        self.db.add(source)
        await self.db.flush()
        return source

    async def _resolve_internal_product(self, company_id: UUID, barcode: str) -> dict[str, Any]:
        result = await self.db.execute(
            select(Product).where(
                Product.company_id == company_id,
                Product.barcode == barcode,
                Product.is_deleted.is_(False),
            )
        )
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundError("Produit")
        if product.price_xof is None:
            raise BadRequestError("Prix indisponible", code="missing_price")
        if product.track_stock and product.stock_available <= 0:
            raise InsufficientStock(product.name, product.stock_available)
        return self._serialize_product(product, source="internal")

    async def _resolve_csv_product(self, company_id: UUID, barcode: str) -> dict[str, Any]:
        result = await self.db.execute(
            select(Product).where(
                Product.company_id == company_id,
                Product.barcode == barcode,
                Product.is_deleted.is_(False),
                Product.source_type == "csv_import",
            )
        )
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundError("Produit")
        if product.price_xof is None:
            raise BadRequestError("Prix indisponible", code="missing_price")
        if product.track_stock and product.stock_available <= 0:
            raise InsufficientStock(product.name, product.stock_available)
        return self._serialize_product(product, source="csv_import")

    async def _resolve_external_product(self, company_id: UUID, barcode: str) -> dict[str, Any]:
        cached = await self._get_cached_external_product(company_id, barcode)
        if cached:
            return cached

        result = await self.db.execute(
            select(ApiIntegration).where(
                ApiIntegration.company_id == company_id,
                ApiIntegration.integration_type == "catalog",
                ApiIntegration.is_active,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise NotFoundError("Integration API")

        started = datetime.now(timezone.utc)
        headers = dict(integration.request_headers or {})
        credentials = (
            await self.db.execute(
                select(ApiCredential).where(
                    ApiCredential.integration_id == integration.id,
                    ApiCredential.is_active,
                )
            )
        ).scalars().all()
        for credential in credentials:
            decrypted = decrypt_secret(credential.encrypted_secret)
            if credential.credential_type == "api_key":
                headers[credential.key_name or "X-API-Key"] = decrypted
            elif credential.credential_type == "bearer":
                headers[credential.key_name or "Authorization"] = f"Bearer {decrypted}"

        try:
            async with httpx.AsyncClient(timeout=integration.timeout_seconds) as client:
                if integration.http_method == "POST":
                    response = await client.post(
                        integration.endpoint_url,
                        json={"barcode": barcode, "company_id": str(company_id)},
                        headers=headers,
                    )
                else:
                    response = await client.get(
                        integration.endpoint_url,
                        params={"barcode": barcode, "company_id": str(company_id)},
                        headers=headers,
                    )
        except httpx.TimeoutException as exc:
            await self._create_api_log(
                company_id=company_id,
                integration=integration,
                barcode=barcode,
                error_message="timeout",
                duration_ms=self._duration_ms(started),
            )
            raise BadRequestError("Timeout API externe", code="external_api_timeout") from exc

        if response.status_code in (401, 403):
            await self._create_api_log(
                company_id=company_id,
                integration=integration,
                barcode=barcode,
                http_status=response.status_code,
                response_payload=self._safe_json(response),
                duration_ms=self._duration_ms(started),
            )
            raise BadRequestError("Cle API invalide", code="invalid_api_key")

        if response.status_code >= 400:
            await self._create_api_log(
                company_id=company_id,
                integration=integration,
                barcode=barcode,
                http_status=response.status_code,
                response_payload=self._safe_json(response),
                duration_ms=self._duration_ms(started),
            )
            raise NotFoundError("Produit")

        raw_payload = self._safe_json(response)
        normalized = self._normalize_external_payload(
            raw_payload, integration.response_mapping or {}
        )
        await self._create_api_log(
            company_id=company_id,
            integration=integration,
            barcode=barcode,
            http_status=response.status_code,
            response_payload=raw_payload,
            duration_ms=self._duration_ms(started),
        )
        await self._cache_external_product(company_id, integration, barcode, normalized)
        await self.db.flush()
        return normalized

    def _normalize_external_payload(self, payload: Any, mapping: dict[str, Any]) -> dict[str, Any]:
        def read(path: Optional[str], default: Any = None) -> Any:
            if not path:
                return default
            current = payload
            for part in path.split("."):
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return default
            return current

        normalized = {
            "id": read(mapping.get("id"), read("id")),
            "name": read(mapping.get("name"), read("name")),
            "description": read(mapping.get("description"), read("description")),
            "brand": read(mapping.get("brand"), read("brand")),
            "origin_country": read(mapping.get("origin_country"), read("origin_country")),
            "barcode": read(mapping.get("barcode"), read("barcode")),
            "sku": read(mapping.get("sku"), read("sku")),
            "unit": read(mapping.get("unit"), read("unit", "pièce")),
            "weight_g": read(mapping.get("weight_g"), read("weight_g")),
            "volume_ml": read(mapping.get("volume_ml"), read("volume_ml")),
            "price_xof": read(mapping.get("price_xof"), read("price_xof")),
            "compare_price_xof": read(mapping.get("compare_price_xof"), read("compare_price_xof")),
            "tax_rate": read(mapping.get("tax_rate"), read("tax_rate")),
            "image_url": read(mapping.get("image_url"), read("image_url")),
            "images": read(mapping.get("images"), read("images", [])),
            "attributes": read(mapping.get("attributes"), read("attributes", {})),
            "tags": read(mapping.get("tags"), read("tags", [])),
            "stock_available": read(mapping.get("stock_available"), read("stock_quantity")),
            "is_available": read(mapping.get("is_available"), read("is_available", True)),
            "source": "external_api",
        }
        if not normalized["name"]:
            raise BadRequestError("Produit introuvable", code="product_not_found")
        if normalized["price_xof"] in (None, ""):
            raise BadRequestError("Prix indisponible", code="missing_price")
        if normalized["stock_available"] is None:
            raise BadRequestError("Stock indisponible", code="missing_stock")
        if int(normalized["stock_available"]) <= 0:
            raise BadRequestError("Stock insuffisant", code="insufficient_stock_external")
        return normalized

    async def _find_existing_import_product(
        self, company_id: UUID, barcode: str, sku: Optional[str]
    ) -> Optional[Product]:
        conditions = [Product.barcode == barcode]
        if sku:
            conditions.append(Product.sku == sku)
        result = await self.db.execute(
            select(Product).where(
                Product.company_id == company_id,
                Product.is_deleted.is_(False),
                or_(*conditions),
            )
        )
        return result.scalar_one_or_none()

    def _normalize_import_row(self, row: dict[str, Any]) -> dict[str, Any]:
        barcode = (row.get("barcode") or "").strip()
        if not barcode:
            raise BadRequestError("barcode requis", code="invalid_import_row")
        name = (row.get("name") or "").strip()
        if not name:
            raise BadRequestError("name requis", code="invalid_import_row")
        try:
            price_xof = int(row.get("price_xof") or 0)
        except Exception as exc:
            raise BadRequestError("price_xof invalide", code="invalid_import_row") from exc
        try:
            stock_quantity = int(row.get("stock_quantity") or 0)
        except Exception as exc:
            raise BadRequestError("stock_quantity invalide", code="invalid_import_row") from exc
        is_available = str(row.get("is_available", "true")).strip().lower() in {"1", "true", "yes", "oui"}

        def _opt_int(key: str) -> Optional[int]:
            v = row.get(key)
            if v in (None, ""):
                return None
            try:
                return int(v)
            except (ValueError, TypeError):
                return None

        import json as _json

        def _opt_json(key: str, default: Any) -> Any:
            v = row.get(key)
            if not v:
                return default
            if isinstance(v, (list, dict)):
                return v
            try:
                return _json.loads(v)
            except Exception:
                return default

        return {
            "barcode": barcode,
            "name": name,
            "description": (row.get("description") or "").strip() or None,
            "brand": (row.get("brand") or "").strip() or None,
            "origin_country": (row.get("origin_country") or "").strip() or None,
            "price_xof": price_xof,
            "compare_price_xof": _opt_int("compare_price_xof"),
            "tax_rate": _opt_int("tax_rate"),
            "stock_quantity": stock_quantity,
            "category": (row.get("category") or "Sans categorie").strip(),
            "unit": (row.get("unit") or "pièce").strip(),
            "weight_g": _opt_int("weight_g"),
            "volume_ml": _opt_int("volume_ml"),
            "is_available": is_available,
            "sku": (row.get("sku") or "").strip() or None,
            "tags": _opt_json("tags", []),
            "attributes": _opt_json("attributes", {}),
        }

    async def _get_or_create_category(
        self, company_id: UUID, store_id: Optional[UUID], name: str
    ) -> Optional[Category]:
        if not name:
            return None
        slug = name.lower().strip().replace(" ", "-")
        result = await self.db.execute(
            select(Category).where(Category.company_id == company_id, Category.slug == slug)
        )
        category = result.scalar_one_or_none()
        if category:
            return category
        category = Category(company_id=company_id, store_id=store_id, name=name, slug=slug)
        self.db.add(category)
        await self.db.flush()
        return category

    async def _create_api_log(
        self,
        *,
        company_id: UUID,
        integration: ApiIntegration,
        barcode: str,
        request_payload: Optional[dict] = None,
        response_payload: Optional[dict] = None,
        error_message: Optional[str] = None,
        http_status: Optional[int] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        log = ApiCallLog(
            company_id=company_id,
            integration_id=integration.id,
            barcode=barcode,
            request_payload=request_payload,
            response_payload=response_payload,
            error_message=error_message,
            http_status=http_status,
            duration_ms=duration_ms,
        )
        self.db.add(log)

    async def _cache_external_product(
        self, company_id: UUID, integration: ApiIntegration, barcode: str, normalized: dict[str, Any]
    ) -> None:
        result = await self.db.execute(
            select(ExternalProductCache).where(
                ExternalProductCache.company_id == company_id,
                ExternalProductCache.barcode == barcode,
            )
        )
        cache = result.scalar_one_or_none()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=integration.cache_ttl_seconds)
        if cache:
            cache.product_payload = normalized
            cache.expires_at = expires_at
            cache.integration_id = integration.id
        else:
            cache = ExternalProductCache(
                company_id=company_id,
                integration_id=integration.id,
                barcode=barcode,
                product_payload=normalized,
                expires_at=expires_at,
            )
            self.db.add(cache)

    async def _get_cached_external_product(self, company_id: UUID, barcode: str) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(ExternalProductCache).where(
                ExternalProductCache.company_id == company_id,
                ExternalProductCache.barcode == barcode,
                ExternalProductCache.expires_at > datetime.now(timezone.utc),
            )
        )
        cache = result.scalar_one_or_none()
        if not cache:
            return None
        return dict(cache.product_payload)

    async def _log_external_failure(
        self, company_id: UUID, source: CatalogSource, barcode: str, message: str
    ) -> None:
        result = await self.db.execute(
            select(ApiIntegration).where(ApiIntegration.company_id == company_id)
        )
        integration = result.scalar_one_or_none()
        if integration:
            await self._create_api_log(
                company_id=company_id,
                integration=integration,
                barcode=barcode,
                error_message=message,
            )

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
            return payload if isinstance(payload, dict) else {"data": payload}
        except Exception:
            return {"raw": response.text}

    @staticmethod
    def _duration_ms(started_at: datetime) -> int:
        return int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

    @staticmethod
    def _serialize_product(product: Product, source: str) -> dict[str, Any]:
        return {
            "id": str(product.id),
            "name": product.name,
            "description": product.description,
            "brand": product.brand,
            "origin_country": product.origin_country,
            "barcode": product.barcode,
            "sku": product.sku,
            "unit": product.unit,
            "weight_g": product.weight_g,
            "volume_ml": product.volume_ml,
            "dimensions": product.dimensions,
            "price_xof": product.price_xof,
            "compare_price_xof": product.compare_price_xof,
            "tax_rate": product.tax_rate,
            "image_url": product.image_url,
            "images": product.images or [],
            "attributes": product.attributes or {},
            "tags": product.tags or [],
            "min_order_qty": product.min_order_qty,
            "max_order_qty": product.max_order_qty,
            "is_available": product.is_available,
            "stock_available": product.stock_available if product.track_stock else None,
            "track_stock": product.track_stock,
            "source": source,
        }
