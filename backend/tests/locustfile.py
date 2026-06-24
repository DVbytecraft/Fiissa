"""
Test de charge Fiissa / SmartCheckout — Locust
===============================================
Scenarios couverts :
  - Parcours client complet  (poids 4) : auth -> panier -> commande -> paiement
  - Resolution barcode         (poids 3) : GET /catalog/products/barcode/{barcode}
  - Tableau de bord marchand   (poids 2) : GET /reports/dashboard
  - Liste commandes marchand   (poids 1) : GET /orders/merchant/list

Utilisation :
  locust -f tests/locustfile.py --host http://localhost:8000 \
         --headless -u 100 -r 10 -t 120s \
         --csv reports/load_100users

  # 100 users  : -u 100  -r 10  -t 120s
  # 500 users  : -u 500  -r 50  -t 180s
  # 1000 users : -u 1000 -r 100 -t 300s

Variables d'environnement :
  FIISSA_BASE_URL   (override --host)
  FIISSA_COMPANY_ID (UUID entreprise de test)
  FIISSA_STORE_ID   (UUID magasin de test)
  FIISSA_PRODUCT_BARCODE
  FIISSA_MGR_TOKEN  (JWT manager pre-genere)
"""

import os
import uuid
import random
import string
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner

# ─────────────────────────────────────────────────────────────────────────────
# Configuration depuis variables d'environnement
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL = os.getenv("FIISSA_BASE_URL", "http://localhost:8000")
COMPANY_ID = os.getenv("FIISSA_COMPANY_ID", "")
STORE_ID = os.getenv("FIISSA_STORE_ID", "")
PRODUCT_BARCODE = os.getenv("FIISSA_PRODUCT_BARCODE", "1234567890123")
MGR_TOKEN = os.getenv("FIISSA_MGR_TOKEN", "")

# Tolerance : ces erreurs sont acceptees pendant la charge (limite de debit etc.)
EXPECTED_ERROR_CODES = {429, 503}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _random_phone() -> str:
    suffix = "".join(random.choices(string.digits, k=7))
    return f"+2217{suffix}"


def _random_ref() -> str:
    return f"WAVE-{uuid.uuid4().hex[:12].upper()}"


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# Utilisateur : Client — flux complet
# ─────────────────────────────────────────────────────────────────────────────

class CustomerUser(HttpUser):
    """
    Simule un client UEMOA : inscription -> OTP -> panier -> commande -> paiement.
    Poids 4 : scenario le plus frequent.
    """
    weight = 4
    wait_time = between(1, 3)

    def on_start(self):
        """Inscription + verification OTP une seule fois par virtual user."""
        self.token = None
        self._register_and_login()

    def _register_and_login(self):
        phone = _random_phone()
        # 1. Inscription (email obligatoire depuis Sprint 1)
        email = f"load_{phone[1:]}@load-test.fiissa.com"
        r = self.client.post(
            "/api/v1/auth/register",
            json={"phone": phone, "email": email, "first_name": "Load", "last_name": "Test"},
            name="/auth/register",
        )
        if r.status_code != 200:
            return
        debug_code = r.json().get("debug_code")
        if not debug_code:
            return

        # 2. Verification OTP
        r2 = self.client.post(
            "/api/v1/auth/login/verify-otp",
            json={"phone": phone, "code": debug_code},
            name="/auth/login/verify-otp",
        )
        if r2.status_code == 200:
            self.token = r2.json().get("access_token")

    @task(3)
    def full_purchase_flow(self):
        """Panier -> Commande -> Paiement."""
        if not self.token or not STORE_ID or not COMPANY_ID:
            return

        hdrs = _bearer(self.token)

        # Panier
        r = self.client.post(
            f"/api/v1/orders/cart/items?store_id={STORE_ID}&company_id={COMPANY_ID}",
            json={"barcode": PRODUCT_BARCODE, "quantity": 1},
            headers=hdrs,
            name="/orders/cart/items",
        )
        if r.status_code not in (200,) | EXPECTED_ERROR_CODES:
            return

        # Commande
        r2 = self.client.post(
            "/api/v1/orders/",
            json={
                "store_id": STORE_ID,
                "company_id": COMPANY_ID,
                "order_type": "click_collect",
            },
            headers=hdrs,
            name="/orders/ [create]",
        )
        if r2.status_code != 200:
            return
        order_id = r2.json().get("id")

        # Paiement
        r3 = self.client.post(
            "/api/v1/payments/",
            json={"order_id": order_id, "operator": "wave"},
            headers=hdrs,
            name="/payments/ [create]",
        )
        if r3.status_code != 200:
            return
        payment_id = r3.json().get("id")

        # Soumission preuve
        self.client.post(
            f"/api/v1/payments/{payment_id}/submit-proof",
            json={"transaction_ref": _random_ref(), "sender_phone": "+221771234567"},
            headers=hdrs,
            name="/payments/{id}/submit-proof",
        )

    @task(2)
    def scan_barcode(self):
        """Resolution barcode sans commande."""
        if not self.token or not STORE_ID or not COMPANY_ID:
            return
        self.client.get(
            f"/api/v1/catalog/products/barcode/{PRODUCT_BARCODE}"
            f"?store_id={STORE_ID}&company_id={COMPANY_ID}",
            headers=_bearer(self.token),
            name="/catalog/products/barcode/{barcode}",
        )

    @task(1)
    def view_my_orders(self):
        """Client consulte ses commandes."""
        if not self.token:
            return
        self.client.get(
            "/api/v1/orders/my",
            headers=_bearer(self.token),
            name="/orders/my",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Utilisateur : Manager — tableau de bord + confirmations
# ─────────────────────────────────────────────────────────────────────────────

class MerchantUser(HttpUser):
    """
    Simule un gerant de magasin : tableau de bord, liste commandes, paiements en attente.
    Poids 1 : moins frequent que le client.
    """
    weight = 1
    wait_time = between(2, 5)

    def on_start(self):
        self.token = MGR_TOKEN
        self.mgr_headers = _bearer(self.token) if self.token else {}
        if self.token and COMPANY_ID:
            self.mgr_headers["X-Company-ID"] = COMPANY_ID

    @task(3)
    def dashboard(self):
        """Tableau de bord en temps reel."""
        if not self.mgr_headers:
            return
        self.client.get(
            "/api/v1/reports/dashboard",
            headers=self.mgr_headers,
            name="/reports/dashboard",
        )

    @task(2)
    def list_orders(self):
        """Liste des commandes du magasin."""
        if not self.mgr_headers:
            return
        self.client.get(
            "/api/v1/orders/merchant/list",
            headers=self.mgr_headers,
            name="/orders/merchant/list",
        )

    @task(2)
    def pending_payments(self):
        """Paiements en attente de confirmation."""
        if not self.mgr_headers:
            return
        self.client.get(
            "/api/v1/payments/pending",
            headers=self.mgr_headers,
            name="/payments/pending",
        )

    @task(1)
    def summary_report(self):
        """Rapport mensuel."""
        if not self.mgr_headers:
            return
        self.client.get(
            "/api/v1/reports/summary?period=month",
            headers=self.mgr_headers,
            name="/reports/summary",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Hook : affichage de statistiques cibles en fin de test
# ─────────────────────────────────────────────────────────────────────────────

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats
    total = stats.total

    print("\n" + "=" * 60)
    print("RAPPORT DE CHARGE — Fiissa SmartCheckout")
    print("=" * 60)
    print(f"  Requetes total   : {total.num_requests}")
    print(f"  Echecs           : {total.num_failures}")
    print(f"  Taux d'erreur    : {100 * total.fail_ratio:.1f}%")
    print(f"  p50 (median)     : {total.get_response_time_percentile(0.50):.0f} ms")
    print(f"  p95              : {total.get_response_time_percentile(0.95):.0f} ms")
    print(f"  p99              : {total.get_response_time_percentile(0.99):.0f} ms")
    print(f"  RPS moyen        : {total.current_rps:.1f} req/s")
    print("=" * 60)

    # Seuils de certification
    p95 = total.get_response_time_percentile(0.95)
    error_rate = total.fail_ratio * 100
    pass_p95 = p95 < 2000
    pass_err = error_rate < 1.0

    print(f"  [{'OK' if pass_p95 else 'FAIL'}] p95 < 2000ms  : {p95:.0f}ms")
    print(f"  [{'OK' if pass_err else 'FAIL'}] erreurs < 1%  : {error_rate:.2f}%")
    overall = "PASSE" if (pass_p95 and pass_err) else "ECHEC"
    print(f"  => CERTIFICATION CHARGE : {overall}")
    print("=" * 60)
