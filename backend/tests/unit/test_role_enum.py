"""Tests for the Role enum."""

import pytest

from app.domain.enums import Role


def test_role_has_user_and_admin():
    """Role enum exposes USER and ADMIN exactly."""
    assert Role.USER.value == "user"
    assert Role.ADMIN.value == "admin"


def test_role_from_string():
    """Role.from_string parses valid values and rejects invalid ones."""
    assert Role("user") == Role.USER
    assert Role("admin") == Role.ADMIN
    with pytest.raises(ValueError):
        Role("superuser")


def test_role_is_serializable_as_string():
    """Role values are plain strings so they serialize cleanly in JSON/DB."""
    assert str(Role.USER.value) == "user"
