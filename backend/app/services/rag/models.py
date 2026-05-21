"""Chunk ORM model — both vector columns + tsvector for full-text search."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.services.auth.models import Base


class Chunk(Base):
    """One ingested chunk with two embeddings + a tsvector for hybrid retrieval."""

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_path: Mapped[str] = mapped_column(String(512), nullable=False)
    section_headers: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    version_tag: Mapped[str] = mapped_column(String(64), nullable=False, default="main")
    embedding_bge: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    embedding_minilm: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    tsv: Mapped[str] = mapped_column(TSVECTOR, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=sql_text("now()")
    )

    __table_args__ = (
        Index("ix_chunks_source_type", "source_type"),
        Index("ix_chunks_chunk_id", "chunk_id"),
    )
