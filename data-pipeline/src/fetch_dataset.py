"""Fetch pandas-dev/pandas closed issues, map labels, build splits, write to data/raw/dataset/.

Run from the data-pipeline directory:
    GITHUB_TOKEN=<your_pat> uv run python -m src.fetch_dataset
"""

import argparse
import asyncio
import io
import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd

from src._github import fetch_all_closed_issues
from src._labels import map_labels_to_class
from src._manifest import (
    ArtifactRef,
    build_manifest,
    compute_raw_sha256,
    manifest_to_json,
)
from src._splits import HeldOutRagSlice, SplitConfig, build_splits

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "data" / "raw" / "dataset"


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
    log.info("rows built: %d kept, %d dropped", len(rows), dropped)
    return pd.DataFrame(rows)


def _write_parquet(df: pd.DataFrame, path: Path) -> ArtifactRef:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return ArtifactRef(name=path.name, path=str(path.relative_to(REPO_ROOT)), n_rows=len(df))


async def _main(out_dir: Path, force: bool) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    manifest_path = out_dir / "manifest.json"
    if manifest_path.exists() and not force:
        log.info("skip: %s already exists (use --force to overwrite)", manifest_path)
        return

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_PAT")
    if not token:
        log.error("GITHUB_TOKEN (or GH_PAT) env var is required")
        sys.exit(1)

    log.info("fetching closed issues from pandas-dev/pandas")
    raw = await fetch_all_closed_issues(token)
    raw_bytes = json.dumps(raw).encode("utf-8")
    raw_sha = compute_raw_sha256(raw_bytes)
    log.info("fetched %d issues (sha=%s)", len(raw), raw_sha[:12])

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "raw").mkdir(exist_ok=True)
    (out_dir / "raw" / f"pandas_issues_{raw_sha[:12]}.json").write_bytes(raw_bytes)

    df = _rows_from_raw(raw)
    if df.empty:
        log.error(
            "no rows kept — all %d issues were dropped by the label mapper; "
            "inspect raw/pandas_issues_%s.json and adjust src/_labels.py",
            len(raw), raw_sha[:12],
        )
        sys.exit(1)
    counts = df["class"].value_counts().to_dict()
    log.info("class counts: %s", counts)

    splits = build_splits(
        df,
        SplitConfig(test_frac=0.2, val_frac=0.1, seed=42),
        HeldOutRagSlice(question_frac=0.1),
    )

    artifacts = [
        _write_parquet(splits.train, out_dir / "splits" / "train.parquet"),
        _write_parquet(splits.val, out_dir / "splits" / "val.parquet"),
        _write_parquet(splits.test, out_dir / "splits" / "test.parquet"),
    ]
    rag_ref = None
    if splits.rag_held_out is not None:
        rag_ref = _write_parquet(
            splits.rag_held_out, out_dir / "splits" / "rag_held_out.parquet"
        )

    manifest = build_manifest(raw_sha, 42, artifacts, rag_ref, counts)
    manifest_path.write_text(manifest_to_json(manifest))
    log.info("wrote %s", manifest_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    asyncio.run(_main(args.out, args.force))


if __name__ == "__main__":
    main()
