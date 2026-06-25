"""
Fiissa FastAPI application entrypoint.
"""

from contextlib import asynccontextmanager

import sentry_sdk
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
from core.middleware import (
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    TenantIsolationMiddleware,
)
from core.rate_limit import limiter


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
    allow_headers=["Authorization", "Content-Type", "X-Company-ID", "X-Request-ID", "Accept"],
    expose_headers=["X-Request-ID", "X-Response-Time"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list or ["*"])
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
    if settings.DEBUG:
        import traceback
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "debug_error",
                "type": type(exc).__name__,
                "message": str(exc)[:500],
                "traceback": traceback.format_exc()[-2000:],
            },
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": "internal_error", "message": "Internal server error"},
    )


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


@app.get("/health", tags=["System"])
async def health_check(db: AsyncSession = Depends(get_db)):
    import redis as redis_lib

    # Vérification base de données
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    # Vérification Redis
    try:
        r = redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    overall = "ok" if db_ok and redis_ok else "degraded"
    return {
        "status": overall,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "db": "connected" if db_ok else "error",
        "redis": "connected" if redis_ok else "error",
    }


@app.get("/", tags=["System"])
async def root():
    return {"message": "Fiissa API", "docs": "/docs"}
