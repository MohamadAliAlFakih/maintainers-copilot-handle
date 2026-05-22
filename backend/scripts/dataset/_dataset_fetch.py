"""Async GitHub closed-issues fetcher with retries; caches raw JSON list."""

import asyncio
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.infra.logging_setup import get_logger

log = get_logger(__name__)

GITHUB_API = "https://api.github.com"


async def _fetch_page(
    client: httpx.AsyncClient, owner: str, repo: str, page: int, per_page: int = 100
) -> list[dict[str, Any]]:
    """Fetches one page of closed issues with retry on transient errors."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues"
    params = {
        "state": "closed",
        "per_page": per_page,
        "page": page,
        "sort": "created",
        "direction": "asc",
    }
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)
        ),
        reraise=True,
    ):
        with attempt:
            r = await client.get(url, params=params, timeout=30.0)
            # 403 with rate-limit headers should NOT retry
            if r.status_code == 403 and "X-RateLimit-Remaining" in r.headers:
                if r.headers["X-RateLimit-Remaining"] == "0":
                    raise RuntimeError(
                        f"GitHub rate limit exhausted. "
                        f"Resets at: {r.headers.get('X-RateLimit-Reset')}"
                    )
            r.raise_for_status()
            return r.json()
    return []  # unreachable but keeps mypy happy


async def fetch_all_closed_issues(
    token: str,
    owner: str = "pandas-dev",
    repo: str = "pandas",
    max_pages: int = 80,
) -> list[dict[str, Any]]:
    """Pages through every closed issue in the repo. Drops PRs (issues endpoint includes them)."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "handle-maintainers-copilot",
    }
    all_issues: list[dict[str, Any]] = []
    page = 1

    async with httpx.AsyncClient(headers=headers) as client:
        while page <= max_pages:
            log.info("github.fetch.page", page=page)
            batch = await _fetch_page(client, owner, repo, page)
            if not batch:
                break
            non_prs = [i for i in batch if "pull_request" not in i]
            all_issues.extend(non_prs)
            if len(batch) < 100:
                break
            page += 1
            await asyncio.sleep(0.3)

    log.info("github.fetch.done", total_issues=len(all_issues), pages=page)
    return all_issues
