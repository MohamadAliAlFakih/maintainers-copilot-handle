"""Tests for the refuse-to-boot policy."""

import pytest

from app.infra.startup_checks import StartupFailure, check_settings_sanity


def test_settings_sanity_passes_with_valid_values():
    """Returns None when settings are well-formed."""
    from app.config import Settings

    s = Settings()  # uses conftest env
    check_settings_sanity(s)


def test_settings_sanity_rejects_blank_vault_token():
    """An empty vault_root_token must fail the sanity check."""
    from app.config import Settings

    s = Settings(vault_root_token="   ")  # whitespace
    with pytest.raises(StartupFailure) as excinfo:
        check_settings_sanity(s)
    assert "vault_root_token" in str(excinfo.value).lower()
