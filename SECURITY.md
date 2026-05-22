# Security

## Redaction patterns (`app/infra/redaction.py`)

Every log line, span attribute, memory write, and chunk snapshot passes through `redact()` before leaving the service boundary.

Patterns:

| Pattern | Replacement | What it catches |
|---|---|---|
| `\b(sk\|pk\|rk)-[A-Za-z0-9]{20,}\b` | `[REDACTED:api_key]` | OpenAI/Stripe/Anthropic-style keys |
| `ghp_[A-Za-z0-9]{36,}` | `[REDACTED:github_token]` | GitHub classic PATs |
| `gho_[A-Za-z0-9]{36,}` | `[REDACTED:github_oauth]` | GitHub OAuth tokens |
| `github_pat_[A-Za-z0-9_-]{20,}` | `[REDACTED:github_pat_new]` | GitHub fine-grained PATs |
| JWT three-segment base64url | `[REDACTED:jwt]` | Any JWT in stack traces / pasted messages |
| `AKIA[0-9A-Z]{16}` | `[REDACTED:aws_access_key]` | AWS access keys |
| `://user:pass@host` | `://[REDACTED:user]:[REDACTED:pass]@host` | Basic-auth-in-URL leaks |
| Emails `x@y.com` | `x***@y.com` | Partial — keeps domain visible for triage |
| 16-digit grouped | `[REDACTED:card]` | Card-number-shaped accidents |

These were chosen because they cover the specific failure modes most likely to appear in pasted issue text: stack traces with tokens, copy-pasted .env values, URLs from production logs. They are NOT exhaustive — PII like phone numbers, IPs, or SSNs are NOT redacted. A pasted SSN would survive. **For v1 this is an accepted limitation.**

The pattern list is tested explicitly in `tests/unit/test_redaction.py`. CI failure on that test blocks merge.

## Origin allowlisting (three layers)

1. **CORS at API:** `DynamicCorsMiddleware` resolves `allowed_origins` from the DB per-request (5-min TTL cache). Non-widget routes use a static allowlist for Streamlit + dev tools.
2. **CSP `frame-ancestors`:** the embed route (`GET /widget/{id}/embed`) sets the header from the same DB-sourced list. Browser refuses to render the iframe in any unlisted parent.
3. **postMessage origin check:** the widget JS validates `event.origin` matches the configured `host_origin` before processing any incoming message.

Defense-in-depth: CORS blocks the API call; CSP blocks the iframe; postMessage blocks a parent that snuck past both.

## What we do NOT do (v1 limitations)

- We don't rate-limit `/auth/register` or `/chat/stream`. A malicious actor can spam them.
- We don't encrypt MinIO objects at rest (dev MinIO is plaintext on disk).
- We don't enforce password complexity beyond min-length 8.
- We don't have a session-revocation mechanism for already-issued JWTs (refresh-token rotation is the design pattern; it's deferred).
- We don't audit-log failed authentication attempts.

These are documented limitations, not bugs. Each has a clear path to remediation in a v2.
