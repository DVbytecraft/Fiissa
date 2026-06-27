"""
PaymentGatewayService — Intégration multi-passerelles (PayGate, FedaPay).

Architecture :
- Chaque marchand lie son propre compte (Token chiffré en DB).
- Le client paie directement sur le compte du marchand via l'API.
- Le webhook entrant confirme le paiement automatiquement.
"""

import logging
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.integrations.models import ApiIntegration, ApiCredential
from apps.payments.models import Payment
from core.config import settings
from core.exceptions import BadRequestError
from core.secrets import decrypt_secret

logger = logging.getLogger(__name__)

PAYGATE_BASE_URL = "https://paygatego.tg/api/v1"
FEDAPAY_BASE_URL = "https://api.fedapay.com/v1" if not settings.FEDAPAY_SANDBOX else "https://sandbox-api.fedapay.com/v1"


async def _get_company_payment_integration(db: AsyncSession, company_id: UUID, provider: str = "paygate") -> tuple[ApiIntegration, dict]:
    """Récupère l'intégration de paiement active pour une entreprise (PayGate ou FedaPay)."""
    result = await db.execute(
        select(ApiIntegration)
        .where(
            ApiIntegration.company_id == company_id,
            ApiIntegration.integration_type == "payment",
            ApiIntegration.name == provider,
            ApiIntegration.is_active,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise BadRequestError(f"Le marchand n'a pas configuré son compte {provider.capitalize()}.")

    result = await db.execute(
        select(ApiCredential).where(
            ApiCredential.integration_id == integration.id,
            ApiCredential.is_active,
        )
    )
    creds = result.scalars().all()
    
    keys = {}
    for cred in creds:
        try:
            keys[cred.key_name] = decrypt_secret(cred.encrypted_secret)
        except Exception:
            logger.error(
                "Impossible de déchiffrer la clé '%s' pour l'intégration %s",
                cred.key_name,
                integration.id,
            )
            raise BadRequestError(
                "Configuration de paiement corrompue — contactez le support ou reconfigurez vos clés."
            )

    return integration, keys


class PaymentGatewayService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def initiate_payment(
        self,
        payment: Payment,
        customer_phone: str,
        provider: str = "paygate"
    ) -> dict:
        """Route vers la bonne passerelle."""
        if provider == "paygate":
            return await self._initiate_paygate(payment, customer_phone)
        elif provider == "fedapay":
            return await self._initiate_fedapay(payment, customer_phone)
        else:
            raise BadRequestError("Passerelle de paiement non supportée.")

    async def _initiate_paygate(self, payment: Payment, customer_phone: str) -> dict:
        """Initie une transaction sur PayGate Togo (USSD Push)."""
        _, keys = await _get_company_payment_integration(self.db, payment.company_id, "paygate")
        token = keys.get("token")
        if not token:
            raise BadRequestError("Token PayGate manquant ou invalide.")

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        identifier = f"FIISSA-{payment.payment_number}"

        payload = {
            "token": token,
            "amount": payment.amount_xof,
            "phone_number": customer_phone,
            "description": f"Paiement Fiissa {payment.payment_number}",
            "identifier": identifier,
        }

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(f"{PAYGATE_BASE_URL}/pay", data=payload, headers=headers)
            
            data = response.json()
            if data.get("status") != 0:
                error_msg = data.get("message", "Erreur inconnue PayGate")
                logger.error("PayGate API error: %s", error_msg)
                raise BadRequestError(f"Erreur PayGate: {error_msg}")

            tx_reference = data.get("tx_reference")
            payment.gateway_response = {"provider": "paygate", "tx_reference": tx_reference, "identifier": identifier}
            payment.transaction_ref = tx_reference

            return {
                "status": "success",
                "tx_reference": tx_reference,
                "message": "Demande de paiement envoyée. Veuillez valider sur votre téléphone.",
            }
        except httpx.RequestError as e:
            logger.error("PayGate request failed: %s", e)
            raise BadRequestError("Passerelle PayGate injoignable.")

    async def _initiate_fedapay(self, payment: Payment, customer_phone: str) -> dict:
        """Initie une transaction sur FedaPay (Redirection/Card/Mobile Money)."""
        _, keys = await _get_company_payment_integration(self.db, payment.company_id, "fedapay")
        api_key = keys.get("api_key")
        if not api_key:
            raise BadRequestError("Clé API FedaPay manquante ou invalide.")

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "description": f"Paiement Fiissa - {payment.payment_number}",
            "amount": payment.amount_xof,
            "currency": {"iso_code": "XOF"},
            "callback_url": f"{settings.APP_URL}/payment/{payment.order_id}/success",
            "customer": {"firstname": "Client", "lastname": "Fiissa", "phone_number": customer_phone, "email": "client@fiissa.app"},
            "metadata": {"payment_id": str(payment.id), "company_id": str(payment.company_id)},
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(f"{FEDAPAY_BASE_URL}/transactions", json=payload, headers=headers)

                if response.status_code not in (200, 201):
                    logger.error("FedaPay API error: %s %s", response.status_code, response.text)
                    raise BadRequestError("Erreur lors de l'initialisation du paiement FedaPay.")

                data = response.json().get("transaction", {})
                tx_id = data.get("id")
                tx_reference = data.get("reference")

                payment.gateway_response = {"provider": "fedapay", "transaction_id": tx_id, "reference": tx_reference}
                payment.transaction_ref = f"FEDAPAY-{tx_reference}"

                # Générer le token de paiement pour l'URL (client toujours ouvert)
                token_resp = await client.post(f"{FEDAPAY_BASE_URL}/transactions/{tx_id}/token", headers=headers)
                if token_resp.status_code not in (200, 201):
                    logger.error("FedaPay token error: %s %s", token_resp.status_code, token_resp.text)
                    raise BadRequestError("Impossible de générer le lien de paiement FedaPay.")
                token_data = token_resp.json().get("token", {})
                payment_url = token_data.get("url")
                if not payment_url:
                    raise BadRequestError("FedaPay n'a pas retourné d'URL de paiement.")

            return {
                "status": "success",
                "payment_url": payment_url,
                "reference": tx_reference,
                "message": "Redirection vers FedaPay...",
            }
        except httpx.RequestError as e:
            logger.error("FedaPay request failed: %s", e)
            raise BadRequestError("Passerelle FedaPay injoignable.")