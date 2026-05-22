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

echo "[vault-init] writing placeholder secrets (skip-if-exists)..."

# Helper: write a placeholder only if the path doesn't already exist.
seed_if_missing() {
  path="$1"
  shift
  if vault kv get "$path" >/dev/null 2>&1; then
    echo "[vault-init] $path already exists, leaving as-is"
  else
    vault kv put "$path" "$@"
  fi
}

# JWT key — real one set in Plan 0c
seed_if_missing secret/jwt signing_key="placeholder-jwt-key-replaced-in-plan-0c"

# Azure OpenAI credentials — real ones pasted into Vault UI after first boot
seed_if_missing secret/llm \
  api_key="placeholder-azure-api-key" \
  endpoint="https://placeholder.openai.azure.com" \
  deployment="gpt-4o" \
  api_version="2024-02-01"

# GitHub token — real one set in Plan 1
seed_if_missing secret/github personal_access_token="placeholder-gh-token-replaced-in-plan-1"

# DB password (mirrors env for app convenience)
vault kv put secret/db password="${DB_PASSWORD}"

# MinIO creds (mirror env)
vault kv put secret/minio access_key="${MINIO_ROOT_USER}" secret_key="${MINIO_ROOT_PASSWORD}"

# Langfuse keys ??? these are filled by Langfuse on first user signup; placeholder for now
vault kv put secret/langfuse public_key="placeholder" secret_key="placeholder"

echo "[vault-init] done."
