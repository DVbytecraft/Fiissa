# System Parity Audit

Date: 2026-06-24

## Verdict

Le systeme est maintenant tres proche d'un etat complet et coherent.

- Backend: large, migre et valide en runtime
- Frontend: surfaces coeur et surfaces avancees branchees
- Base de donnees: structure metier presente et migrations appliquees jusqu'a `0007`
- Workers async: runtime schema corrige et tache critique `cancel_expired_orders` validee
- Reste eventuel: finition visuelle continue et hygiene infra non bloquante

## Couverture Equilibree

### Auth / Identite

- Backend present:
  - register
  - login request OTP
  - login verify OTP
  - staff login
  - refresh / logout
  - forgot password / reset password
  - me / update me
  - verify email
  - staff list / invite / revoke
- Frontend visible:
  - login
  - register
  - forgot password
  - reset password
  - verify email
  - employees merchant
- Base:
  - users
  - otp_codes
  - refresh_tokens
  - email_verification_tokens
  - password_reset_tokens
- Statut:
  - presque aligne
- Ecart:
  - `authApi` n'expose pas encore `verify-email`
  - profil utilisateur encore partiellement branche

### Stores / Catalog / Orders / Payments

- Backend present:
  - stores, categories, products, barcode, stock, imports
  - cart, create order, scan-go, merchant orders, status updates
  - payment creation, proof submission, confirm, pending list
- Frontend visible:
  - customer home / store / scan / cart / order detail / payment
  - merchant products / orders / payments / dashboard
- Base:
  - stores
  - categories
  - products
  - stock_movements
  - carts
  - cart_items
  - orders
  - order_items
  - payments
- Statut:
  - bien aligne

### Receipts

- Backend present:
  - verify public
  - merchant receipts
  - my receipts
  - receipt by order
  - generate by payment
  - detail / html / qr
- Frontend visible:
  - customer receipts
  - merchant receipts
  - receipt verify
- Base:
  - receipts
- Statut:
  - partiellement aligne
- Ecart:
  - pas de branchement frontend pour:
    - `GET /receipts/order/{order_id}`
    - `POST /receipts/generate/{payment_id}`
    - `GET /receipts/{receipt_id}/qr`

### Reports

- Backend present:
  - dashboard
  - summary
  - sales
  - exports csv / excel / pdf
- Frontend visible:
  - merchant dashboard
  - merchant reports
- Base:
  - derivee de orders / payments / receipts
- Statut:
  - aligne sur le coeur

### Notifications

- Backend present:
  - list
  - summary
  - mark one read
  - mark all read
  - templates
  - events
- Frontend visible:
  - consommation implicite partielle seulement
- Base:
  - notifications
  - notification_templates
  - notification_events
- Statut:
  - non aligne completement
- Ecart:
  - `notificationsApi` ne couvre aujourd'hui que:
    - list
    - mark all read
  - manquent:
    - summary
    - mark one read
    - templates
    - events

### Support

- Backend present:
  - create ticket
  - list tickets
  - get ticket
  - reply
  - update
- Frontend visible:
  - customer support
  - merchant support
- Base:
  - support_tickets
  - support_messages
  - support_attachments
- Statut:
  - bien aligne sur les flux principaux

### Integrations / Webhooks

- Backend present:
  - list/create/update/delete webhooks
  - list deliveries
  - test webhook
- Frontend visible:
  - merchant integrations
- Base:
  - api_integrations
  - api_credentials
  - api_call_logs
  - external_product_cache
  - webhook_endpoints
  - webhook_deliveries
- Statut:
  - partiel
- Ecart:
  - le frontend ne couvre pas:
    - deliveries
    - test webhook

### Loyalty / Wallet / Customer Intelligence

- Backend present:
  - programs / tiers / rewards
  - card templates
  - issue/import cards
  - earn / redeem
  - coupons
  - RFM customer intelligence
  - wallet methods
- Frontend visible:
  - customer loyalty / coupons / rewards / wallet
  - merchant loyalty / coupons / customers
- Base:
  - loyalty_programs
  - loyalty_tiers
  - card_templates
  - loyalty_cards
  - loyalty_transactions
  - loyalty_rewards
  - loyalty_coupons
  - customer_scores
  - wallet_payment_methods
- Statut:
  - bien avance
- Ecart:
  - certaines fonctions merchant restent peu exposees ou peu profondes selon les pages

### Companies / Subscription / Settings

- Backend present:
  - company detail
  - settings
  - catalog config
  - feature flags
  - plans
  - subscription
  - change/cancel subscription
  - invoices
  - renewals
  - invoice pay
- Frontend visible:
  - merchant settings
  - merchant subscription
  - company detail superadmin
- Base:
  - companies
  - company_settings
  - feature_flags
  - plans
  - subscriptions
  - subscription_invoices
  - subscription_renewals
- Statut:
  - partiel
- Ecart:
  - `companiesApi` ne couvre pas:
    - feature flags
    - plans
    - pay invoice
    - create company

### Superadmin

- Backend present:
  - companies list
  - create plans
  - suspend / activate company
  - create staff
  - audit logs
  - stats
  - users
- Frontend visible:
  - companies
  - company detail
  - users
  - stats
- Base:
  - appuyee sur companies / users / audit_logs / plans / subscriptions
- Statut:
  - partiel
- Ecart:
  - pas de surface frontend pour:
    - create plan
    - activate company
    - create staff
    - audit logs

## Base de Donnees

Tables metier presentes et deja confirmees:

- auth / users:
  - users
  - user_company_roles
  - otp_codes
  - refresh_tokens
  - email_verification_tokens
  - password_reset_tokens
- commerce:
  - companies
  - company_settings
  - plans
  - subscriptions
  - subscription_invoices
  - subscription_renewals
  - stores
  - categories
  - products
  - stock_movements
  - product_history
  - catalog_sources
  - catalog_import_jobs
  - catalog_import_errors
  - product_sync_jobs
- customer order flow:
  - carts
  - cart_items
  - orders
  - order_items
  - payments
  - receipts
  - pickups
  - deliveries
  - order_qr_codes
- notifications / support:
  - notifications
  - notification_templates
  - notification_events
  - support_tickets
  - support_messages
  - support_attachments
  - audit_logs
- integrations:
  - api_integrations
  - api_credentials
  - api_call_logs
  - external_product_cache
  - webhook_endpoints
  - webhook_deliveries
- loyalty / wallet:
  - loyalty_programs
  - loyalty_tiers
  - card_templates
  - loyalty_cards
  - loyalty_transactions
  - loyalty_rewards
  - loyalty_coupons
  - customer_scores
  - wallet_payment_methods

## Priorite de Fermeture

### Priorite 1

- notifications frontend:
  - summary
  - mark one read
  - templates
  - events
- companies frontend:
  - feature flags
  - plans
  - pay subscription invoice
- integrations frontend:
  - webhook deliveries
  - webhook test
- receipts frontend:
  - generate
  - qr
  - by order

### Priorite 2

- superadmin frontend:
  - audit logs
  - create plan
  - activate company
  - create staff

### Priorite 3

- finition profil client / auth:
  - `verify-email`
  - update profile unifie

## Condition pour dire "systeme complet"

On pourra dire que le systeme est complet et equilibre quand:

- chaque endpoint metier important du backend a soit:
  - un ecran frontend
  - un flux frontend
  - ou une justification claire de rester purement admin/technique
- les migrations sont appliquees jusqu'au dernier niveau utile
- les workers async tournent sans erreur runtime de schema
- les parcours coeur passent:
  - inscription -> OTP -> commande -> paiement -> recu
  - merchant -> catalogue -> commandes -> paiements -> rapports
  - loyalty -> wallet -> support -> webhooks
