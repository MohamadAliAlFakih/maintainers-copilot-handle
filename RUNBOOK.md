# Runbook

The repo has two tracks:

1. **`data-pipeline/`** — offline, run once on a workstation. Fetches the
   GitHub issues + pandas docs, fine-tunes the RoBERTa classifier, chunks the
   corpus, and embeds it with BGE + MiniLM. Outputs land in `./data/`.
2. **`docker compose up`** — online stack. The `artifacts-loader` init
   container reads `./data/artifacts/` and pushes weights to MinIO + chunks
   to pgvector on first boot. After that `api` and `modelserver` start in
   seconds with no GPU and no network.

## Step 1 — produce artifacts (offline, one-time)

```bash
cd data-pipeline
uv sync                                    # installs torch+cu124, transformers, etc.
export GITHUB_TOKEN=ghp_xxx                # PAT only used here, never copied into MinIO
uv run python -m src.run_all               # ~30-90 min total on a CUDA GPU
cd ..
```

This writes:

```
data/raw/dataset/manifest.json
data/raw/dataset/splits/{train,val,test,rag_held_out}.parquet
data/raw/docs/pandas_docs.tar.gz
data/artifacts/classifier/roberta-issue-cls-v1/{model.safetensors,model_card.md,eval_report.json}
data/artifacts/rag/{chunks.parquet,bge.npy,minilm.npy,manifest.json}
```

`./data/` is `.gitignore`d — re-run the pipeline whenever you want fresh artifacts.

## Step 2 — bring up the online stack

```bash
cp .env.example .env                       # only Vault root token + ports live here
./scripts/rotate_jwt_key.sh                # sets a real JWT signing key in Vault
docker compose exec vault sh -c '
  export VAULT_ADDR=http://vault:8200
  vault login ${VAULT_ROOT_TOKEN} >/dev/null
  vault kv put secret/llm groq_api_key="gsk_REAL_KEY"
'
docker compose up -d --build
./scripts/check-stack.sh                    # waits for api + modelserver healthy
```

The `artifacts-loader` init service handles loading; you don't run it manually.

## Run the evals locally

```bash
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
- **Promote user to admin:** `docker compose exec api uv run python -m scripts.admin.promote_admin user@example.com`
- **Rotate JWT key:** `./scripts/rotate_jwt_key.sh && docker compose restart api`
- **Rebuild artifacts after data change:** `cd data-pipeline && uv run python -m src.run_all --force`
- **Force loader to re-publish:** `docker compose exec db psql -U handle -d handle -c "DELETE FROM chunks;" && docker compose restart artifacts-loader`
- **Inspect audit log:** `docker compose exec db psql -U handle -d handle -c "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 20;"`

## Troubleshooting

- **artifacts-loader exits with "no /data/artifacts/classifier"** — you haven't run the offline pipeline yet (see Step 1).
- **api refuses to boot with "weights SHA mismatch"** — `data/artifacts/classifier/.../model.safetensors` was edited out-of-band; re-run training.
- **api refuses to boot with "chunks table is empty"** — `artifacts-loader` didn't run successfully; check `docker compose logs artifacts-loader`.
- **api refuses to boot with "JWT signing key is placeholder"** — run `./scripts/rotate_jwt_key.sh`.
- **Widget loads but chat returns 401** — token expired; re-login via Streamlit or refresh the host page.
- **CORS error on `/widgets/.../config`** — host_origin not in the widget's allowed_origins; fix via the Streamlit admin page.
