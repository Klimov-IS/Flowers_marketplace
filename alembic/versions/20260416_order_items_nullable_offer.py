"""Make order_items.offer_id and normalized_sku_id nullable.

Required for new product-based order flow where offers/skus don't exist.

Revision ID: order_items_nullable_offer
Revises: create_products
Create Date: 2026-04-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "order_items_nullable_offer"
down_revision: Union[str, None] = "create_products"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("order_items", "offer_id", existing_type=UUID(as_uuid=True), nullable=True)
    op.alter_column("order_items", "normalized_sku_id", existing_type=UUID(as_uuid=True), nullable=True)


def downgrade() -> None:
    op.alter_column("order_items", "normalized_sku_id", existing_type=UUID(as_uuid=True), nullable=False)
    op.alter_column("order_items", "offer_id", existing_type=UUID(as_uuid=True), nullable=False)
