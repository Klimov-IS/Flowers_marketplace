"""Fix order ENUM (add assembled, shipped) and add shipping columns.

Revision ID: fix_order_statuses
Revises: add_password_reset_codes
Create Date: 2026-03-03 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fix_order_statuses"
down_revision: Union[str, None] = "add_password_reset_codes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing ENUM values and new columns."""
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction in PostgreSQL.
    # We need to commit the current transaction first.
    op.execute("COMMIT")

    # Add missing 'assembled' value to order_status ENUM
    op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'assembled'")
    # Add new 'shipped' value
    op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'shipped'")

    # Now start a new transaction for DDL
    op.execute("BEGIN")

    # Add shipped_at timestamp
    op.add_column(
        "orders",
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add delivery_type column (pickup / delivery)
    op.add_column(
        "orders",
        sa.Column(
            "delivery_type",
            sa.String(20),
            nullable=True,
            server_default="delivery",
        ),
    )


def downgrade() -> None:
    """Remove added columns. ENUM values cannot be removed easily."""
    op.drop_column("orders", "delivery_type")
    op.drop_column("orders", "shipped_at")
