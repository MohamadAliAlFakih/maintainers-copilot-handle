"""Tests for the GitHub-label -> 4-class mapping."""

from scripts.dataset._dataset_labels import LabelMappingResult, map_labels_to_class


def test_single_bug_label_maps_to_bug():
    """A single 'bug' label produces class 'bug'."""
    r = map_labels_to_class(["bug"])
    assert r == LabelMappingResult(label="bug", conflict=False, dropped=False)


def test_enhancement_maps_to_feature():
    """'enhancement' is an alias for 'feature'."""
    r = map_labels_to_class(["enhancement"])
    assert r.label == "feature"


def test_documentation_maps_to_docs():
    """'documentation' is an alias for 'docs'."""
    r = map_labels_to_class(["documentation"])
    assert r.label == "docs"


def test_answered_maps_to_question():
    """'answered' is an alias for 'question'."""
    r = map_labels_to_class(["answered"])
    assert r.label == "question"


def test_unknown_labels_drop():
    """Labels that don't map to any class produce a dropped result."""
    r = map_labels_to_class(["good first issue", "help wanted"])
    assert r.dropped is True
    assert r.label is None


def test_conflicting_labels_drop():
    """Multiple labels mapping to different classes produce a conflict (dropped)."""
    r = map_labels_to_class(["bug", "feature"])
    assert r.conflict is True
    assert r.dropped is True
    assert r.label is None


def test_unknown_alongside_known_uses_known():
    """An unknown label paired with one known label uses the known label."""
    r = map_labels_to_class(["good first issue", "bug"])
    assert r.label == "bug"
    assert r.dropped is False


def test_empty_labels_drop():
    """Empty label list produces a dropped result."""
    r = map_labels_to_class([])
    assert r.dropped is True
