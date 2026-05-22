"""One-shot dataset builder: fetch GitHub issues, map labels, split, push to MinIO.

Run inside the backend container:
    docker compose exec api uv run python /app/scripts/fetch_dataset.py
"""

import asyncio
import io
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.infra.logging_setup import configure_logging, get_logger  # noqa: E402
from app.infra.minio import build_minio_client  # noqa: E402
from app.infra.vault import VaultClient  # noqa: E402
from scripts.dataset._dataset_fetch import fetch_all_closed_issues  # noqa: E402
from scripts.dataset._dataset_labels import map_labels_to_class  # noqa: E402
from scripts.dataset._dataset_manifest import (  # noqa: E402
    ArtifactRef,
    build_manifest,
    compute_raw_sha256,
    manifest_to_json,
)
from scripts.dataset._dataset_splits import HeldOutRagSlice, SplitConfig, build_splits  # noqa: E402

log = get_logger(__name__)


def _rows_from_raw(raw: list[dict]) -> pd.DataFrame:
    """Flattens raw GitHub issue JSON to a tabular row with mapped class."""
    rows = []
    dropped = 0
    for issue in raw:
        labels = [lbl["name"] for lbl in issue.get("labels", [])]
        mapping = map_labels_to_class(labels)
        if mapping.dropped:
            dropped += 1
            continue
        rows.append(
            {
                "issue_number": issue["number"],
                "title": issue.get("title") or "",
                "body": (issue.get("body") or "")[:8000],
                "labels": labels,
                "class": mapping.label,
                "closed_at": pd.Timestamp(issue["closed_at"]),
                "user": (issue.get("user") or {}).get("login"),
            }
        )
    log.info("dataset.rows_built", n_rows=len(rows), n_dropped=dropped)
    return pd.DataFrame(rows)


def _upload_parquet(client, bucket: str, key: str, df: pd.DataFrame) -> ArtifactRef:
    """Writes a DataFrame to MinIO as parquet and returns an artifact ref."""
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    client.put_object(bucket, key, buf, length=buf.getbuffer().nbytes)
    return ArtifactRef(name=key.split("/")[-1], bucket=bucket, object_key=key, n_rows=len(df))


async def _main() -> None:
    """Main async entrypoint."""
    configure_logging()
    settings = get_settings()

    minio_client = build_minio_client(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )

    # Idempotent skip: if MinIO already has the manifest, the dataset is already fetched.
    from minio.error import S3Error

    try:
        minio_client.stat_object("dataset", "manifest.json")
        log.info("dataset.skip", reason="MinIO already has dataset/manifest.json")
        return
    except S3Error:
        pass

    vault = VaultClient(addr=settings.vault_addr, token=settings.vault_root_token)
    secrets = vault.load_all_secrets()
    if "placeholder" in secrets.github_pat:
        log.error("dataset.refuse", reason="github PAT is still placeholder; set it in Vault first")
        sys.exit(1)

    log.info("dataset.fetch.begin")
    raw = await fetch_all_closed_issues(secrets.github_pat)
    raw_bytes = json.dumps(raw).encode("utf-8")
    raw_sha = compute_raw_sha256(raw_bytes)
    log.info("dataset.fetch.done", n_raw=len(raw), sha=raw_sha[:12])

    # cache the raw json in MinIO so we don't re-hit the API
    minio_client.put_object(
        "dataset",
        f"raw/pandas_issues_{raw_sha}.json",
        io.BytesIO(raw_bytes),
        length=len(raw_bytes),
    )

    df = _rows_from_raw(raw)
    counts = df["class"].value_counts().to_dict()
    log.info("dataset.class_counts", **counts)

    splits = build_splits(
        df,
        SplitConfig(test_frac=0.2, val_frac=0.1, seed=42),
        HeldOutRagSlice(question_frac=0.1),
    )

    artifacts = [
        _upload_parquet(minio_client, "dataset", "splits/train.parquet", splits.train),
        _upload_parquet(minio_client, "dataset", "splits/val.parquet", splits.val),
        _upload_parquet(minio_client, "dataset", "splits/test.parquet", splits.test),
    ]
    rag_ref = None
    if splits.rag_held_out is not None:
        rag_ref = _upload_parquet(
            minio_client, "dataset", "splits/rag_held_out.parquet", splits.rag_held_out
        )

    manifest = build_manifest(raw_sha, 42, artifacts, rag_ref, counts)
    manifest_json = manifest_to_json(manifest)
    manifest_bytes = manifest_json.encode("utf-8")
    minio_client.put_object(
        "dataset",
        "manifest.json",
        io.BytesIO(manifest_bytes),
        length=len(manifest_bytes),
    )

    # also dump locally so it can be committed
    Path("dataset_manifest.json").write_text(manifest_json)
    log.info("dataset.done")


def main() -> None:
    """CLI entrypoint."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
