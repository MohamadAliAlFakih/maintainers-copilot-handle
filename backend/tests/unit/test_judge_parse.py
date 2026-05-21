"""Tests for the judge response parser."""

from evals.rag._judge import JudgeScore, parse_judge_response


def test_parses_clean_response():
    """Standard format parses to a JudgeScore."""
    raw = "faithfulness: 4\nanswer_relevancy: 5"
    s = parse_judge_response(raw)
    assert s == JudgeScore(faithfulness=4, answer_relevancy=5)


def test_parses_response_with_extra_text():
    """Tolerates a preamble like 'Here are the scores:'."""
    raw = "Here are the scores:\n\nfaithfulness: 3\nanswer_relevancy: 4\n\nDone."
    s = parse_judge_response(raw)
    assert s == JudgeScore(faithfulness=3, answer_relevancy=4)


def test_returns_none_on_missing_field():
    """Missing one of the two fields returns None."""
    raw = "faithfulness: 4"
    assert parse_judge_response(raw) is None


def test_clamps_out_of_range_to_none():
    """Scores outside 1..5 are rejected as invalid."""
    raw = "faithfulness: 9\nanswer_relevancy: 0"
    assert parse_judge_response(raw) is None


def test_returns_none_on_empty():
    """Empty input returns None."""
    assert parse_judge_response("") is None
