"""Health endpoint — used by docker healthchecks and the smoke test."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — returns 200 if the process is alive and routes are mounted."""
    return {"status": "ok", "service": "api"}
