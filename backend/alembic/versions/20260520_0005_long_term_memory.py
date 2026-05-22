"""long_term_memory table

Revision ID: 0005_long_term_memory
Revises: 0004_conversations_messages
Create Date: 2026-05-22
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005_long_term_memory"
down_revision = "0004_conversations_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Creates long_term_memory + ivfflat index."""
    op.create_table(
        "long_term_memory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fact_text", sa.Text, nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("source_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_ltm_user", "long_term_memory", ["user_id"])
    op.execute(
        "CREATE INDEX ix_ltm_embedding ON long_term_memory "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)"
    )


def downgrade() -> None:
    """Drops the table."""
    op.execute("DROP INDEX IF EXISTS ix_ltm_embedding")
    op.drop_index("ix_ltm_user", table_name="long_term_memory")
    op.drop_table("long_term_memory")
