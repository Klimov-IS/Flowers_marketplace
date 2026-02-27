"""Add seller profile fields and assembled order status.

Revision ID: add_seller_profile
Revises: add_photo_url
Create Date: 2026-02-27 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_seller_profile"
down_revision: Union[str, None] = "add_photo_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add profile fields to suppliers and assembled_at to orders."""
    # New columns for supplier profile
    op.add_column("suppliers", sa.Column("legal_name", sa.String(), nullable=True))
    op.add_column("suppliers", sa.Column("warehouse_address", sa.String(), nullable=True))
    op.add_column("suppliers", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "suppliers",
        sa.Column("min_order_amount", sa.Numeric(precision=10, scale=2), nullable=True),
    )
    op.add_column("suppliers", sa.Column("avatar_url", sa.String(), nullable=True))

    # Add assembled_at to orders (for "assembled/picked" status)
    op.add_column(
        "orders",
        sa.Column("assembled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Remove added columns."""
    op.drop_column("orders", "assembled_at")
    op.drop_column("suppliers", "avatar_url")
    op.drop_column("suppliers", "min_order_amount")
    op.drop_column("suppliers", "description")
    op.drop_column("suppliers", "warehouse_address")
    op.drop_column("suppliers", "legal_name")
