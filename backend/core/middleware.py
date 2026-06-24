import time
import uuid
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.request_context import clear_request_context, set_request_context

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log chaque requête avec durée et status."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start_time = time.perf_counter()
        set_request_context(
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_id=request_id,
        )

        try:
            response = await call_next(request)
        finally:
            clear_request_context()

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"→ {response.status_code} ({duration_ms}ms)"
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Ajoute des headers de sécurité HTTP."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=()"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        return response


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """
    Middleware de protection : vérifie que les endpoints /api/v1/companies/{id}/...
    ne sont pas accédés sans company_id dans la route ou le context.
    La vraie isolation se fait dans les dépendances FastAPI, ce middleware
    ajoute une couche de logging pour détecter les tentatives d'accès croisé.
    """

    AUDIT_PATHS = ["/api/v1/orders", "/api/v1/payments", "/api/v1/receipts"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if any(path.startswith(p) for p in self.AUDIT_PATHS):
            if not request.headers.get("authorization"):
                logger.warning(
                    f"Tentative d'accès non authentifié : {request.method} {path} "
                    f"from {request.client.host if request.client else 'unknown'}"
                )
        return await call_next(request)
