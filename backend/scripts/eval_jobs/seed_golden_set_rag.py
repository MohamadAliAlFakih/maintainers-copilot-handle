"""Samples 25 candidate questions seeded from the corpus structure.

Run inside backend:
    docker-compose exec api uv run python /app/scripts/seed_golden_set_rag.py > /tmp/rag_candidates.jsonl

Then hand-write the question/ideal_answer/ground_truth_chunk_ids for each.
"""

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config import get_settings  # noqa: E402
from app.infra.db import build_engine, build_session_factory  # noqa: E402

# Hand-pick topics that cover the major doc areas
TOPICS = [
    "JWT auth",
    "CORS configuration",
    "OAuth2 password flow",
    "Dependency injection with Depends()",
    "Pydantic model validation",
    "BackgroundTasks",
    "FileResponse / StreamingResponse",
    "WebSockets",
    "Middleware",
    "Custom exception handlers",
    "SQL database with SQLAlchemy",
    "Async ORM patterns",
    "Path parameters",
    "Query parameters",
    "Request body validation",
    "Form data and uploads",
    "Static files",
    "Testing with TestClient",
    "Async testing",
    "Lifespan events (startup/shutdown)",
    "Sub-applications and mounting",
    "OpenAPI / Swagger customization",
    "Response models",
    "Status codes",
    "Headers",
]


async def main() -> None:
    """Prints 25 candidate questions seeded from each topic + sample chunk_ids per topic."""
    settings = get_settings()
    engine = build_engine(settings.db_dsn)
    factory = build_session_factory(engine)

    async with factory() as session:
        for i, topic in enumerate(TOPICS):
            sql = text(
                """
                SELECT chunk_id, source_path, LEFT(text, 200) as snippet
                FROM chunks
                WHERE tsv @@ plainto_tsquery('english', :topic)
                ORDER BY ts_rank_cd(tsv, plainto_tsquery('english', :topic)) DESC
                LIMIT 3
                """
            )
            result = await session.execute(sql, {"topic": topic})
            candidates = [
                {"chunk_id": r.chunk_id, "source_path": r.source_path, "snippet": r.snippet}
                for r in result.all()
            ]
            print(
                json.dumps(
                    {
                        "id": f"rag-{i + 1:03d}",
                        "topic": topic,
                        "question": f"TODO: write a real question about {topic}",
                        "ideal_answer": "TODO: write a 1-2 paragraph ideal answer",
                        "candidate_chunks": candidates,
                        "ground_truth_chunk_ids": ["TODO: pick from candidate_chunks"],
                        "notes": "TODO: human verification notes",
                    }
                )
            )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
