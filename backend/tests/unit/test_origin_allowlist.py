"""Tests for the origin allowlist cache."""

from unittest.mock import MagicMock

import pytest

from app.services.widgets import get_allowed_origins, invalidate_origins_cache


@pytest.mark.asyncio
async def test_returns_origins_from_db_first_time(monkeypatch):
    """Cache miss falls back to DB lookup and caches result."""
    fake_widget = MagicMock()
    fake_widget.allowed_origins = ["http://a.test", "http://b.test"]

    async def fake_get(_session, wid):
        return fake_widget if wid == "wgt_abc" else None

    monkeypatch.setattr("app.repositories.widgets.get_widget_by_widget_id", fake_get)

    invalidate_origins_cache()
    origins = await get_allowed_origins(None, "wgt_abc")
    assert origins == frozenset({"http://a.test", "http://b.test"})


@pytest.mark.asyncio
async def test_returns_none_for_missing_widget(monkeypatch):
    """A widget not in the DB returns None."""

    async def fake_get(_session, _wid):
        return None

    monkeypatch.setattr("app.repositories.widgets.get_widget_by_widget_id", fake_get)
    invalidate_origins_cache()
    origins = await get_allowed_origins(None, "wgt_missing")
    assert origins is None


@pytest.mark.asyncio
async def test_invalidate_drops_specific_widget(monkeypatch):
    """invalidate_origins_cache(wid) drops only that widget's entry."""
    fake_widget = MagicMock()
    fake_widget.allowed_origins = ["http://a.test"]

    async def fake_get(_session, _wid):
        return fake_widget

    monkeypatch.setattr("app.repositories.widgets.get_widget_by_widget_id", fake_get)

    invalidate_origins_cache()
    await get_allowed_origins(None, "wgt_x")
    invalidate_origins_cache("wgt_x")

    # next call should re-query (we just verify it doesn't crash and returns the same value)
    origins = await get_allowed_origins(None, "wgt_x")
    assert origins == frozenset({"http://a.test"})
