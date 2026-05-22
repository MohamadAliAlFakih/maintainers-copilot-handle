"""Samples 25 candidate issues from the dataset for hand-labeling.

Run inside backend:
    docker-compose exec api uv run python /app/scripts/seed_golden_set_classification.py > /tmp/candidates.jsonl

Then hand-verify each row's `class` and write a curated golden_set.jsonl to backend/evals/classification/.
"""

import io
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.infra.minio import build_minio_client  # noqa: E402

PER_CLASS = {"bug": 7, "feature": 7, "docs": 6, "question": 5}
SEED = 42


def main() -> None:
    """Samples candidates from the test split (never trained on)."""
    settings = get_settings()
    minio_client = build_minio_client(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )

    # We sample candidates from the TEST split — these issues were never trained on.
    # The hand-curated set must STILL be verified by a human, but starting from test is fine.
    resp = minio_client.get_object("dataset", "splits/test.parquet")
    try:
        df = pd.read_parquet(io.BytesIO(resp.read()))
    finally:
        resp.close()
        resp.release_conn()

    rng = pd.Series(range(len(df))).sample(frac=1, random_state=SEED).index.tolist()
    df = df.loc[rng].reset_index(drop=True)

    out = []
    for cls, n in PER_CLASS.items():
        rows = df[df["class"] == cls].head(n)
        for _, r in rows.iterrows():
            out.append(
                {
                    "issue_number": int(r["issue_number"]),
                    "true_label": r["class"],
                    "issue_text": f"{r['title']}\n\n{r['body'][:2000]}",
                    "notes": "VERIFY: confirm label is correct before committing",
                }
            )

    for row in out:
        print(json.dumps(row))


if __name__ == "__main__":
    main()
