"""Convert order_status ENUM to VARCHAR and backfill buyer records for suppliers.

Revision ID: fix_enum_backfill_buyers
Revises: allow_manual_items
Create Date: 2026-03-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fix_enum_backfill_buyers"
down_revision: Union[str, None] = "allow_manual_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Convert order_status ENUM to VARCHAR to match SQLAlchemy String model
    # First drop the server_default that depends on the ENUM type
    op.execute("ALTER TABLE orders ALTER COLUMN status DROP DEFAULT")
    # Convert column type
    op.execute(
        "ALTER TABLE orders ALTER COLUMN status TYPE VARCHAR "
        "USING status::text"
    )
    # Re-add default as plain string
    op.execute("ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'pending'")
    # Now safe to drop the ENUM type
    op.execute("DROP TYPE IF EXISTS order_status")

    # 2. Create buyer records for suppliers that don't have one yet
    op.execute("""
        INSERT INTO buyers (id, name, phone, email, city_id, status, password_hash, created_at, updated_at)
        SELECT
            s.id,
            s.name,
            COALESCE(s.contacts->>'phone', ''),
            s.email,
            s.city_id,
            'active',
            s.password_hash,
            s.created_at,
            s.updated_at
        FROM suppliers s
        LEFT JOIN buyers b ON s.id = b.id
        WHERE b.id IS NULL
          AND s.city_id IS NOT NULL
    """)


def downgrade() -> None:
    # Re-create ENUM type
    op.execute(
        "CREATE TYPE order_status AS ENUM "
        "('pending', 'confirmed', 'rejected', 'cancelled', 'assembled', 'shipped')"
    )
    op.execute("ALTER TABLE orders ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE orders ALTER COLUMN status TYPE order_status "
        "USING status::order_status"
    )
    op.execute("ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'pending'")
    # Note: backfilled buyer records are NOT removed on downgrade
