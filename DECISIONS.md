# Decisions

Project-wide decisions backed by numbers or rationale, per the brief's "every decision backed by a number" rule.

## Pipeline split (offline `data-pipeline/` vs online `docker compose`)

**Decision:** A separate top-level `data-pipeline/` package owns dataset fetch,
docs fetch, classifier fine-tuning, and corpus chunking + embedding. Its
outputs land in `./data/` (gitignored). The online compose stack has a single
`artifacts-loader` init container that mounts `./data/:ro` and pushes weights
into MinIO + chunks/embeddings into pgvector.

**Reason:** The brief requires `docker compose up` from a fresh clone after
`cp .env.example .env`. Doing fetch + train + ingest inside compose meant
demos needed a GitHub PAT, GPU, and tens of minutes — and broke deterministic
CI. Splitting offline (expensive, GPU, network) from online (consumer of
artifacts) lets the online stack boot in ~30 s with no GPU and no network.

**Trade:** Anyone running the system for the first time has to run the offline
pipeline once (or be handed a `data/` tarball). This is documented in
`RUNBOOK.md` step 1.

**Embeddings are pre-baked:** the offline pipeline writes `bge.npy` and
`minilm.npy` alongside `chunks.parquet`. The online loader does plain SQL
INSERTs into pgvector — no `modelserver` call at boot, no GPU required for
the online stack to come up.

## Dataset

### Source

**Decision:** `pandas-dev/pandas` repository, closed issues only, fetched via the GitHub REST API (capped at 80 pages ≈ 8000 issues).

**Reason:** Pivoted away from `fastapi/fastapi` after observing severe class skew (3097 question / 66 feature / 58 bug / 4 docs); pandas has more balanced triage labels (1777 bug / 1136 feature / 286 docs / 39 question) which gives the classifier real signal across all four classes. Docs corpus is rst-based (vs fastapi's markdown), which required extending the chunker.

### Label mapping

**Decision:**

| Maintainer label(s) | Mapped class |
|---|---|
| `bug` | `bug` |
| `feature`, `enhancement` | `feature` |
| `docs`, `documentation` | `docs` |
| `question`, `discussion`, `answered` | `question` |
| (no usable label) | dropped |
| (multiple conflicting) | dropped |

**Reason:** These are the labels the pandas-dev maintainers actually apply (case-insensitively matched, so `Bug`/`bug`/`BUG` collapse). `Enhancement`/`Performance`/`API` collapse into `feature`; `Usage Question`/`Needs info` collapse into `question`. Anything with no usable label is dropped to keep the dataset honest about what we can supervise on.

### Splits

**Decision:** Stratified by class, test strictly more recent than train, train/val/test = 72/8/20 (val is 10% of the train+val subset). Held-out RAG slice = most recent 10% of `question`-class issues, excluded from classifier train/val/test entirely.

**Reason:** Brief requirement. Time-ordered test simulates "model deployed in the past, evaluated on the future." Held-out RAG slice prevents leakage between the classifier training set and the RAG corpus.

**Seed:** 42. Committed in the manifest.

## Widget bundle size

**Target:** widget bundle < 100 KB gzipped.

**Measurement:** to be recorded after the first `docker compose build widget` completes locally; measurement command is documented below.

**Choices made to stay under budget:**
- React 18 + Tailwind (prefix-scoped `mc-`, preflight disabled at framework level so it only applies inside `.mc-root`).
- Single chunk output (no code splitting — host loads it all at once anyway).
- No-cache on `index.html` so the next deploy reaches users immediately; assets cached for 1 year via the hashed filename.

**Preact fallback (unused in v1):** if React+Tailwind ever exceeds 100 KB gzipped, swap `react` for `preact/compat` via a Vite alias. Decision deferred unless triggered.

**How to measure (run from repo root):**
```
docker run --rm -v "$(pwd)/widget:/work" -w /work node:20-alpine sh -c \
  "npm install --silent && npm run build && for f in dist/assets/*.js; do echo \"\$f raw=\$(stat -c%s \$f)  gzip=\$(gzip -9 -c \$f | wc -c)\"; done"
```
