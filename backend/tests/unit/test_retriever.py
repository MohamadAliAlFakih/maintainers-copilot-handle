"""Tests for the RagOrchestrator wiring (mocks SQL + httpx + Groq)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.schemas.rag import RagQuery
from app.services.rag.orchestrator import RagOrchestrator


@pytest.fixture
def orchestrator(monkeypatch: pytest.MonkeyPatch):
    """Builds a RagOrchestrator with all external calls mocked."""
    groq = MagicMock()
    groq.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content="hypothetical answer body"))]
        )
    )
    http = MagicMock()
    orch = RagOrchestrator(
        groq=groq,
        groq_model_cheap="llama-3.1-8b-instant",
        prompts_dir=Path("/tmp/prompts"),
        modelserver_http=http,
    )

    monkeypatch.setattr(
        "app.services.rag.hyde._load_prompt",
        lambda _dir: "Q: {{ question }}\nA:",
    )

    return orch


@pytest.fixture
def session():
    """Mock AsyncSession (we just need the object identity for repo calls)."""
    return MagicMock()


@pytest.mark.asyncio
async def test_search_returns_reranked_hits(orchestrator, session, monkeypatch):
    """Happy path: HyDE -> embed -> hybrid -> RRF -> rerank -> top-3 hits."""

    async def fake_embed_texts(_client, texts, which="bge"):
        return [[0.1] * 384]

    monkeypatch.setattr("app.services.rag.orchestrator.embed_texts", fake_embed_texts)

    async def fake_rerank(_client, _q, passages, top_k=5):
        return [(i, 1.0 - 0.01 * i) for i in reversed(range(len(passages)))][:top_k]

    monkeypatch.setattr("app.services.rag.orchestrator.rerank_passages", fake_rerank)

    async def fake_dense(_s, _e, embedder="bge", top_k=50, source_type=None):
        return [("c1", 0.9), ("c2", 0.8), ("c3", 0.7)]

    async def fake_sparse(_s, _q, top_k=50, source_type=None):
        return [("c2", 0.95), ("c4", 0.6)]

    monkeypatch.setattr("app.services.rag.orchestrator.dense_search", fake_dense)
    monkeypatch.setattr("app.services.rag.orchestrator.sparse_search", fake_sparse)

    def make_orm_chunk(cid: str) -> MagicMock:
        m = MagicMock()
        m.chunk_id = cid
        m.text = f"text of {cid}"
        m.source_type = "doc"
        m.source_path = f"docs/{cid}.md"
        m.section_headers = []
        return m

    async def fake_get_chunks_by_ids(_s, ids):
        return {cid: make_orm_chunk(cid) for cid in ids}

    monkeypatch.setattr("app.services.rag.orchestrator.get_chunks_by_ids", fake_get_chunks_by_ids)

    ctx = await orchestrator.search(session, RagQuery(question="how do I auth?", top_k=3))
    assert len(ctx.hits) == 3
    assert ctx.hypothetical_answer.startswith("hypothetical")
    assert all(h.text.startswith("text of c") for h in ctx.hits)


@pytest.mark.asyncio
async def test_search_returns_empty_when_no_candidates(orchestrator, session, monkeypatch):
    """If dense + sparse both return empty, the orchestrator returns 0 hits cleanly."""

    async def fake_embed(_c, _t, which="bge"):
        return [[0.1] * 384]

    monkeypatch.setattr("app.services.rag.orchestrator.embed_texts", fake_embed)

    async def empty(_s, *args, **kwargs):
        return []

    monkeypatch.setattr("app.services.rag.orchestrator.dense_search", empty)
    monkeypatch.setattr("app.services.rag.orchestrator.sparse_search", empty)

    ctx = await orchestrator.search(session, RagQuery(question="x"))
    assert ctx.hits == []
