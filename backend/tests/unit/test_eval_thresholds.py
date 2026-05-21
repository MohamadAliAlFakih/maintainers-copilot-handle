"""Tests for the threshold loader."""

from pathlib import Path

from evals.classification._runner import (
    check_classification_thresholds,
    load_thresholds,
)


def test_load_thresholds_returns_nested_dict(tmp_path: Path):
    """load_thresholds reads YAML and returns the parsed dict."""
    p = tmp_path / "th.yaml"
    p.write_text(
        "classification:\n"
        "  roberta:\n"
        "    macro_f1_min: 0.7\n"
        "    per_class_f1_min:\n"
        "      bug: 0.65\n"
    )
    t = load_thresholds(p)
    assert t["classification"]["roberta"]["macro_f1_min"] == 0.7


def test_check_classification_passes_when_above_thresholds():
    """No violations when all metrics meet the thresholds."""
    thresholds = {
        "classification": {
            "roberta": {
                "macro_f1_min": 0.75,
                "per_class_f1_min": {"bug": 0.7, "feature": 0.7, "docs": 0.6, "question": 0.6},
            }
        }
    }
    report = {
        "models": {
            "roberta": {
                "macro_f1": 0.80,
                "per_class_f1": {"bug": 0.78, "feature": 0.75, "docs": 0.70, "question": 0.72},
            }
        }
    }
    violations = check_classification_thresholds(thresholds, report)
    assert violations == []


def test_check_classification_flags_low_macro_f1():
    """Low macro-F1 produces a violation."""
    thresholds = {"classification": {"roberta": {"macro_f1_min": 0.75, "per_class_f1_min": {}}}}
    report = {"models": {"roberta": {"macro_f1": 0.60, "per_class_f1": {}}}}
    violations = check_classification_thresholds(thresholds, report)
    assert len(violations) == 1
    assert "macro_f1" in violations[0].metric


def test_check_classification_flags_low_per_class():
    """A single low per-class F1 produces a violation."""
    thresholds = {
        "classification": {
            "roberta": {
                "macro_f1_min": 0.5,
                "per_class_f1_min": {"bug": 0.75},
            }
        }
    }
    report = {
        "models": {
            "roberta": {
                "macro_f1": 0.8,
                "per_class_f1": {"bug": 0.50},
            }
        }
    }
    violations = check_classification_thresholds(thresholds, report)
    assert len(violations) == 1
    assert violations[0].metric == "per_class_f1.bug"
