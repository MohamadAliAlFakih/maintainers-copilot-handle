"""widgets table

Revision ID: 0006_widgets_table
Revises: 0005_long_term_memory
Create Date: 2026-05-22
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_widgets_table"
down_revision = "0005_long_term_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Creates the widgets table."""
    op.create_table(
        "widgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("widget_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "allowed_origins",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("theme", sa.JSON, nullable=False, server_default="{}"),
        sa.Column(
            "greeting",
            sa.Text,
            nullable=False,
            server_default="How can I help?",
        ),
        sa.Column(
            "enabled_tools",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_widgets_widget_id", "widgets", ["widget_id"], unique=True)


def downgrade() -> None:
    """Drops widgets."""
    op.drop_index("ix_widgets_widget_id", table_name="widgets")
    op.drop_table("widgets")
