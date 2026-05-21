"""Renders the classifier model card and computes the weights SHA."""
import hashlib

from scripts._classifier_eval import EvalReport


def compute_weights_sha(weights_bytes: bytes) -> str:
    """SHA-256 of the safetensors weights blob; used by the refuse-to-boot check."""
    return hashlib.sha256(weights_bytes).hexdigest()


def render_model_card(
    architecture: str,
    hyperparams: dict[str, float | int | str],
    weights_sha: str,
    training_data_hash: str,
    eval_report: EvalReport,
) -> str:
    """Renders the model card as markdown — the api startup check parses weights_sha from it."""
    hp_lines = "\n".join(f"- **{k}:** {v}" for k, v in hyperparams.items())

    cm = eval_report.confusion_matrix
    cm_md = "| | " + " | ".join(["bug", "feature", "docs", "question"]) + " |\n"
    cm_md += "|---|" + "|".join(["---"] * 4) + "|\n"
    labels = ["bug", "feature", "docs", "question"]
    for i, row in enumerate(cm):
        cm_md += f"| **{labels[i]}** | " + " | ".join(str(x) for x in row) + " |\n"

    per_class_lines = "\n".join(
        f"- **{cls}:** {f1:.4f}" for cls, f1 in eval_report.per_class_f1.items()
    )

    return f"""# Issue Classifier — model card

## Architecture
{architecture}

## Hyperparameters
{hp_lines}

## Hashes
- **weights_sha256:** `{weights_sha}`
- **training_data_hash:** `{training_data_hash}`

## Metrics (test split)
- **accuracy:** {eval_report.accuracy:.4f}
- **macro_f1:** {eval_report.macro_f1:.4f}

### Per-class F1
{per_class_lines}

### Confusion matrix
{cm_md}

### Latency
- **p50:** {eval_report.p50_latency_ms:.1f} ms
- **p95:** {eval_report.p95_latency_ms:.1f} ms
"""
