"""User-self endpoints."""

from fastapi import APIRouter, Depends

from app.api.dependencies import current_active_user
from app.domain.schemas.user import UserRead
from app.services.auth.models import User

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def get_me(user: User = Depends(current_active_user)) -> User:
    """Returns the authenticated user's public profile (no password hash)."""
    return user
