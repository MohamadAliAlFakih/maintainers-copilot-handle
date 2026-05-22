"""Writes a dataset_manifest.json describing every artifact this run produced."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime


@dataclass
class ArtifactRef:
    """Reference to a single file written to MinIO."""

    name: str
    bucket: str
    object_key: str
    n_rows: int


@dataclass
class DatasetManifest:
    """Top-level manifest describing this dataset build."""

    created_at: str
    raw_issues_sha256: str
    seed: int
    splits: list[ArtifactRef]
    rag_held_out: ArtifactRef | None
    counts_per_class: dict[str, int]


def compute_raw_sha256(raw_json_bytes: bytes) -> str:
    """Returns the SHA-256 of the raw JSON bytes; used in the model card."""
    return hashlib.sha256(raw_json_bytes).hexdigest()


def build_manifest(
    raw_sha: str,
    seed: int,
    artifacts: list[ArtifactRef],
    rag_held_out: ArtifactRef | None,
    counts: dict[str, int],
) -> DatasetManifest:
    """Constructs a manifest with a UTC timestamp."""
    return DatasetManifest(
        created_at=datetime.now(UTC).isoformat(),
        raw_issues_sha256=raw_sha,
        seed=seed,
        splits=artifacts,
        rag_held_out=rag_held_out,
        counts_per_class=counts,
    )


def manifest_to_json(m: DatasetManifest) -> str:
    """Serializes manifest as pretty JSON."""
    return json.dumps(asdict(m), indent=2, default=str)
