from fastapi import HTTPException, status


class SmartCheckoutException(HTTPException):
    """Base exception pour SmartCheckout."""
    def __init__(self, status_code: int, detail: str, code: str = "error"):
        super().__init__(status_code=status_code, detail={"message": detail, "code": code})


# 400
class BadRequestError(SmartCheckoutException):
    def __init__(self, detail: str, code: str = "bad_request"):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail, code)


class ValidationError(SmartCheckoutException):
    def __init__(self, detail: str):
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, detail, "validation_error")


# 401
class AuthenticationError(SmartCheckoutException):
    def __init__(self, detail: str = "Non authentifié"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, "unauthenticated")


class InvalidCredentials(SmartCheckoutException):
    def __init__(self):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "Identifiants incorrects", "invalid_credentials")


class TokenExpired(SmartCheckoutException):
    def __init__(self):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "Session expirée, veuillez vous reconnecter", "token_expired")


class InvalidOTP(SmartCheckoutException):
    def __init__(self):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "Code incorrect ou expiré", "invalid_otp")

class AccountLocked(SmartCheckoutException):
    def __init__(self, retry_after_minutes: int = 15):
        super().__init__(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Compte verrouillé pour sécurité. Réessayez dans {retry_after_minutes} minutes.",
            "account_locked"
        )


# 403
class PermissionDenied(SmartCheckoutException):
    def __init__(self, detail: str = "Accès refusé"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail, "permission_denied")


class TenantAccessDenied(SmartCheckoutException):
    def __init__(self):
        super().__init__(status.HTTP_403_FORBIDDEN, "Accès refusé à cette ressource", "tenant_access_denied")


# 404
class NotFoundError(SmartCheckoutException):
    def __init__(self, resource: str = "Ressource"):
        super().__init__(status.HTTP_404_NOT_FOUND, f"{resource} introuvable", "not_found")


# 409
class ConflictError(SmartCheckoutException):
    def __init__(self, detail: str, code: str = "conflict"):
        super().__init__(status.HTTP_409_CONFLICT, detail, code)


class DuplicatePaymentRef(SmartCheckoutException):
    def __init__(self):
        super().__init__(
            status.HTTP_409_CONFLICT,
            "Cette référence de transaction a déjà été utilisée",
            "duplicate_payment_ref",
        )


class PaymentAlreadyConfirmed(SmartCheckoutException):
    def __init__(self):
        super().__init__(
            status.HTTP_409_CONFLICT,
            "Ce paiement a déjà été confirmé",
            "payment_already_confirmed",
        )


# 422 — Erreurs métier
class InsufficientStock(SmartCheckoutException):
    def __init__(self, product_name: str, available: int):
        super().__init__(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Stock insuffisant pour '{product_name}'. Disponible : {available}",
            "insufficient_stock",
        )


class ProductNotAvailable(SmartCheckoutException):
    def __init__(self, product_name: str):
        super().__init__(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Le produit '{product_name}' n'est pas disponible",
            "product_not_available",
        )


class OrderNotCancellable(SmartCheckoutException):
    def __init__(self, current_status: str):
        super().__init__(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Impossible d'annuler une commande en statut '{current_status}'",
            "order_not_cancellable",
        )


class InvalidOrderTransition(SmartCheckoutException):
    def __init__(self, from_status: str, to_status: str):
        super().__init__(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Transition interdite : {from_status} → {to_status}",
            "invalid_order_transition",
        )


class StoreInactive(SmartCheckoutException):
    def __init__(self):
        super().__init__(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Ce magasin n'est pas disponible actuellement",
            "store_inactive",
        )


class CompanySuspended(SmartCheckoutException):
    def __init__(self):
        super().__init__(
            status.HTTP_403_FORBIDDEN,
            "Ce commerce est suspendu",
            "company_suspended",
        )


# 429
class RateLimitExceeded(SmartCheckoutException):
    def __init__(self):
        super().__init__(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Trop de requêtes. Veuillez patienter.",
            "rate_limit_exceeded",
        )


# 500
class PDFGenerationError(SmartCheckoutException):
    def __init__(self):
        super().__init__(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Erreur lors de la génération du reçu PDF",
            "pdf_generation_error",
        )
