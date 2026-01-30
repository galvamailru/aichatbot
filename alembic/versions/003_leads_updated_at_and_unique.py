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
    op.add_column("leads", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_unique_constraint("uq_leads_user_dialog", "leads", ["user_id", "dialog_id"])


def downgrade() -> None:
    op.drop_constraint("uq_leads_user_dialog", "leads", type_="unique")
    op.drop_column("leads", "updated_at")
