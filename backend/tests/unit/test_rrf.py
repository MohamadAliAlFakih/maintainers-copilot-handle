"""Tests for Reciprocal Rank Fusion."""

from app.services.rag.retriever import rrf_combine


def test_rrf_merges_overlapping_lists():
    """Items in both lists get a higher combined score than items in only one."""
    dense = ["A", "B", "C"]
    sparse = ["B", "D", "A"]
    merged = rrf_combine([dense, sparse], k=60)
    assert merged[0][0] in {"A", "B"}
    rankings = {item: idx for idx, (item, _score) in enumerate(merged)}
    assert rankings["A"] < rankings["C"]
    assert rankings["B"] < rankings["D"]


def test_rrf_handles_disjoint_lists():
    """When lists don't overlap, the higher-ranked items in either list come first."""
    dense = ["A", "B"]
    sparse = ["C", "D"]
    merged = rrf_combine([dense, sparse], k=60)
    items = [m[0] for m in merged]
    assert set(items) == {"A", "B", "C", "D"}
    rankings = {item: idx for idx, (item, _) in enumerate(merged)}
    assert rankings["A"] < rankings["B"]
    assert rankings["C"] < rankings["D"]


def test_rrf_empty_lists():
    """No input returns an empty list, not a crash."""
    assert rrf_combine([], k=60) == []
    assert rrf_combine([[], []], k=60) == []


def test_rrf_handles_single_list():
    """A single ranked list comes back in the same order with positive scores."""
    merged = rrf_combine([["A", "B", "C"]], k=60)
    assert [m[0] for m in merged] == ["A", "B", "C"]
    assert all(score > 0 for _, score in merged)
