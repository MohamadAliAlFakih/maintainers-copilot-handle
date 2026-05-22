"""Per-conversation chunk snapshot writer with FIFO retention of 100 conversations."""
import io
import json
from typing import Any

from minio import Minio


def write_chunk_snapshot(
    minio_client: Minio, conversation_id: str, turn_index: int, chunks: list[dict[str, Any]]
) -> None:
    """Writes the 5 retrieved chunks for one turn to MinIO under conversations/<id>/chunks/."""
    key = f"conversations/{conversation_id}/chunks/{turn_index:04d}.json"
    body = json.dumps(chunks, indent=2).encode("utf-8")
    minio_client.put_object("conversations", key, io.BytesIO(body), length=len(body))


def gc_old_conversations(minio_client: Minio, keep_latest: int = 100) -> int:
    """Lists `conversations/` prefixes and deletes all but the most recent `keep_latest`. Returns count deleted."""
    objects = list(minio_client.list_objects("conversations", prefix="", recursive=False))
    ids = sorted(
        {obj.object_name.rstrip("/").split("/")[0] for obj in objects if obj.is_dir},
        key=lambda s: s,
    )
    to_delete = ids[:-keep_latest] if len(ids) > keep_latest else []
    n = 0
    for cid in to_delete:
        for obj in minio_client.list_objects("conversations", prefix=f"{cid}/", recursive=True):
            minio_client.remove_object("conversations", obj.object_name)
            n += 1
    return n
