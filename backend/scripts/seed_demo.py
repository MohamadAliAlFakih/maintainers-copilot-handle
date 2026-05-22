"""Demo seed: creates an admin user + a 'wgt_demo' widget on first boot.

Run inside backend (idempotent — no-ops if already seeded):
    docker compose exec api uv run python /app/scripts/seed_demo.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi_users.password import PasswordHelper  # type: ignore  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.domain.enums import Role  # noqa: E402
from app.infra.db import build_engine, build_session_factory  # noqa: E402
from app.infra.logging_setup import configure_logging, get_logger  # noqa: E402
from app.repositories.widgets import get_widget_by_widget_id  # noqa: E402
from app.services.auth.models import User  # noqa: E402
from app.services.widgets import Widget  # noqa: E402

log = get_logger(__name__)

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin-demo-password-change-me"  # noqa: S105
DEMO_WIDGET_ID = "wgt_demo"


async def main() -> None:
    """Seeds admin + demo widget if absent."""
    configure_logging()
    settings = get_settings()
    engine = build_engine(settings.db_dsn)
    factory = build_session_factory(engine)

    async with factory() as session:
        # ---- admin user ----
        result = await session.execute(select(User).where(User.email == ADMIN_EMAIL))
        admin = result.scalar_one_or_none()
        if admin is None:
            helper = PasswordHelper()
            hashed = helper.hash(ADMIN_PASSWORD)
            admin = User(
                email=ADMIN_EMAIL,
                hashed_password=hashed,
                is_active=True,
                is_verified=True,
                is_superuser=False,
                role=Role.ADMIN.value,
            )
            session.add(admin)
            await session.flush()
            log.info("seed_demo.admin_created", email=ADMIN_EMAIL)
        else:
            if admin.role != Role.ADMIN.value:
                admin.role = Role.ADMIN.value
                log.info("seed_demo.admin_promoted", email=ADMIN_EMAIL)

        # ---- demo widget ----
        # Both origins are required: :9000 is the demo host page, :8080 is the
        # React widget bundle the api iframe embeds. Without both the CSP
        # frame-ancestors blocks the embed chain.
        DEMO_ORIGINS = ["http://localhost:9000", "http://localhost:8080"]
        widget = await get_widget_by_widget_id(session, DEMO_WIDGET_ID)
        if widget is None:
            widget = Widget(
                widget_id=DEMO_WIDGET_ID,
                name="Demo widget",
                allowed_origins=DEMO_ORIGINS,
                theme={"primary_color": "#4F46E5", "position": "bottom-right"},
                greeting="Hi! Ask me anything about pandas.",
                enabled_tools=[
                    "classify_issue",
                    "extract_entities",
                    "summarize_thread",
                    "rag_search",
                ],
                created_by_user_id=admin.id,
            )
            session.add(widget)
            await session.flush()
            log.info("seed_demo.widget_created", widget_id=DEMO_WIDGET_ID)
        else:
            # Keep allowed_origins in sync even if the widget was already seeded.
            if set(widget.allowed_origins) != set(DEMO_ORIGINS):
                widget.allowed_origins = DEMO_ORIGINS
                log.info("seed_demo.widget_origins_updated", widget_id=DEMO_WIDGET_ID)
            else:
                log.info("seed_demo.widget_already_present", widget_id=DEMO_WIDGET_ID)

        await session.commit()

    await engine.dispose()
    print(f"seed complete: admin={ADMIN_EMAIL}, widget_id={DEMO_WIDGET_ID}")


if __name__ == "__main__":
    asyncio.run(main())
