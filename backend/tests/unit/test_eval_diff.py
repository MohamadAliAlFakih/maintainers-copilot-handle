"""Tests for the eval report diff."""

from evals.classification._diff import diff_reports


def test_no_regression_when_metrics_unchanged():
    """Identical reports produce zero regressions."""
    a = {"models": {"roberta": {"macro_f1": 0.80, "per_class_f1": {"bug": 0.7}}}}
    b = {"models": {"roberta": {"macro_f1": 0.80, "per_class_f1": {"bug": 0.7}}}}
    summary = diff_reports(previous=a, current=b)
    assert summary.regressions == []


def test_flag_5_percent_relative_drop():
    """A >5% relative drop on macro_f1 is flagged."""
    a = {"models": {"roberta": {"macro_f1": 0.80, "per_class_f1": {}}}}
    b = {"models": {"roberta": {"macro_f1": 0.74, "per_class_f1": {}}}}  # 7.5% drop
    summary = diff_reports(previous=a, current=b)
    assert any("macro_f1" in r.metric for r in summary.regressions)


def test_dont_flag_3_percent_drop():
    """A <5% relative drop is fine."""
    a = {"models": {"roberta": {"macro_f1": 0.80, "per_class_f1": {}}}}
    b = {"models": {"roberta": {"macro_f1": 0.78, "per_class_f1": {}}}}  # 2.5% drop
    summary = diff_reports(previous=a, current=b)
    assert summary.regressions == []


def test_improvements_are_recorded():
    """A relative improvement is captured (informational)."""
    a = {"models": {"roberta": {"macro_f1": 0.70, "per_class_f1": {}}}}
    b = {"models": {"roberta": {"macro_f1": 0.80, "per_class_f1": {}}}}
    summary = diff_reports(previous=a, current=b)
    assert summary.improvements
