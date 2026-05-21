"""Tests for the classifier loader's SHA-check refusal."""
import hashlib

import pytest

from app.infra.classifier_loader import (
    WeightsShaMismatch,
    extract_weights_sha_from_card,
    verify_weights_sha,
)


def test_extract_weights_sha_from_card_parses_backtick_value():
    """Extracts the SHA from a card line like '- **weights_sha256:** `abc...`'."""
    card = (
        "# header\n"
        "## Hashes\n"
        "- **weights_sha256:** `deadbeef` \n"
        "- **training_data_hash:** `cafef00d`\n"
    )
    assert extract_weights_sha_from_card(card) == "deadbeef"


def test_verify_weights_sha_passes_on_match():
    """When the actual SHA matches, verify returns None."""
    data = b"abcdef"
    expected = hashlib.sha256(data).hexdigest()
    verify_weights_sha(data, expected_sha=expected)  # no raise


def test_verify_weights_sha_raises_on_mismatch():
    """Mismatch raises WeightsShaMismatch with both hashes in the message."""
    with pytest.raises(WeightsShaMismatch) as excinfo:
        verify_weights_sha(b"abcdef", expected_sha="0" * 64)
    msg = str(excinfo.value)
    assert "0000" in msg
    assert hashlib.sha256(b"abcdef").hexdigest()[:8] in msg
