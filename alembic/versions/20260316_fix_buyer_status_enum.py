"""Convert buyer_status ENUM to VARCHAR to match SQLAlchemy String model.

This fixes registration (both buyer and supplier) which fails with:
  column "status" is of type buyer_status but expression is of type character varying

Revision ID: fix_buyer_status_enum
Revises: fix_enum_backfill_buyers
Create Date: 2026-03-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fix_buyer_status_enum"
down_revision: Union[str, None] = "fix_enum_backfill_buyers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the server_default that depends on the ENUM type
    op.execute("ALTER TABLE buyers ALTER COLUMN status DROP DEFAULT")
    # Convert column type from buyer_status ENUM to VARCHAR
    op.execute(
        "ALTER TABLE buyers ALTER COLUMN status TYPE VARCHAR "
        "USING status::text"
    )
    # Re-add default as plain string
    op.execute("ALTER TABLE buyers ALTER COLUMN status SET DEFAULT 'active'")
    # Drop the ENUM type
    op.execute("DROP TYPE IF EXISTS buyer_status")


def downgrade() -> None:
    # Re-create ENUM type
    op.execute(
        "CREATE TYPE buyer_status AS ENUM "
        "('active', 'blocked', 'pending_verification')"
    )
    op.execute("ALTER TABLE buyers ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE buyers ALTER COLUMN status TYPE buyer_status "
        "USING status::buyer_status"
    )
    op.execute(
        "ALTER TABLE buyers ALTER COLUMN status SET DEFAULT 'active'::buyer_status"
    )
