# Decisions

Project-wide decisions backed by numbers or rationale, per the brief's "every decision backed by a number" rule.

## Dataset

### Source

**Decision:** `fastapi/fastapi` repository, closed issues only, fetched via the GitHub REST API.

**Reason:** Best label hygiene among candidates (pandas, pydantic, prefect, httpx). Markdown docs trivial to ingest later. Demo punchline lands ("a fastapi copilot built with fastapi").

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

**Reason:** These are the labels the fastapi maintainers actually apply. `enhancement` is GitHub's default, so it's used interchangeably with `feature`. `answered` and `discussion` are applied to closed Q&A threads. Anything with no usable label is dropped to keep the dataset honest about what we can supervise on.

### Splits

**Decision:** Stratified by class, test strictly more recent than train, train/val/test = 72/8/20 (val is 10% of the train+val subset). Held-out RAG slice = most recent 10% of `question`-class issues, excluded from classifier train/val/test entirely.

**Reason:** Brief requirement. Time-ordered test simulates "model deployed in the past, evaluated on the future." Held-out RAG slice prevents leakage between the classifier training set and the RAG corpus.

**Seed:** 42. Committed in the manifest.
