"""Add unique constraint on sku_mappings(supplier_item_id, normalized_sku_id).

Prevents duplicate mappings from race conditions in concurrent normalization.

Revision ID: add_sku_mapping_unique
Revises: email_password_reset
Create Date: 2026-04-07
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "add_sku_mapping_unique"
down_revision: Union[str, None] = "email_password_reset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove duplicates first: keep the row with the earliest created_at
    op.execute("""
        DELETE FROM sku_mappings
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY supplier_item_id, normalized_sku_id
                           ORDER BY created_at ASC
                       ) AS rn
                FROM sku_mappings
            ) sub
            WHERE rn > 1
        )
    """)

    op.create_unique_constraint(
        "uq_sku_mappings_item_sku",
        "sku_mappings",
        ["supplier_item_id", "normalized_sku_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_sku_mappings_item_sku", "sku_mappings", type_="unique")
