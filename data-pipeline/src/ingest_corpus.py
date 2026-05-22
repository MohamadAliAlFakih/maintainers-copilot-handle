"""Chunk pandas docs + held-out issues, embed with BGE+MiniLM, save to data/artifacts/rag/.

Run from the data-pipeline directory:
    uv run python -m src.ingest_corpus
"""

import argparse
import io
import json
import logging
import tarfile
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from src._chunker import Chunk, chunk_issue, chunk_markdown, chunk_rst

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW = REPO_ROOT / "data" / "raw"
DEFAULT_OUT = REPO_ROOT / "data" / "artifacts" / "rag"

BGE_MODEL = "BAAI/bge-small-en-v1.5"
MINILM_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _docs_to_chunks(tar_path: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    tar_bytes = tar_path.read_bytes()
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            f = tar.extractfile(member)
            if f is None:
                continue
            raw = f.read().decode("utf-8", errors="replace")
            name = member.name
            if name.endswith(".md"):
                chunks.extend(chunk_markdown(raw, source_path=name))
            elif name.endswith(".rst"):
                chunks.extend(chunk_rst(raw, source_path=name))
    return chunks


def _issues_to_chunks(df: pd.DataFrame) -> list[Chunk]:
    chunks: list[Chunk] = []
    for row in df.itertuples(index=False):
        chunks.extend(
            chunk_issue(
                {
                    "issue_number": int(row.issue_number),
                    "title": row.title,
                    "body": row.body,
                    "best_answer": row.body,  # v1: body doubles as answer source
                }
            )
        )
    return chunks


def _embed(model_name: str, texts: list[str], batch_size: int = 64) -> np.ndarray:
    log.info("loading %s", model_name)
    model = SentenceTransformer(model_name)
    log.info("encoding %d chunks with %s", len(texts), model_name)
    arr = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return arr.astype(np.float32)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    manifest_path = args.out / "manifest.json"
    if manifest_path.exists() and not args.force:
        log.info("skip: %s exists (use --force to overwrite)", manifest_path)
        return

    args.out.mkdir(parents=True, exist_ok=True)

    docs_tar = args.raw / "docs" / "pandas_docs.tar.gz"
    rag_held_out = args.raw / "dataset" / "splits" / "rag_held_out.parquet"

    all_chunks: list[Chunk] = []
    if docs_tar.exists():
        doc_chunks = _docs_to_chunks(docs_tar)
        log.info("docs chunked: %d", len(doc_chunks))
        all_chunks.extend(doc_chunks)
    else:
        log.warning("no docs tarball at %s", docs_tar)

    if rag_held_out.exists():
        issues_df = pd.read_parquet(rag_held_out)
        issue_chunks = _issues_to_chunks(issues_df)
        log.info("issues chunked: %d", len(issue_chunks))
        all_chunks.extend(issue_chunks)
    else:
        log.warning("no rag_held_out at %s", rag_held_out)

    if not all_chunks:
        log.error("no chunks produced; aborting")
        return

    df = pd.DataFrame([asdict(c) for c in all_chunks])
    chunks_path = args.out / "chunks.parquet"
    df.to_parquet(chunks_path, index=False)
    log.info("wrote %s (%d rows)", chunks_path, len(df))

    texts = [c.text for c in all_chunks]
    bge_arr = _embed(BGE_MODEL, texts)
    np.save(args.out / "bge.npy", bge_arr)
    log.info("wrote bge.npy shape=%s", bge_arr.shape)

    minilm_arr = _embed(MINILM_MODEL, texts)
    np.save(args.out / "minilm.npy", minilm_arr)
    log.info("wrote minilm.npy shape=%s", minilm_arr.shape)

    manifest = {
        "n_chunks": len(all_chunks),
        "n_doc_chunks": sum(1 for c in all_chunks if c.source_type == "doc"),
        "n_issue_chunks": sum(1 for c in all_chunks if c.source_type == "resolved_issue"),
        "embedding_models": {
            "bge": {"name": BGE_MODEL, "dim": int(bge_arr.shape[1])},
            "minilm": {"name": MINILM_MODEL, "dim": int(minilm_arr.shape[1])},
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    log.info("wrote %s", manifest_path)


if __name__ == "__main__":
    main()
