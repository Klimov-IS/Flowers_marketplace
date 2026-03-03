"""Allow manual item creation (nullable import_batch_id).

Revision ID: allow_manual_items
Revises: fix_order_statuses
Create Date: 2026-03-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "allow_manual_items"
down_revision: Union[str, None] = "fix_order_statuses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make import_batch_id nullable so items can be created manually
    op.alter_column(
        "offer_candidates",
        "import_batch_id",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "offer_candidates",
        "import_batch_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
