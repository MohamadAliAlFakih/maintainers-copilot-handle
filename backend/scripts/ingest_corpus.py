"""End-to-end corpus ingest: pull docs + held-out issues from MinIO, chunk, embed, insert.

Run inside backend container:
    docker compose exec api uv run python /app/scripts/ingest_corpus.py
"""

import asyncio
import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.infra.db import build_engine, build_session_factory  # noqa: E402
from app.infra.logging_setup import configure_logging, get_logger  # noqa: E402
from app.infra.minio import build_minio_client  # noqa: E402
from app.repositories.chunks import count_chunks, delete_all_chunks  # noqa: E402
from scripts._ingest_pipeline import ingest_all  # noqa: E402

log = get_logger(__name__)


def _read_bytes(client, bucket: str, key: str) -> bytes:
    """Pulls a MinIO object into memory."""
    resp = client.get_object(bucket, key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()


async def _main() -> None:
    """Ingestion orchestrator."""
    configure_logging()
    settings = get_settings()

    minio_client = build_minio_client(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )

    log.info("ingest.docs.pull")
    docs_bytes = _read_bytes(minio_client, "corpus", "raw/pandas_docs.tar.gz")

    log.info("ingest.issues.pull")
    issues_bytes = _read_bytes(minio_client, "dataset", "splits/rag_held_out.parquet")
    issues_df = pd.read_parquet(io.BytesIO(issues_bytes))

    engine = build_engine(settings.db_dsn)
    factory = build_session_factory(engine)
    async with factory() as session:
        deleted = await delete_all_chunks(session)
        await session.commit()
        log.info("ingest.wiped", deleted=deleted)

    async with factory() as session:
        total = await ingest_all(session, docs_bytes, issues_df)
        log.info("ingest.done", total_chunks=total)
        post_count = await count_chunks(session)
        log.info("ingest.verify", row_count=post_count)
        assert post_count == total, "row count mismatch"

    await engine.dispose()


def main() -> None:
    """CLI entrypoint."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
