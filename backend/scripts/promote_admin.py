#!/usr/bin/env python
"""Promotes an existing user to admin role.

Usage (from host machine, after `docker compose up`):
    docker compose exec api uv run python /app/scripts/promote_admin.py <email>
"""
import asyncio
import sys
from pathlib import Path

# ensure backend/app is importable when run inside the container
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.domain.enums import Role  # noqa: E402
from app.infra.db import build_engine, build_session_factory  # noqa: E402
from app.repositories.audit_log import write_audit_entry  # noqa: E402
from app.services.auth.models import User  # noqa: E402


async def promote(email: str) -> None:
    """Looks up the user by email and sets role=admin."""
    settings = get_settings()
    engine = build_engine(settings.db_dsn)
    factory = build_session_factory(engine)

    async with factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            print(f"No user found with email {email}", file=sys.stderr)
            sys.exit(1)

        if user.role == Role.ADMIN.value:
            print(f"User {email} is already admin.")
            return

        user.role = Role.ADMIN.value
        await write_audit_entry(
            session,
            actor_user_id=None,  # CLI-driven; no acting user
            action="role.change",
            target_type="user",
            target_id=str(user.id),
            extra={"new_role": Role.ADMIN.value, "via": "promote_admin.py"},
        )
        await session.commit()
        print(f"Promoted {email} to admin.")

    await engine.dispose()


def main() -> None:
    """CLI entrypoint: takes one arg (the email)."""
    if len(sys.argv) != 2:
        print("Usage: promote_admin.py <email>", file=sys.stderr)
        sys.exit(2)
    asyncio.run(promote(sys.argv[1]))


if __name__ == "__main__":
    main()
