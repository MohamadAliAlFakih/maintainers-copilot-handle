"""chunks table with two vector columns + tsvector

Revision ID: 0003_chunks_table
Revises: 0002_users_and_audit_log
Create Date: 2026-05-20

"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_chunks_table"
down_revision = "0002_users_and_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Creates the chunks table with vectors + tsvector and ivfflat indexes."""
    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chunk_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_path", sa.String(length=512), nullable=False),
        sa.Column(
            "section_headers",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("version_tag", sa.String(length=64), nullable=False, server_default="main"),
        sa.Column("embedding_bge", Vector(384), nullable=False),
        sa.Column("embedding_minilm", Vector(384), nullable=False),
        sa.Column("tsv", postgresql.TSVECTOR, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_chunks_source_type", "chunks", ["source_type"])
    op.create_index("ix_chunks_chunk_id", "chunks", ["chunk_id"], unique=True)

    # ivfflat indexes for cosine similarity. lists=100 is sensible for a ~5k-row corpus.
    op.execute(
        "CREATE INDEX ix_chunks_embedding_bge ON chunks "
        "USING ivfflat (embedding_bge vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute(
        "CREATE INDEX ix_chunks_embedding_minilm ON chunks "
        "USING ivfflat (embedding_minilm vector_cosine_ops) WITH (lists = 100)"
    )

    # GIN index for tsvector full-text search
    op.execute("CREATE INDEX ix_chunks_tsv ON chunks USING gin (tsv)")


def downgrade() -> None:
    """Drops the chunks table and its indexes."""
    op.execute("DROP INDEX IF EXISTS ix_chunks_tsv")
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_minilm")
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_bge")
    op.drop_index("ix_chunks_chunk_id", table_name="chunks")
    op.drop_index("ix_chunks_source_type", table_name="chunks")
    op.drop_table("chunks")
