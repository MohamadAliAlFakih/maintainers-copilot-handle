"""Tests for redaction patterns — brief requirement, CI-blocking."""

from app.infra.redaction import redact


def test_redacts_openai_style_key():
    """sk-... pattern must be redacted everywhere."""
    s = "my key is sk-abcdefghijklmnopqrstuvwxyz0123456789"
    out = redact(s)
    assert "sk-abcdefghijklmnop" not in out
    assert "[REDACTED:api_key]" in out


def test_redacts_github_classic_token():
    """ghp_... tokens must be redacted."""
    s = "ghp_abcdefghijklmnopqrstuvwxyz0123456789AB"
    assert "ghp_abcdefghijklmnop" not in redact(s)
    assert "[REDACTED:github_token]" in redact(s)


def test_redacts_github_pat_new_format():
    """github_pat_... tokens must be redacted."""
    s = "github_pat_11ABCDEFG0_long-random-string-here-1234"
    assert "github_pat_11ABCDEFG0" not in redact(s)
    assert "[REDACTED:github_pat_new]" in redact(s)


def test_redacts_aws_access_key():
    """AKIA... access keys must be redacted."""
    s = "key=AKIAIOSFODNN7EXAMPLE"
    assert "AKIAIOSFODNN7EXAMPLE" not in redact(s)
    assert "[REDACTED:aws_access_key]" in redact(s)


def test_redacts_jwt():
    """JWT-shaped strings must be redacted."""
    fake = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    assert fake not in redact(fake)
    assert "[REDACTED:jwt]" in redact(fake)


def test_redacts_basic_auth_in_url():
    """user:password@host pattern must be redacted."""
    s = "postgres://admin:hunter2@db.example.com:5432/x"
    out = redact(s)
    assert "hunter2" not in out
    assert "[REDACTED:pass]" in out


def test_partial_redacts_email():
    """Email addresses must be partially redacted (first letter + domain)."""
    s = "contact alice@example.com"
    out = redact(s)
    assert "alice@example.com" not in out
    assert "a***@example.com" in out


def test_redacts_card_number():
    """16-digit-grouped card-like numbers must be redacted."""
    s = "card 4111 1111 1111 1111"
    out = redact(s)
    assert "4111 1111 1111 1111" not in out
    assert "[REDACTED:card]" in out


def test_passthrough_safe_text():
    """Plain text without sensitive patterns should pass through unchanged."""
    s = "The user asked about FastAPI dependencies and OAuth2."
    assert redact(s) == s


def test_redact_handles_none_and_empty():
    """Redact must not crash on None or empty input."""
    assert redact("") == ""
    assert redact(None) is None  # type: ignore[arg-type]
