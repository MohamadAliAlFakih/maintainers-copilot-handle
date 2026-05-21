"""baseline — empty migration to mark the schema as initialized

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-20

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Confirms pgvector extension is present; future migrations build on this."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """No-op: we never drop the extension on downgrade."""
    pass
