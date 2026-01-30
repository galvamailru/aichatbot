"""leads: updated_at and unique (user_id, dialog_id)

Revision ID: 003
Revises: 002
Create Date: 2025-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add column if not present (idempotent if 003 previously failed after add_column)
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute(sa.text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL"))
    else:
        op.add_column("leads", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    # Remove duplicates: keep one row per (user_id, dialog_id) with the latest created_at/id
    op.execute(
        sa.text("""
            DELETE FROM leads
            WHERE id IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (PARTITION BY user_id, dialog_id ORDER BY created_at DESC, id DESC) AS rn
                    FROM leads
                ) t
                WHERE rn > 1
            )
        """)
    )
    op.create_unique_constraint("uq_leads_user_dialog", "leads", ["user_id", "dialog_id"])


def downgrade() -> None:
    op.drop_constraint("uq_leads_user_dialog", "leads", type_="unique")
    op.drop_column("leads", "updated_at")
