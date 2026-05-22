# Runbook

## First-time setup

```
git clone <repo>
cd handle
cp .env.example .env
# .env defaults are fine for local dev; edit if you want
docker compose up -d --build
# wait ~5 minutes for Langfuse and the modelserver to fully boot
./scripts/check-stack.sh
```

After this, the stack is up but has no data. Run the bootstrap steps:

```
# 1. set real secrets in Vault
./scripts/rotate_jwt_key.sh
docker compose exec vault sh -c "
  export VAULT_ADDR=http://vault:8200
  vault login \${VAULT_ROOT_TOKEN} >/dev/null
  vault kv put secret/llm groq_api_key='gsk_REAL_KEY'
  vault kv put secret/github personal_access_token='ghp_REAL_PAT'
"
docker compose restart api modelserver

# 2. fetch dataset + docs (one-time)
docker compose exec api uv run python /app/scripts/fetch_dataset.py
docker compose exec api uv run python /app/scripts/fetch_docs.py

# 3. train the classifier (~20-45 min on CPU)
docker compose exec api uv run python /app/scripts/train_classifier.py

# 4. ingest corpus
docker compose exec api uv run python /app/scripts/ingest_corpus.py

# 5. restart so refuse-to-boot checks pass with populated chunks table
docker compose restart api
sleep 30
./scripts/check-stack.sh
```

## Run the evals locally

```
docker compose exec api uv run python /app/evals/run_all.py
```

## Demo flow (Friday)

1. Open `http://localhost:9000` — widget bubble appears, click → chat.
2. Open `http://localhost:8501` — Streamlit; log in as `admin@example.com` / password from seed.
3. Open `http://localhost:3001` — Langfuse — show the trace tree from a real chat.
4. From Streamlit widget admin, edit `wgt_demo` to remove `http://localhost:9000` from allowed_origins.
5. Refresh `http://localhost:9000` — widget blocked. Show DevTools Console + Network.
6. Restore the allowlist; widget works again.

## Common operations

- **Re-seed demo:** `docker compose exec api uv run python /app/scripts/seed_demo.py`
- **Promote user to admin:** `docker compose exec api uv run python /app/scripts/promote_admin.py user@example.com`
- **Rotate JWT key:** `./scripts/rotate_jwt_key.sh && docker compose restart api`
- **Clear MinIO data:** `docker compose down -v` then re-run setup
- **Inspect audit log:** `docker compose exec db psql -U handle -d handle -c "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 20;"`

## Troubleshooting

- **api refuses to boot with "weights SHA mismatch"** — re-run `train_classifier.py` to produce a fresh artifact.
- **api refuses to boot with "chunks table is empty"** — run `ingest_corpus.py`.
- **api refuses to boot with "JWT signing key is placeholder"** — run `./scripts/rotate_jwt_key.sh`.
- **Widget loads but chat returns 401** — token expired; re-login via Streamlit or refresh the host page.
- **CORS error on `/widgets/.../config`** — host_origin not in the widget's allowed_origins; fix via the Streamlit admin page.
