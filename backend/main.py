"""
Fiissa FastAPI application entrypoint.
"""

from contextlib import asynccontextmanager
from typing import Optional
import logging
import asyncio

import sentry_sdk
import redis as redis_lib
from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.trustedhost import TrustedHostMiddleware

from core.config import settings
from core.database import get_db
from core.exceptions import SmartCheckoutException
from core.middleware import(
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    TenantIsolationMiddleware,
)
from core.rate_limit import limiter

# Routers
from apps.auth.router import router as auth_router
from apps.users.router import router as users_router
from apps.companies.router import router as companies_router
from apps.stores.router import router as stores_router
from apps.catalog.router import router as catalog_router
from apps.orders.router import router as orders_router
from apps.payments.router import router as payments_router
from apps.receipts.router import router as receipts_router
from apps.notifications.router import router as notifications_router
from apps.reports.router import router as reports_router
from apps.superadmin.router import router as superadmin_router
from apps.support.router import router as support_router
from apps.integrations.router import router as integrations_router
from apps.loyalty.router import router as loyalty_router
from apps.wallet.router import router as wallet_router
from apps.promotions.router import router as promotions_router
from workers.celery_app import celery_app
from core.storage import StorageService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle hooks."""
    print(f"[Fiissa] Startup in {settings.ENVIRONMENT} mode")

    if settings.SENTRY_DSN and settings.is_production:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            release=settings.APP_VERSION,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        )

    if settings.is_production:
        await StorageService.ensure_ready(create_missing=True)

    yield

    print("[Fiissa] Shutdown")


app = FastAPI(
    title="Fiissa API",
    description="Multi-tenant commerce API for UEMOA retailers.",
    version=settings.APP_VERSION,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys([settings.APP_URL, *settings.cors_origins_list])),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Company-ID", "X-Request-ID", "Idempotency-Key", "Accept"],
    expose_headers=["X-Request-ID", "X-Response-Time"],
)
allowed_hosts = settings.allowed_hosts_list
if not allowed_hosts:
    if settings.is_production:
        raise RuntimeError("ALLOWED_HOSTS must be set in production")
    allowed_hosts = ["*"]

app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TenantIsolationMiddleware)
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(SmartCheckoutException)
async def business_exception_handler(request: Request, exc: SmartCheckoutException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail), "code": "error"}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": detail.get("code", "error"),
            "message": detail.get("message", str(exc.detail)),
        },
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"code": "rate_limit_exceeded", "message": "Too many requests. Please retry later."},
        headers={"Retry-After": "60"},
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": "validation_error", "message": "Invalid payload", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": "internal_error", "message": "Internal server error"},
    )


API_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(companies_router, prefix=API_PREFIX)
app.include_router(stores_router, prefix=API_PREFIX)
app.include_router(catalog_router, prefix=API_PREFIX)
app.include_router(orders_router, prefix=API_PREFIX)
app.include_router(payments_router, prefix=API_PREFIX)
app.include_router(receipts_router, prefix=API_PREFIX)
app.include_router(notifications_router, prefix=API_PREFIX)
app.include_router(reports_router, prefix=API_PREFIX)
app.include_router(superadmin_router, prefix=API_PREFIX)
app.include_router(support_router, prefix=API_PREFIX)
app.include_router(integrations_router, prefix=API_PREFIX)
app.include_router(loyalty_router, prefix=API_PREFIX)
app.include_router(wallet_router, prefix=API_PREFIX)
app.include_router(promotions_router, prefix=API_PREFIX)


def _build_redis_client() -> Optional[redis_lib.Redis]:
    if not settings.REDIS_URL.startswith(("redis://", "rediss://", "unix://")):
        return None
    return redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=2)


redis_client = _build_redis_client()


async def _check_storage() -> bool:
    try:
        await StorageService.ensure_ready(create_missing=False)
        return True
    except Exception:
        return False


async def _check_celery_workers() -> bool:
    try:
        response = await asyncio.to_thread(lambda: celery_app.control.inspect(timeout=1).ping())
        return bool(response)
    except Exception:
        return False

@app.get("/health", tags=["System"])
async def health_check(db: AsyncSession = Depends(get_db)):
    # Vérification base de données
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    # Vérification Redis
    try:
        if redis_client is None:
            redis_ok = True
        else:
            redis_client.ping()
            redis_ok = True
    except Exception:
        redis_ok = False

    storage_ok = await _check_storage()
    celery_ok = await _check_celery_workers()

    overall = "ok" if db_ok and redis_ok and storage_ok and celery_ok else "degraded"
    return {
        "status": overall,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "db": "connected" if db_ok else "error",
        "redis": "connected" if redis_ok else "error",
        "storage": "connected" if storage_ok else "error",
        "celery": "connected" if celery_ok else "error",
    }



@app.get("/", tags=["System"])
async def root():
    return {"message": "Fiissa API", "docs": "/docs"}
