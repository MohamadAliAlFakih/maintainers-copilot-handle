"""Online artifacts-loader: pushes data-pipeline output into MinIO + pgvector.

Reads from `/data` (host-mounted ./data folder) and is fully idempotent:
- classifier: skip if MinIO has model_card.md for the model
- rag chunks: skip if the chunks table already has rows

Run inside the backend container:
    docker compose up artifacts-loader

CLI:
    uv run python -m scripts.loader.load_artifacts
"""

import asyncio
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from minio.error import S3Error
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config import get_settings  # noqa: E402
from app.infra.db import build_engine, build_session_factory  # noqa: E402
from app.infra.logging_setup import configure_logging, get_logger  # noqa: E402
from app.infra.minio import build_minio_client  # noqa: E402
from app.repositories.chunks import count_chunks  # noqa: E402

log = get_logger(__name__)

DATA_ROOT = Path("/data")
CLASSIFIER_DIR = DATA_ROOT / "artifacts" / "classifier"
RAG_DIR = DATA_ROOT / "artifacts" / "rag"


def _load_classifier(minio_client) -> None:
    """Push every classifier/<MODEL_NAME>/{model.safetensors,model_card.md,eval_report.json} to MinIO."""
    if not CLASSIFIER_DIR.exists():
        log.warning("loader.classifier.skip", reason=f"no {CLASSIFIER_DIR}")
        return

    for model_dir in CLASSIFIER_DIR.iterdir():
        if not model_dir.is_dir():
            continue
        model_name = model_dir.name
        prefix = f"classifier/{model_name}"

        # Idempotent skip
        try:
            minio_client.stat_object("models", f"{prefix}/model_card.md")
            log.info("loader.classifier.skip", model=model_name, reason="already in MinIO")
            continue
        except S3Error:
            pass

        for filename in ("model.safetensors", "model_card.md", "eval_report.json"):
            src = model_dir / filename
            if not src.exists():
                log.warning("loader.classifier.missing", model=model_name, file=filename)
                continue
            data = src.read_bytes()
            minio_client.put_object(
                "models", f"{prefix}/{filename}", io.BytesIO(data), length=len(data)
            )
            log.info(
                "loader.classifier.upload",
                model=model_name, file=filename, bytes=len(data),
            )


async def _load_rag(session_factory) -> None:
    """Bulk-insert chunks + both embeddings into pgvector if the table is empty."""
    if not RAG_DIR.exists():
        log.warning("loader.rag.skip", reason=f"no {RAG_DIR}")
        return

    chunks_path = RAG_DIR / "chunks.parquet"
    bge_path = RAG_DIR / "bge.npy"
    minilm_path = RAG_DIR / "minilm.npy"
    if not (chunks_path.exists() and bge_path.exists() and minilm_path.exists()):
        log.error(
            "loader.rag.missing_files",
            chunks=chunks_path.exists(),
            bge=bge_path.exists(),
            minilm=minilm_path.exists(),
        )
        return

    async with session_factory() as session:
        existing = await count_chunks(session)
        if existing > 0:
            log.info("loader.rag.skip", reason=f"chunks table has {existing} rows")
            return

        df = pd.read_parquet(chunks_path)
        bge = np.load(bge_path)
        minilm = np.load(minilm_path)
        if len(df) != bge.shape[0] or len(df) != minilm.shape[0]:
            log.error(
                "loader.rag.length_mismatch",
                chunks=len(df), bge=bge.shape[0], minilm=minilm.shape[0],
            )
            sys.exit(1)

        log.info("loader.rag.begin", n_chunks=len(df))

        # pgvector via asyncpg wants the vector as a string literal "[v1,v2,...]"
        def vec_lit(arr: np.ndarray) -> str:
            return "[" + ",".join(repr(float(x)) for x in arr) + "]"

        # Bulk-insert in batches with a single INSERT … VALUES per batch for speed.
        BATCH = 500
        sql = text(
            """
            INSERT INTO chunks (
                chunk_id, text, source_type, source_path,
                section_headers, version_tag,
                embedding_bge, embedding_minilm, tsv
            ) VALUES (
                :chunk_id, :text, :source_type, :source_path,
                :section_headers, :version_tag,
                CAST(:bge AS vector), CAST(:minilm AS vector),
                to_tsvector('english', :text)
            )
            """
        )

        rows = df.to_dict(orient="records")
        for i in range(0, len(rows), BATCH):
            batch = rows[i : i + BATCH]
            params = [
                {
                    "chunk_id": r["chunk_id"],
                    "text": r["text"],
                    "source_type": r["source_type"],
                    "source_path": r["source_path"],
                    "section_headers": list(r["section_headers"]),
                    "version_tag": r["version_tag"],
                    "bge": vec_lit(bge[i + j]),
                    "minilm": vec_lit(minilm[i + j]),
                }
                for j, r in enumerate(batch)
            ]
            for p in params:
                await session.execute(sql, p)
            await session.commit()
            log.info("loader.rag.batch", inserted=min(i + BATCH, len(rows)), total=len(rows))

        log.info("loader.rag.done", inserted=len(rows))


async def _main() -> None:
    configure_logging()
    settings = get_settings()

    minio_client = build_minio_client(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )
    _load_classifier(minio_client)

    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)
    try:
        await _load_rag(session_factory)
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
