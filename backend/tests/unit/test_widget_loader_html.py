"""Tests for the embed HTML wrapper: CSP header reflects allowed_origins."""

from unittest.mock import MagicMock

import pytest


@pytest.mark.asyncio
async def test_embed_renders_csp_from_allowed_origins(monkeypatch):
    """The CSP header lists each allowed origin in frame-ancestors."""
    from app.api.routes.widget_loader import widget_embed

    fake_widget = MagicMock()
    fake_widget.allowed_origins = ["http://localhost:9000", "https://example.com"]
    fake_widget.widget_id = "wgt_test"

    async def fake_get(_s, _wid):
        return fake_widget

    monkeypatch.setattr("app.api.routes.widget_loader.get_widget_by_widget_id", fake_get)

    fake_request = MagicMock()
    fake_request.query_params = {"host_origin": "http://localhost:9000"}

    response = await widget_embed(widget_id="wgt_test", request=fake_request, session=MagicMock())
    csp = response.headers["content-security-policy"]
    assert "frame-ancestors" in csp
    assert "http://localhost:9000" in csp
    assert "https://example.com" in csp


@pytest.mark.asyncio
async def test_embed_404_when_widget_missing(monkeypatch):
    """A missing widget raises NotFoundError."""
    from app.api.routes.widget_loader import widget_embed
    from app.domain.exceptions import NotFoundError

    async def fake_get(_s, _wid):
        return None

    monkeypatch.setattr("app.api.routes.widget_loader.get_widget_by_widget_id", fake_get)
    fake_request = MagicMock()
    fake_request.query_params = {}

    with pytest.raises(NotFoundError):
        await widget_embed(widget_id="missing", request=fake_request, session=MagicMock())
