# Fiissa - Production Checklist

## Pre-flight

- [ ] Copy `.env.prod.example` to `.env.prod`
- [ ] Generate a real `SECRET_KEY` with `openssl rand -hex 32`
- [ ] Set strong values for `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
- [ ] Verify `APP_URL`, `API_URL`, `CORS_ORIGINS`, and `ALLOWED_HOSTS`
- [ ] Set `FEDAPAY_*`, `SMTP_*`, `BREVO_API_KEY`, `SENTRY_DSN`, and SMS provider secrets if those integrations are enabled
- [ ] Set `SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD`, and `SUPERADMIN_PHONE`
- [ ] Confirm DNS for `fiissa.com` and `www.fiissa.com`
- [ ] Open ports `80` and `443`
- [ ] Confirm at least 20 GB free disk space for Docker volumes and backups

## First Boot Commands

```bash
cd /opt/fiissa
cp .env.prod.example .env.prod
# edit .env.prod

docker compose -f docker-compose.prod.yml --env-file .env.prod build --pull backend worker beat frontend
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d postgres redis minio
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend alembic upgrade head
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend python scripts/seed.py
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d backend worker beat frontend nginx certbot
```

## Health Validation

- [ ] `docker compose -f docker-compose.prod.yml --env-file .env.prod ps`
- [ ] `docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T backend curl -fsS http://localhost:8000/health`
- [ ] `/health` reports `db=connected`
- [ ] `/health` reports `redis=connected`
- [ ] `/health` reports `storage=connected`
- [ ] `/health` reports `celery=connected`
- [ ] `postgres`, `redis`, `minio`, `backend`, `worker`, `beat`, `frontend`, and `nginx` are `healthy` or `running`

## TLS

- [ ] If using Let's Encrypt, run `bash scripts/init-letsencrypt.sh fiissa.com admin@fiissa.com`
- [ ] If using pre-issued certificates, place them under `certbot/conf/live/fiissa.com/`
- [ ] `http://fiissa.com` redirects to HTTPS
- [ ] `curl -I https://fiissa.com` returns HSTS, `X-Frame-Options`, and `X-Content-Type-Options`

## Storage and Data Safety

- [ ] MinIO health passes: `docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T minio curl -fsS http://localhost:9000/minio/health/live`
- [ ] Buckets `products` and `receipts` exist after backend startup
- [ ] Product image upload returns a public API URL, not an internal `minio:9000` URL
- [ ] Receipt PDF download works through `/api/v1/receipts/download/...`
- [ ] Backup works: `docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > scripts/backup/manual_smoke.sql.gz`
- [ ] Restore drill works: `bash scripts/restore.sh scripts/backup/manual_smoke.sql.gz`

## Live Smoke Test

- [ ] Customer registration and OTP login
- [ ] Product lookup and cart add
- [ ] Order creation
- [ ] Payment creation
- [ ] Payment proof submission
- [ ] Receipt generation and PDF download
- [ ] Outbound webhook delivery
- [ ] Delayed Celery task execution
- [ ] Merchant dashboard and pending payments

## External Integrations

- [ ] SMTP/Brevo test email sent and received
- [ ] SMS provider test sent and received if SMS is enabled
- [ ] FedaPay or PayGate test transaction confirmed
- [ ] Sentry test event visible in the target project
- [ ] MinIO or S3 object upload and download verified with real credentials

## Load and Resilience

- [ ] Run Locust against the live stack:

```bash
cd backend
locust -f tests/locustfile.py --host https://fiissa.com --headless -u 100 -r 10 -t 120s --csv reports/load_100users
```

- [ ] Review p95 latency under 2000 ms
- [ ] Review error rate under 1%
- [ ] Review `backend`, `worker`, `beat`, `nginx`, and `redis` logs during the run

## Operational Commands

```bash
# full deploy
bash scripts/deploy.sh

# first deploy without existing database
bash scripts/deploy.sh --no-backup

# stack status
docker compose -f docker-compose.prod.yml --env-file .env.prod ps

# backend health
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T backend curl -fsS http://localhost:8000/health

# targeted logs
docker compose -f docker-compose.prod.yml --env-file .env.prod logs --tail=100 backend worker beat nginx minio

# manual rollback
bash scripts/rollback.sh
```

## Remaining Honest Blockers Before Real Production Certification

- [ ] A full live `docker compose -f docker-compose.prod.yml up` has been executed in an environment with Docker daemon access
- [ ] Real `.env.prod` secrets have been injected and validated
- [ ] Real SMTP, SMS, payment, Sentry, and object-storage providers have been exercised end-to-end
- [ ] Backup and restore drills have been executed against a running production-like database
- [ ] Locust has been run against the running stack and results reviewed
