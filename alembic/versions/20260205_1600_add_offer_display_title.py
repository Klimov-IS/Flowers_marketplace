"""Add display_title to offers table.

Revision ID: add_offer_display_title
Revises: 20260205_1500_add_flower_catalog
Create Date: 2026-02-05 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_offer_display_title"
down_revision: Union[str, None] = "20260205_1500_add_flower_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add display_title column to offers table."""
    op.add_column(
        "offers",
        sa.Column(
            "display_title",
            sa.String(255),
            nullable=True,
            comment="Clean name for display (Тип + Субтип + Сорт)",
        ),
    )


def downgrade() -> None:
    """Remove display_title column from offers table."""
    op.drop_column("offers", "display_title")
