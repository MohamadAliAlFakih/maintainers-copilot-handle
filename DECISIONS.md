# Decisions

Project-wide decisions backed by numbers or rationale, per the brief's "every decision backed by a number" rule.

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
