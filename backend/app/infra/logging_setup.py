"""structlog setup with a redaction processor and trace-id correlation."""
import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.infra.redaction import redact


def _redact_processor(_logger: Any, _name: str, event_dict: EventDict) -> EventDict:
    """Redacts sensitive values in every log line before output."""
    for key, value in list(event_dict.items()):
        if isinstance(value, str):
            event_dict[key] = redact(value)
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    """Initializes structlog + stdlib logging with JSON output to stdout."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact_processor,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Returns a bound structlog logger; convenience over structlog.get_logger()."""
    return structlog.get_logger(name)
