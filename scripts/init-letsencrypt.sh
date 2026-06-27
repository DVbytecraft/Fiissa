#!/bin/sh
# Initialize Let's Encrypt for the production compose stack.

set -eu

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
DATA_PATH="$PROJECT_DIR/certbot"

cd "$PROJECT_DIR"

if ! docker compose version >/dev/null 2>&1; then
  echo "Error: docker compose is not available." >&2
  exit 1
fi

DOMAINS="${1:-fiissa.com}"
RSA_KEY_SIZE=4096
EMAIL="${2:-admin@fiissa.com}"
STAGING="${3:-0}"

if [ -d "$DATA_PATH/conf/live/" ]; then
  printf "Existing certificates detected. Delete and continue? (y/N) "
  read -r DECISION
  if [ "$DECISION" != "Y" ] && [ "$DECISION" != "y" ]; then
    exit 0
  fi
fi

mkdir -p "$DATA_PATH/conf" "$DATA_PATH/www"

if [ ! -e "$DATA_PATH/conf/options-ssl-nginx.conf" ]; then
  curl -fsSL https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$DATA_PATH/conf/options-ssl-nginx.conf"
fi
if [ ! -e "$DATA_PATH/conf/ssl-dhparams.pem" ]; then
  curl -fsSL https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$DATA_PATH/conf/ssl-dhparams.pem"
fi

echo "### Creating temporary certificate for nginx bootstrap ..."
CERT_PATH="/etc/letsencrypt/live/$DOMAINS"
mkdir -p "$DATA_PATH/conf/live/$DOMAINS"
docker compose -f "$COMPOSE_FILE" run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:$RSA_KEY_SIZE -days 1 \
    -keyout '$CERT_PATH/privkey.pem' \
    -out '$CERT_PATH/fullchain.pem' \
    -subj '/CN=localhost'" certbot
echo

echo "### Starting nginx ..."
docker compose -f "$COMPOSE_FILE" up --force-recreate -d nginx
echo

echo "### Removing temporary certificate ..."
rm -rf "$DATA_PATH/conf/live/$DOMAINS"
rm -rf "$DATA_PATH/conf/archive/$DOMAINS"
rm -rf "$DATA_PATH/conf/renewal/$DOMAINS.conf"
echo

echo "### Requesting Let's Encrypt certificate ..."
DOMAIN_ARGS=""
for DOMAIN in $DOMAINS; do
  DOMAIN_ARGS="$DOMAIN_ARGS -d $DOMAIN"
done

case "$EMAIL" in
  "") EMAIL_ARG="--register-unsafely-without-email" ;;
  *) EMAIL_ARG="--email $EMAIL" ;;
esac

STAGING_ARG=""
if [ "$STAGING" != "0" ]; then
  STAGING_ARG="--staging"
fi

docker compose -f "$COMPOSE_FILE" run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $STAGING_ARG \
    $EMAIL_ARG \
    $DOMAIN_ARGS \
    --rsa-key-size $RSA_KEY_SIZE \
    --non-interactive \
    --agree-tos" certbot
echo

echo "### Reloading nginx ..."
docker compose -f "$COMPOSE_FILE" exec nginx nginx -s reload
echo

echo "### Success: SSL configured for $DOMAINS"
