"""Tests for the kappa helper."""

from evals.rag._kappa import compute_kappa


def test_perfect_agreement_is_1():
    """Identical scores yield kappa = 1.0."""
    human = [5, 4, 3, 2, 1]
    judge = [5, 4, 3, 2, 1]
    assert compute_kappa(human, judge) == 1.0


def test_no_agreement_close_to_0_or_negative():
    """Completely opposing scores produce kappa near 0 or negative."""
    human = [1, 1, 1, 5, 5]
    judge = [5, 5, 5, 1, 1]
    k = compute_kappa(human, judge)
    assert k < 0


def test_mixed_agreement():
    """Partial overlap gives positive but < 1.0 kappa."""
    human = [5, 4, 3, 2, 1]
    judge = [5, 4, 4, 2, 1]
    k = compute_kappa(human, judge)
    assert 0 < k < 1.0


def test_empty_returns_zero():
    """No samples returns 0 instead of crashing."""
    assert compute_kappa([], []) == 0.0
