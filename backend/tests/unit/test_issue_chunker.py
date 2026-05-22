"""Tests for the resolved-issue chunker."""

from scripts.corpus._chunker_issues import chunk_issue


def test_short_issue_becomes_one_chunk():
    """An issue under the token cap is a single chunk."""
    issue = {
        "issue_number": 100,
        "title": "Crash on startup",
        "body": "Short body.",
        "best_answer": "Try X.",
    }
    chunks = chunk_issue(issue)
    assert len(chunks) == 1
    assert chunks[0].source_type == "resolved_issue"
    assert "issues/100" in chunks[0].source_path


def test_long_issue_splits_into_title_body_and_answer():
    """An issue over the cap splits into (title+body) and (best_answer)."""
    issue = {
        "issue_number": 200,
        "title": "Long one",
        "body": "Body " * 800,
        "best_answer": "Answer " * 200,
    }
    chunks = chunk_issue(issue)
    assert len(chunks) == 2
    assert "Answer" in chunks[1].text


def test_missing_best_answer_still_yields_chunk():
    """An issue with no maintainer answer still produces at least one chunk."""
    issue = {
        "issue_number": 300,
        "title": "T",
        "body": "B",
        "best_answer": None,
    }
    chunks = chunk_issue(issue)
    assert len(chunks) >= 1
