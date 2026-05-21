"""Single redaction layer applied before any sensitive value leaves the service."""

import re
from re import Pattern

# Pattern list defended in SECURITY.md.
_PATTERNS: list[tuple[Pattern[str], str]] = [
    # OpenAI-style API keys (sk-, pk-, rk-)
    (re.compile(r"\b(sk|pk|rk)-[A-Za-z0-9]{20,}\b"), "[REDACTED:api_key]"),
    # GitHub classic personal access token
    (re.compile(r"ghp_[A-Za-z0-9]{36,}"), "[REDACTED:github_token]"),
    # GitHub OAuth token
    (re.compile(r"gho_[A-Za-z0-9]{36,}"), "[REDACTED:github_oauth]"),
    # GitHub new fine-grained PAT
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "[REDACTED:github_pat_new]"),
    # JWT — three base64url segments separated by dots
    (
        re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
        "[REDACTED:jwt]",
    ),
    # AWS access key
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED:aws_access_key]"),
    # Card-like 16-digit pattern (grouped or not)
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[REDACTED:card]"),
]

# Basic-auth-in-url pattern handled separately because we replace inside groups
_BASIC_AUTH_URL = re.compile(r"://([^:/\s]+):([^@/\s]+)@")

# Email pattern — partial redaction keeps first char + domain
_EMAIL = re.compile(r"\b([a-zA-Z])[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b")


def redact(text: str | None) -> str | None:
    """Replaces sensitive patterns in text with placeholders. Safe on None/empty."""
    if text is None or text == "":
        return text

    out = text

    for pat, replacement in _PATTERNS:
        out = pat.sub(replacement, out)

    out = _BASIC_AUTH_URL.sub("://[REDACTED:user]:[REDACTED:pass]@", out)

    out = _EMAIL.sub(r"\1***@\2", out)

    return out
