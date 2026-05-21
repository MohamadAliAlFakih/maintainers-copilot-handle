"""Domain exception hierarchy mapped to HTTP status codes at the API boundary."""
from typing import ClassVar


class DomainError(Exception):
    """Base for all expected business-logic errors."""

    code: ClassVar[str] = "domain_error"
    http_status: ClassVar[int] = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """Resource lookup failed — maps to 404."""

    code = "not_found"
    http_status = 404


class PermissionDenied(DomainError):
    """Authenticated user lacks the required role — maps to 403."""

    code = "forbidden"
    http_status = 403


class AuthenticationFailed(DomainError):
    """No valid token / bad credentials — maps to 401."""

    code = "unauthenticated"
    http_status = 401


class ToolFailure(DomainError):
    """A chatbot tool failed in a way the agent should handle — maps to 502 at API."""

    code = "tool_failure"
    http_status = 502


class MemoryQuotaExceeded(DomainError):
    """User hit a memory-write quota — maps to 429."""

    code = "memory_quota"
    http_status = 429


class WidgetOriginRejected(DomainError):
    """Request origin not in widget's allowed_origins — maps to 403."""

    code = "origin_rejected"
    http_status = 403


class ValidationFailed(DomainError):
    """Semantic validation error beyond what Pydantic catches — maps to 422."""

    code = "invalid"
    http_status = 422
