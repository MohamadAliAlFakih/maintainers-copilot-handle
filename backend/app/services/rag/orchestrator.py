"""End-to-end RAG retrieval: HyDE -> embed -> hybrid -> RRF -> rerank."""

from pathlib import Path

import httpx
from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.schemas.rag import RagAnswerContext, RagHit, RagQuery
from app.infra.modelserver_client import embed_texts, rerank_passages
from app.infra.tracing import observe
from app.repositories.chunks import dense_search, get_chunks_by_ids, sparse_search
from app.services.rag.hyde import generate_hypothetical_answer
from app.services.rag.retriever import rrf_combine

from app.infra.logging_setup import get_logger

log = get_logger(__name__)


class RagOrchestrator:
    """Holds the dependencies needed for one end-to-end RAG query."""

    def __init__(
        self,
        groq: AsyncGroq,
        groq_model_cheap: str,
        prompts_dir: Path,
        modelserver_http: httpx.AsyncClient,
    ) -> None:
        self._groq = groq
        self._groq_model = groq_model_cheap
        self._prompts_dir = prompts_dir
        self._http = modelserver_http

    @observe(name="rag.search")
    async def search(self, session: AsyncSession, query: RagQuery) -> RagAnswerContext:
        """Runs HyDE -> hybrid retrieval -> RRF -> cross-encoder rerank. Returns top_k hits."""
        # ---- HyDE ----
        hypothetical = await generate_hypothetical_answer(
            self._groq, self._prompts_dir, self._groq_model, query.question
        )

        # ---- embed hypothetical answer with BGE ----
        emb_list = await embed_texts(self._http, [hypothetical], which="bge")
        emb = emb_list[0]

        # ---- dense + sparse retrieval ----
        source_filter = query.source_type if query.source_type != "any" else None
        dense_hits = await dense_search(
            session, emb, embedder="bge", top_k=50, source_type=source_filter
        )
        sparse_hits = await sparse_search(
            session, query.question, top_k=50, source_type=source_filter
        )

        dense_ids = [chunk_id for chunk_id, _score in dense_hits]
        sparse_ids = [chunk_id for chunk_id, _score in sparse_hits]

        log.info(
            "rag.retrieve.candidates",
            n_dense=len(dense_ids),
            n_sparse=len(sparse_ids),
        )

        # ---- RRF combine, take top-20 candidates for rerank ----
        rrf = rrf_combine([dense_ids, sparse_ids], k=60)
        top20_ids = [chunk_id for chunk_id, _score in rrf[:20]]

        if not top20_ids:
            log.warning("rag.retrieve.empty", question=query.question[:80])
            return RagAnswerContext(hits=[], hypothetical_answer=hypothetical)

        # ---- pull texts for the top-20 ----
        chunks_by_id = await get_chunks_by_ids(session, top20_ids)
        ordered = [chunks_by_id[cid] for cid in top20_ids if cid in chunks_by_id]
        passages = [c.text for c in ordered]

        # ---- rerank with cross-encoder ----
        ranked = await rerank_passages(self._http, query.question, passages, top_k=query.top_k)

        # ---- build hits in reranked order ----
        hits: list[RagHit] = []
        for idx, score in ranked:
            c = ordered[idx]
            hits.append(
                RagHit(
                    chunk_id=c.chunk_id,
                    text=c.text,
                    source_type=c.source_type,
                    source_path=c.source_path,
                    section_headers=list(c.section_headers),
                    score=score,
                )
            )

        log.info("rag.retrieve.done", n_hits=len(hits))
        return RagAnswerContext(hits=hits, hypothetical_answer=hypothetical)
