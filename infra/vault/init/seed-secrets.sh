#!/bin/sh
# Writes initial placeholder secrets to Vault on first boot.
# These are dev defaults; real secrets get set during Plan 0b auth wiring.

set -e

echo "[vault-init] waiting for Vault..."
export VAULT_ADDR="http://vault:8200"
until vault status >/dev/null 2>&1; do
  sleep 2
done

echo "[vault-init] logging in with root token..."
vault login "${VAULT_ROOT_TOKEN}" >/dev/null

echo "[vault-init] enabling kv-v2 secrets engine..."
vault secrets enable -path=secret -version=2 kv 2>/dev/null || true

echo "[vault-init] writing placeholder secrets..."
# JWT key — real one set in Plan 0c
vault kv put secret/jwt signing_key="placeholder-jwt-key-replaced-in-plan-0c"

# Groq key — real one set in Plan 1
vault kv put secret/llm groq_api_key="placeholder-groq-key-replaced-in-plan-1"

# GitHub token — real one set in Plan 1
vault kv put secret/github personal_access_token="placeholder-gh-token-replaced-in-plan-1"

# DB password (mirrors env for app convenience)
vault kv put secret/db password="${DB_PASSWORD}"

# MinIO creds (mirror env)
vault kv put secret/minio access_key="${MINIO_ROOT_USER}" secret_key="${MINIO_ROOT_PASSWORD}"

# Langfuse keys — these are filled by Langfuse on first user signup; placeholder for now
vault kv put secret/langfuse public_key="placeholder" secret_key="placeholder"

echo "[vault-init] done."
