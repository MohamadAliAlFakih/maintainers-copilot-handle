"""Langfuse tracing init — re-exports @observe and exposes the client."""

from langfuse import Langfuse
from langfuse.decorators import observe

__all__ = ["build_langfuse_client", "observe"]


def build_langfuse_client(host: str, public_key: str, secret_key: str) -> Langfuse:
    """Builds the Langfuse client used by @observe and manual span calls."""
    return Langfuse(
        host=host,
        public_key=public_key,
        secret_key=secret_key,
    )
