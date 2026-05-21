"""Tests for Settings — required fields, defaults, forbid-extra."""
import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


def test_settings_loads_required_fields():
    """Confirms Settings reads the env vars set by conftest."""
    s = Settings()
    assert s.vault_addr == "http://vault.test:8200"
    assert s.vault_root_token == "test-root-token"
    assert s.db_user == "test-user"


def test_settings_forbids_extra_fields(monkeypatch: pytest.MonkeyPatch):
    """Unknown env vars must be rejected — typos shouldn't silently pass."""
    monkeypatch.setenv("APP_UNKNOWN_FIELD", "x")
    with pytest.raises(ValidationError):
        Settings(unknown_field="x")  # type: ignore[call-arg]


def test_get_settings_is_cached():
    """get_settings() returns the same instance every call (lru_cache)."""
    a = get_settings()
    b = get_settings()
    assert a is b
