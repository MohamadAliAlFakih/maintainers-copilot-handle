"""Tests for the domain exception hierarchy."""

import pytest

from app.domain.exceptions import (
    AuthenticationFailed,
    DomainError,
    MemoryQuotaExceeded,
    NotFoundError,
    PermissionDenied,
    ToolFailure,
    ValidationFailed,
    WidgetOriginRejected,
)


def test_domain_error_subclass_structure():
    """All domain errors expose code, http_status, and message."""
    e = NotFoundError("user does not exist")
    assert isinstance(e, DomainError)
    assert e.code == "not_found"
    assert e.http_status == 404
    assert e.message == "user does not exist"


def test_each_subclass_has_correct_http_status():
    """Each named exception maps to the documented HTTP status."""
    assert NotFoundError("x").http_status == 404
    assert PermissionDenied("x").http_status == 403
    assert AuthenticationFailed("x").http_status == 401
    assert ToolFailure("x").http_status == 502
    assert MemoryQuotaExceeded("x").http_status == 429
    assert WidgetOriginRejected("x").http_status == 403
    assert ValidationFailed("x").http_status == 422


def test_domain_error_is_raisable():
    """Domain errors behave like normal Python exceptions."""
    with pytest.raises(NotFoundError) as excinfo:
        raise NotFoundError("nope")
    assert excinfo.value.message == "nope"
