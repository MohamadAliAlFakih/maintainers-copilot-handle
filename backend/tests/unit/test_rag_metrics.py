"""Tests for retrieval metric helpers."""

from evals.rag._runner import compute_hit_at_k, compute_mrr_at_k


def test_hit_at_5_full_overlap():
    """When at least one ground-truth id is in the top-5, hit@5 = 1.0."""
    retrieved = ["c1", "c2", "c3", "c4", "c5"]
    truth = ["c3"]
    assert compute_hit_at_k(retrieved, truth, k=5) == 1.0


def test_hit_at_5_no_overlap():
    """No overlap returns 0.0."""
    assert compute_hit_at_k(["a", "b"], ["c"], k=5) == 0.0


def test_hit_at_5_partial_overlap():
    """Any one match counts as a hit."""
    assert compute_hit_at_k(["c1", "c5", "c9"], ["c5", "c100"], k=5) == 1.0


def test_mrr_at_10_first_position():
    """MRR is 1/1 = 1.0 when the first retrieved is correct."""
    assert compute_mrr_at_k(["c1", "c2", "c3"], ["c1"], k=10) == 1.0


def test_mrr_at_10_third_position():
    """MRR is 1/3 when the third item is the first relevant one."""
    assert abs(compute_mrr_at_k(["a", "b", "c", "d"], ["c"], k=10) - 1 / 3) < 1e-9


def test_mrr_at_10_no_hit():
    """MRR is 0 when no relevant item is in the top-k."""
    assert compute_mrr_at_k(["a", "b"], ["c"], k=10) == 0.0


def test_mrr_at_k_capped_by_k():
    """A relevant item past k contributes 0."""
    assert compute_mrr_at_k(["a", "b", "c", "d", "e"], ["e"], k=3) == 0.0
