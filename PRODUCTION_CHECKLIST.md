# Fiissa — Checklist Production

## Avant premier déploiement

### Secrets et configuration
- [ ] Générer SECRET_KEY : `openssl rand -hex 32`
- [ ] Configurer `.env.prod` avec toutes les valeurs (voir `.env.prod.example`)
- [ ] Vérifier que `.env.prod` n'est pas commité dans git (`.gitignore`)
- [ ] Configurer `POSTGRES_PASSWORD` fort (min. 32 caractères)
- [ ] Configurer `REDIS_PASSWORD` fort (min. 32 caractères)

### Infrastructure
- [ ] Obtenir certificat SSL (Let's Encrypt via certbot ou certificat commercial)
- [ ] Placer `fullchain.pem` et `privkey.pem` dans `nginx/ssl/`
- [ ] Configurer DNS : `fiissa.com` → IP serveur, `www.fiissa.com` → IP serveur
- [ ] Ouvrir ports 80 et 443 sur le pare-feu serveur
- [ ] Vérifier espace disque disponible (min. 20 Go recommandés)

### Services tiers
- [ ] Configurer SMTP Brevo (`BREVO_API_KEY`) et tester envoi d'un email
- [ ] Configurer Sentry DSN backend (`SENTRY_DSN`) et vérifier un event de test
- [ ] Configurer Sentry DSN frontend et vérifier un event de test
- [ ] Configurer Africa's Talking / Twilio (`SMS_PROVIDER` + clés API) et tester un SMS
- [ ] Configurer FedaPay (`FEDAPAY_API_KEY`) en mode production (`FEDAPAY_SANDBOX=false`)
- [ ] Créer le bucket MinIO `receipts` et `products` (ou configurer S3)

### Données initiales
- [ ] Définir `SUPERADMIN_EMAIL` et `SUPERADMIN_PASSWORD` dans `.env.prod`
- [ ] Lancer migrations : `docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head`
- [ ] Seed superadmin : `docker compose -f docker-compose.prod.yml run --rm backend python scripts/seed.py`

### Backup
- [ ] Tester le script backup : `bash scripts/backup.sh`
- [ ] Tester la restauration depuis un backup : `bash scripts/restore.sh /path/to/backup.sql.gz`
- [ ] Configurer le cron backup quotidien : `0 2 * * * /opt/fiissa/scripts/backup.sh >> /var/log/fiissa-backup.log 2>&1`
- [ ] Vérifier rétention 30 jours (automatique dans le script)

---

## Déploiement initial

```bash
# Depuis /opt/fiissa sur le serveur
git clone <repo> /opt/fiissa
cp .env.prod.example .env.prod
# Remplir .env.prod

# Premier démarrage (sans backup car DB vide)
bash scripts/deploy.sh --no-backup
```

- [ ] `bash scripts/deploy.sh` s'exécute sans erreur
- [ ] Vérifier `http://fiissa.com` redirige bien vers HTTPS
- [ ] Vérifier `https://fiissa.com/api/health` → `{"status":"ok","db":"connected","redis":"connected"}`
- [ ] Tester login superadmin via l'interface
- [ ] Tester création d'une entreprise et d'une commande client

---

## Déploiements suivants

```bash
bash scripts/deploy.sh
```

- Backup automatique pré-déploiement inclus
- Migrations Alembic automatiques
- Rollback automatique si health check échoue
- Pour rollback manuel : `bash scripts/rollback.sh`

---

## Monitoring

- [ ] Sentry configuré — vérifier réception d'un event de test
- [ ] Alertes Sentry : error rate > 1%, latence P95 > 2s
- [ ] Logs Nginx disponibles dans le volume `nginx_logs`
- [ ] Surveiller l'espace disque des volumes Docker régulièrement

---

## Sécurité post-déploiement

- [ ] Vérifier les headers de sécurité : `curl -I https://fiissa.com`
  - `Strict-Transport-Security` présent
  - `X-Frame-Options: DENY` présent
  - `X-Content-Type-Options: nosniff` présent
- [ ] Tester le rate limiting sur `/api/v1/auth/login` (max 5 req/min par IP)
- [ ] Confirmer que MinIO console (port 9001) n'est pas accessible publiquement
- [ ] Vérifier que `/docs` et `/redoc` FastAPI sont désactivés en production
- [ ] Confirmer que `DEBUG=false` et `ENVIRONMENT=production` dans `.env.prod`

---

## Références

- Script déploiement : `scripts/deploy.sh`
- Script rollback manuel : `scripts/rollback.sh`
- Script backup : `scripts/backup.sh`
- Script restore : `scripts/restore.sh`
- Config nginx : `nginx/nginx.conf`
- Docker Compose prod : `docker-compose.prod.yml`
