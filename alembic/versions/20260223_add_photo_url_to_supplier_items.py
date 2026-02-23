"""Add photo_url to supplier_items.

Revision ID: add_photo_url
Revises: add_telegram_links
Create Date: 2026-02-23 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_photo_url"
down_revision: Union[str, None] = "add_telegram_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add photo_url column to supplier_items."""
    op.add_column(
        "supplier_items",
        sa.Column("photo_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove photo_url column from supplier_items."""
    op.drop_column("supplier_items", "photo_url")
