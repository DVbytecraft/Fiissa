import httpx
import pytest

from apps.catalog.models import CatalogSource, Product
from apps.integrations.models import ApiCallLog, ApiCredential, ApiIntegration, ExternalProductCache
from core.secrets import encrypt_secret


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self.response = kwargs.pop("response", None)
        self.error = kwargs.pop("error", None)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *args, **kwargs):
        if self.error:
            raise self.error
        return self.response

    async def post(self, *args, **kwargs):
        if self.error:
            raise self.error
        return self.response


def make_client_factory(response=None, error=None):
    class _Client(FakeAsyncClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, response=response, error=error, **kwargs)

    return _Client


@pytest.mark.asyncio
async def test_barcode_resolution_internal_product(client, product, store):
    response = await client.get(f"/api/v1/catalog/products/barcode/{product.barcode}", params={"store_id": str(store.id)})

    assert response.status_code == 200
    assert response.json()["source"] == "internal"
    assert response.json()["name"] == product.name


@pytest.mark.asyncio
async def test_barcode_resolution_csv_import_product(client, db, manager, staff_headers, company, store):
    csv_content = (
        "barcode,name,price_xof,stock_quantity,category,unit,is_available\n"
        "9988776655443,Sucre fin,1200,14,Epicerie,sachet,true\n"
    )
    response = await client.post(
        f"/api/v1/catalog/products/import?store_id={store.id}",
        files={"file": ("catalog.csv", csv_content, "text/csv")},
        headers=staff_headers(manager, company.id),
    )

    assert response.status_code == 200
    assert response.json()["created_count"] == 1

    barcode_response = await client.get(
        "/api/v1/catalog/products/barcode/9988776655443",
        params={"store_id": str(store.id)},
    )
    assert barcode_response.status_code == 200
    assert barcode_response.json()["source"] == "csv_import"


@pytest.mark.asyncio
async def test_barcode_resolution_external_api_product(client, db, company, store, monkeypatch):
    db.add(CatalogSource(company_id=company.id, store_id=store.id, mode="external_api"))
    await db.flush()
    integration = ApiIntegration(
        company_id=company.id,
        integration_type="catalog",
        endpoint_url="https://catalog.example.test/products",
        http_method="GET",
        cache_ttl_seconds=120,
        timeout_seconds=5,
        is_active=True,
    )
    db.add(integration)
    await db.flush()
    db.add(
        ApiCredential(
            integration_id=integration.id,
            credential_type="api_key",
            key_name="X-API-Key",
            encrypted_secret=encrypt_secret("secret-key"),
            masked_preview="se***ey",
        )
    )
    await db.commit()

    monkeypatch.setattr(
        "apps.catalog.service.httpx.AsyncClient",
        make_client_factory(
            response=httpx.Response(
                200,
                json={
                    "barcode": "4455667788990",
                    "name": "Huile 1L",
                    "price_xof": 2500,
                    "stock_quantity": 7,
                    "unit": "bouteille",
                },
            )
        ),
    )

    response = await client.get(
        "/api/v1/catalog/products/barcode/4455667788990",
        params={"store_id": str(store.id)},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "external_api"
    assert response.json()["price_xof"] == 2500

    logs = (await db.execute(ApiCallLog.__table__.select())).all()
    cache_rows = (await db.execute(ExternalProductCache.__table__.select())).all()
    assert len(logs) == 1
    assert len(cache_rows) == 1


@pytest.mark.asyncio
async def test_barcode_resolution_hybrid_fallback_internal(client, db, company, store, product, monkeypatch):
    db.add(CatalogSource(company_id=company.id, store_id=store.id, mode="hybrid"))
    db.add(
        ApiIntegration(
            company_id=company.id,
            integration_type="catalog",
            endpoint_url="https://catalog.example.test/products",
            http_method="GET",
            cache_ttl_seconds=120,
            timeout_seconds=1,
            is_active=True,
        )
    )
    await db.commit()

    monkeypatch.setattr(
        "apps.catalog.service.httpx.AsyncClient",
        make_client_factory(error=httpx.TimeoutException("boom")),
    )

    response = await client.get(
        f"/api/v1/catalog/products/barcode/{product.barcode}",
        params={"store_id": str(store.id)},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "internal"

    log_count = (await db.execute(ApiCallLog.__table__.select())).all()
    assert len(log_count) >= 1


@pytest.mark.asyncio
async def test_barcode_resolution_product_not_found(client, store):
    response = await client.get(
        "/api/v1/catalog/products/barcode/0000000000000",
        params={"store_id": str(store.id)},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


@pytest.mark.asyncio
async def test_barcode_resolution_missing_price_external(client, db, company, store, monkeypatch):
    db.add(CatalogSource(company_id=company.id, store_id=store.id, mode="external_api"))
    db.add(
        ApiIntegration(
            company_id=company.id,
            integration_type="catalog",
            endpoint_url="https://catalog.example.test/products",
            http_method="GET",
            cache_ttl_seconds=120,
            timeout_seconds=5,
            is_active=True,
        )
    )
    await db.commit()

    monkeypatch.setattr(
        "apps.catalog.service.httpx.AsyncClient",
        make_client_factory(
            response=httpx.Response(
                200,
                json={"barcode": "111", "name": "Produit sans prix", "stock_quantity": 3},
            )
        ),
    )

    response = await client.get("/api/v1/catalog/products/barcode/111", params={"store_id": str(store.id)})

    assert response.status_code == 400
    assert response.json()["code"] == "missing_price"


@pytest.mark.asyncio
async def test_barcode_resolution_insufficient_stock_internal(client, db, product, store):
    product.stock_quantity = 0
    await db.commit()

    response = await client.get(
        f"/api/v1/catalog/products/barcode/{product.barcode}",
        params={"store_id": str(store.id)},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "insufficient_stock"


@pytest.mark.asyncio
async def test_barcode_resolution_invalid_api_key(client, db, company, store, monkeypatch):
    db.add(CatalogSource(company_id=company.id, store_id=store.id, mode="external_api"))
    db.add(
        ApiIntegration(
            company_id=company.id,
            integration_type="catalog",
            endpoint_url="https://catalog.example.test/products",
            http_method="GET",
            cache_ttl_seconds=120,
            timeout_seconds=5,
            is_active=True,
        )
    )
    await db.commit()

    monkeypatch.setattr(
        "apps.catalog.service.httpx.AsyncClient",
        make_client_factory(response=httpx.Response(401, json={"detail": "unauthorized"})),
    )

    response = await client.get("/api/v1/catalog/products/barcode/401401", params={"store_id": str(store.id)})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_api_key"


@pytest.mark.asyncio
async def test_barcode_resolution_external_timeout(client, db, company, store, monkeypatch):
    db.add(CatalogSource(company_id=company.id, store_id=store.id, mode="external_api"))
    db.add(
        ApiIntegration(
            company_id=company.id,
            integration_type="catalog",
            endpoint_url="https://catalog.example.test/products",
            http_method="GET",
            cache_ttl_seconds=120,
            timeout_seconds=1,
            is_active=True,
        )
    )
    await db.commit()

    monkeypatch.setattr(
        "apps.catalog.service.httpx.AsyncClient",
        make_client_factory(error=httpx.TimeoutException("timeout")),
    )

    response = await client.get("/api/v1/catalog/products/barcode/999111", params={"store_id": str(store.id)})

    assert response.status_code == 400
    assert response.json()["code"] == "external_api_timeout"


@pytest.mark.asyncio
async def test_barcode_resolution_invalid_response_mapping(client, db, company, store, monkeypatch):
    db.add(CatalogSource(company_id=company.id, store_id=store.id, mode="external_api"))
    db.add(
        ApiIntegration(
            company_id=company.id,
            integration_type="catalog",
            endpoint_url="https://catalog.example.test/products",
            http_method="GET",
            response_mapping={"name": "payload.title", "price_xof": "payload.amount"},
            cache_ttl_seconds=120,
            timeout_seconds=5,
            is_active=True,
        )
    )
    await db.commit()

    monkeypatch.setattr(
        "apps.catalog.service.httpx.AsyncClient",
        make_client_factory(response=httpx.Response(200, json={"payload": {"barcode": "778899"}})),
    )

    response = await client.get("/api/v1/catalog/products/barcode/778899", params={"store_id": str(store.id)})

    assert response.status_code == 400
    assert response.json()["code"] == "product_not_found"
