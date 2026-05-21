"""Tests for the model card writer."""

import hashlib

from scripts._classifier_card import compute_weights_sha, render_model_card
from scripts._classifier_eval import EvalReport


def test_compute_weights_sha_matches_expected():
    """SHA-256 of a known byte sequence matches hashlib's output."""
    data = b"some-bytes"
    expected = hashlib.sha256(data).hexdigest()
    assert compute_weights_sha(data) == expected


def test_render_model_card_includes_all_required_fields():
    """The rendered card includes architecture, hyperparams, hashes, and metrics."""
    report = EvalReport(
        accuracy=0.85,
        macro_f1=0.82,
        per_class_f1={"bug": 0.84, "feature": 0.80, "docs": 0.78, "question": 0.86},
        confusion_matrix=[[20, 1, 0, 1], [2, 18, 0, 1], [0, 1, 15, 0], [1, 0, 0, 19]],
        p50_latency_ms=45.0,
        p95_latency_ms=92.0,
    )
    card = render_model_card(
        architecture="roberta-base",
        hyperparams={"lr": 2e-5, "batch_size": 16, "epochs": 3},
        weights_sha="deadbeef" * 8,
        training_data_hash="cafef00d" * 8,
        eval_report=report,
    )
    assert "roberta-base" in card
    assert "deadbeef" in card
    assert "cafef00d" in card
    assert "0.82" in card
    assert "bug" in card and "0.84" in card
