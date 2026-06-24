# SmartCheckout

SaaS multi-tenant pour supermarchés, restaurants et commerce local en zone UEMOA. Click & Collect, livraison, Scan & Go, Mobile Money, reçus PDF.

## Stack technique

- **Backend** : FastAPI + Python 3.12 + SQLAlchemy 2.0 (async) + PostgreSQL 16
- **Workers** : Celery 5 + Redis 7
- **Frontend** : Next.js 14 + TypeScript + Tailwind CSS + PWA
- **Stockage** : MinIO (compatible S3)
- **PDF** : WeasyPrint
- **SMS** : Africa's Talking

## Démarrage rapide

### Prérequis

- Docker Desktop ≥ 24
- Git

### 1. Cloner et configurer

```bash
git clone https://github.com/votre-org/smartcheckout.git
cd smartcheckout
cp .env.example .env
```

Modifier `.env` :
- `SECRET_KEY` : générer avec `openssl rand -hex 32`
- `SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD`
- Identifiants SMS Africa's Talking (optionnel pour dev)

### 2. Lancer les services

```bash
make dev
```

Services disponibles :
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |

### 3. Migrations et données de démo

```bash
make migrate   # Créer toutes les tables
make seed      # Insérer super-admin + boutique démo
```

Compte gérant démo : `gerant@fatou.sn` / `Demo1234!`

## Architecture multi-tenant

Isolation par `company_id` sur toutes les tables métier. Chaque employé ne voit que les données de son entreprise. Contrôle triple en cascade :
1. JWT valide + utilisateur actif
2. Permission requise (`products.create`, `payments.confirm`, etc.)
3. `company_id` dans le JWT correspond au `company_id` de la ressource

## Flux de commande

```
draft → pending → awaiting_payment → payment_submitted
      ↓
   confirmed → preparing → ready → out_for_delivery → delivered
      ↓
   cancelled | refunded
```

## Paiement Mobile Money V1

1. Client soumet une preuve de paiement (opérateur + référence transaction)
2. Le marchand vérifie sur son app Mobile Money
3. Le marchand confirme ou rejette avec une raison
4. Confirmation → génération automatique du reçu PDF + QR code

Protection anti-fraude : contrainte UNIQUE sur `(company_id, operator, transaction_ref)`.

## Tests

```bash
make test              # Tous les tests
make test-auth         # Tests authentification
make test-isolation    # Tests isolation multi-tenant
make test-orders       # Tests commandes
make test-coverage     # Avec rapport de couverture HTML
```

## Déploiement production

### Prérequis serveur
- Linux (Ubuntu 22.04 LTS recommandé)
- Docker + Docker Compose
- Certificats SSL (Let's Encrypt via Certbot)

### Déploiement

```bash
cp .env.example .env.prod
# Éditer .env.prod avec les valeurs de production

# Certificats SSL
certbot certonly --standalone -d smartcheckout.africa
cp /etc/letsencrypt/live/smartcheckout.africa/fullchain.pem nginx/ssl/
cp /etc/letsencrypt/live/smartcheckout.africa/privkey.pem nginx/ssl/

# Démarrer
make deploy
```

### Variables production requises

```env
ENVIRONMENT=production
SECRET_KEY=<32 bytes hex>
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/smartcheckout
REDIS_URL=redis://:password@redis:6379/0
AT_API_KEY=<Africa's Talking API key>
AT_USERNAME=<username>
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=<key>
MINIO_SECRET_KEY=<secret>
```

### Sauvegardes automatiques

```bash
# Ajouter au cron du serveur
0 2 * * * docker exec smartcheckout-postgres-1 bash /backup/backup.sh
```

Les sauvegardes sont conservées 30 jours dans le volume `postgres_data:/backup`.

## Structure du projet

```
smartcheckout/
├── backend/
│   ├── apps/
│   │   ├── auth/         # Authentification JWT + OTP
│   │   ├── catalog/      # Produits, catégories, stock
│   │   ├── companies/    # Entreprises + abonnements
│   │   ├── notifications/# Notifications + audit logs
│   │   ├── orders/       # Commandes + state machine
│   │   ├── payments/     # Mobile Money V1
│   │   ├── receipts/     # Reçus PDF + QR vérification
│   │   ├── reports/      # Rapports + exports
│   │   └── stores/       # Boutiques
│   ├── core/             # Config, DB, sécurité, permissions
│   ├── workers/          # Celery tasks + beat scheduler
│   ├── alembic/          # Migrations DB
│   └── tests/            # Tests pytest
├── frontend/
│   └── app/
│       ├── (customer)/   # Interface client PWA
│       ├── (merchant)/   # Dashboard marchand
│       ├── (security)/   # Interface agent sécurité
│       └── (superadmin)/ # Administration plateforme
├── nginx/                # Configuration Nginx
├── scripts/              # Seed, backup, init SQL
└── docker-compose.yml    # Environnement développement
```

## Rôles et permissions

| Rôle | Description |
|------|-------------|
| `super_admin` | Accès total plateforme |
| `company_owner` | Propriétaire d'entreprise |
| `store_manager` | Gérant de boutique |
| `accountant` | Comptable (lecture rapports) |
| `preparer` | Préparateur de commandes |
| `security_agent` | Vérification QR à la sortie |
| `support_agent` | Support client |
| `customer` | Client final |

## Licence

Propriétaire — tous droits réservés.
