#!/bin/sh
# Generates a fresh 512-bit random JWT signing key and writes it to Vault at secret/jwt.
# Run this once before bringing up the api for real, and on every prod rotation.

set -e

# load .env so VAULT_ROOT_TOKEN is available
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

if [ -z "${VAULT_ROOT_TOKEN:-}" ]; then
  echo "VAULT_ROOT_TOKEN is not set. Did you copy .env.example to .env?" >&2
  exit 1
fi

NEW_KEY="$(openssl rand -hex 64)"

echo "[rotate-jwt] writing new signing key to vault..."
docker compose exec -T vault sh -c "
  export VAULT_ADDR=http://vault:8200
  vault login ${VAULT_ROOT_TOKEN} >/dev/null
  vault kv put secret/jwt signing_key='${NEW_KEY}' >/dev/null
"

echo "[rotate-jwt] done. Restart the api container so it picks up the new key:"
echo "  docker compose restart api"
