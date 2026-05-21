"""Diffs two eval reports; flags any metric that regressed by > REGRESSION_THRESHOLD."""

from dataclasses import dataclass, field
from typing import Any

REGRESSION_THRESHOLD = 0.05  # 5% relative drop


@dataclass
class Regression:
    """One metric that regressed."""

    metric: str
    previous: float
    current: float
    drop_pct: float


@dataclass
class RegressionSummary:
    """Container for regressions + improvements between two reports."""

    regressions: list[Regression] = field(default_factory=list)
    improvements: list[Regression] = field(default_factory=list)


def _flat(report: dict[str, Any]) -> dict[str, float]:
    """Flattens a report into 'roberta.macro_f1' -> value pairs for diffing."""
    out: dict[str, float] = {}
    for model_name, metrics in (report.get("models") or {}).items():
        for k, v in metrics.items():
            if isinstance(v, (int, float)):
                out[f"{model_name}.{k}"] = float(v)
            elif isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    if isinstance(sub_v, (int, float)):
                        out[f"{model_name}.{k}.{sub_k}"] = float(sub_v)
    return out


def diff_reports(previous: dict[str, Any], current: dict[str, Any]) -> RegressionSummary:
    """Returns a summary listing metrics that dropped > 5% relative."""
    prev_flat = _flat(previous)
    curr_flat = _flat(current)

    summary = RegressionSummary()
    for metric, curr_val in curr_flat.items():
        prev_val = prev_flat.get(metric)
        if prev_val is None or prev_val == 0:
            continue
        change = (curr_val - prev_val) / prev_val
        if change <= -REGRESSION_THRESHOLD:
            summary.regressions.append(
                Regression(metric=metric, previous=prev_val, current=curr_val, drop_pct=-change)
            )
        elif change >= REGRESSION_THRESHOLD:
            summary.improvements.append(
                Regression(metric=metric, previous=prev_val, current=curr_val, drop_pct=-change)
            )

    return summary
