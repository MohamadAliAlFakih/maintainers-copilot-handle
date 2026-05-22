"""Dynamic CORS middleware — for /widgets/{id}/* routes, allowlist comes from DB."""

import re
from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.infra.logging_setup import get_logger
from app.services.widgets import get_allowed_origins

log = get_logger(__name__)

# Static allowlist for non-widget endpoints (Streamlit, dev tools, demo host, widget bundle)
STATIC_ALLOW = {
    "http://localhost:8501",  # streamlit
    "http://localhost:9000",  # demo host (default in seed)
    "http://localhost:8080",  # widget bundle (cross-origin chat/stream calls)
    "http://localhost:5173",  # vite dev
}

# Routes that route through widget-level origin checks
_WIDGET_PATH_RE = re.compile(r"^/(widgets?|widget\.js|chat/stream)")


class DynamicCorsMiddleware(BaseHTTPMiddleware):
    """Enforces CORS using the widget's allowed_origins from the DB for widget routes,
    and a static allowlist for everything else.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Per-request: validate origin against the right allowlist; add headers on response."""
        origin = request.headers.get("origin")

        # Handle preflight (OPTIONS) directly so it never reaches a real handler
        if request.method == "OPTIONS" and origin is not None:
            allowed = await self._is_allowed(request, origin)
            if allowed:
                return self._preflight_response(origin)
            return Response(status_code=403)

        response = await call_next(request)
        if origin is not None and await self._is_allowed(request, origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin"
        return response

    async def _is_allowed(self, request: Request, origin: str) -> bool:
        """Resolves whether the origin is allowed for this path."""
        path = request.url.path

        if not _WIDGET_PATH_RE.match(path):
            return origin in STATIC_ALLOW

        widget_id = self._extract_widget_id(path) or request.headers.get("x-widget-id")
        if widget_id is None:
            return origin in STATIC_ALLOW

        factory = request.app.state.session_factory
        async with factory() as session:
            allowed = await get_allowed_origins(session, widget_id)

        if allowed is None:
            log.warning("cors.widget_not_found", widget_id=widget_id, origin=origin)
            return False
        return origin in allowed

    def _extract_widget_id(self, path: str) -> str | None:
        """Pulls widget_id from /widgets/<id>/... or /widget/<id>/..."""
        m = re.match(r"^/widgets?/([^/]+)", path)
        return m.group(1) if m else None

    def _preflight_response(self, origin: str) -> Response:
        """Standard CORS preflight response with permissive method/header lists."""
        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Widget-Id",
                "Access-Control-Max-Age": "600",
                "Vary": "Origin",
            },
        )
