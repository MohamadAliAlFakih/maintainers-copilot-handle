# data-pipeline

Offline track that produces every artifact the online stack needs. Runs once on a workstation with a GitHub PAT (and, for fast training, a CUDA-capable GPU).

```
data/
  raw/
    dataset/   <- fetched GitHub issues + splits
    docs/      <- pandas_docs.tar.gz (sparse-checkout of doc/source)
  artifacts/
    classifier/<MODEL_NAME>/
      model.safetensors
      model_card.md
      eval_report.json
    rag/
      chunks.parquet
      bge.npy
      minilm.npy
      manifest.json
```

## Setup

```bash
cd data-pipeline
uv sync
```

## Run individual stages

```bash
# 1. fetch GitHub issues, map labels, build splits
GITHUB_TOKEN=ghp_xxx uv run python -m src.fetch_dataset

# 2. sparse-checkout pandas docs into a tarball
uv run python -m src.fetch_docs

# 3. fine-tune the RoBERTa classifier
uv run python -m src.train_classifier

# 4. chunk docs+issues, embed with BGE + MiniLM, save parquet+npy
uv run python -m src.ingest_corpus
```

Each stage is idempotent — skips if its output already exists. Pass `--force` to rebuild.

## Run everything

```bash
GITHUB_TOKEN=ghp_xxx uv run python -m src.run_all
```

## Online stack

`docker compose up` consumes the artifacts from `data/artifacts/`: the online init container pushes weights to MinIO and chunks+embeddings to pgvector, then `api` and `modelserver` boot in seconds with no GPU and no network.
