.PHONY: help dev prod down logs migrate seed test shell clean build

help:
	@echo "SmartCheckout — Commandes disponibles :"
	@echo ""
	@echo "  make dev         Démarrer l'environnement de développement"
	@echo "  make prod        Démarrer l'environnement de production"
	@echo "  make down        Arrêter tous les services"
	@echo "  make logs        Afficher les logs en temps réel"
	@echo "  make migrate     Exécuter les migrations Alembic"
	@echo "  make seed        Insérer les données de démo"
	@echo "  make test        Lancer les tests backend"
	@echo "  make shell       Ouvrir un shell dans le backend"
	@echo "  make clean       Supprimer volumes et images"
	@echo "  make build       Reconstruire les images"
	@echo ""

# Développement
dev:
	docker compose up -d
	@echo "Services démarrés :"
	@echo "  Backend API : http://localhost:8000"
	@echo "  Frontend    : http://localhost:3000"
	@echo "  API Docs    : http://localhost:8000/docs"
	@echo "  MinIO       : http://localhost:9001"

# Production
prod:
	docker compose -f docker-compose.prod.yml up -d
	@echo "Production démarrée"

down:
	docker compose down

down-prod:
	docker compose -f docker-compose.prod.yml down

logs:
	docker compose logs -f --tail=100

logs-backend:
	docker compose logs -f backend worker beat

# Base de données
migrate:
	docker compose exec backend alembic upgrade head

migrate-create:
	docker compose exec backend alembic revision --autogenerate -m "$(MSG)"

migrate-rollback:
	docker compose exec backend alembic downgrade -1

seed:
	docker compose exec backend python scripts/seed.py

# Tests
test:
	docker compose exec backend pytest -v --tb=short

test-coverage:
	docker compose exec backend pytest --cov=. --cov-report=html -v

test-auth:
	docker compose exec backend pytest tests/test_auth.py -v

test-isolation:
	docker compose exec backend pytest tests/test_tenant_isolation.py -v

test-orders:
	docker compose exec backend pytest tests/test_orders.py -v

# Utilitaires
shell:
	docker compose exec backend bash

shell-db:
	docker compose exec postgres psql -U smartcheckout -d smartcheckout

build:
	docker compose build --no-cache

clean:
	docker compose down -v --remove-orphans
	docker image prune -f

# Déploiement production
deploy:
	@echo "=== Déploiement SmartCheckout ==="
	git pull origin main
	docker compose -f docker-compose.prod.yml build
	docker compose -f docker-compose.prod.yml up -d
	docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
	@echo "=== Déploiement terminé ==="

backup:
	docker compose -f docker-compose.prod.yml exec postgres bash /backup/backup.sh

# Monitoring
ps:
	docker compose ps

health:
	curl -s http://localhost:8000/health | python -m json.tool
