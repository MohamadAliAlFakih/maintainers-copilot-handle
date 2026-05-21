"""Tests for the LLM classifier prompt-and-parse logic."""
from app.infra.llm_classifier import parse_llm_label


def test_parses_clean_label():
    """A clean single-word response is parsed."""
    assert parse_llm_label("bug") == "bug"


def test_parses_label_with_whitespace_and_punctuation():
    """Extra whitespace and a trailing period are stripped."""
    assert parse_llm_label("  bug.\n") == "bug"
    assert parse_llm_label("Feature\n") == "feature"


def test_parses_label_inside_a_sentence():
    """A label embedded in 'LABEL: ' style is extracted."""
    assert parse_llm_label("LABEL: docs") == "docs"


def test_returns_none_on_invalid():
    """Anything that doesn't match the 4 classes returns None (caller decides)."""
    assert parse_llm_label("maybe a bug?") is None
    assert parse_llm_label("xyz") is None
