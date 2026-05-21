"""Placeholder for custom auth endpoints; the bulk of routes are mounted in main.py."""

from fastapi import APIRouter

router = APIRouter()
# Currently empty — auth/login/register/logout routes come from fastapi-users.
# Custom endpoints (e.g., password change) will land here in later plans.
