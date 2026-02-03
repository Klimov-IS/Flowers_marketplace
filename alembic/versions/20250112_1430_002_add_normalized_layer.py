"""Add normalized layer tables

Revision ID: 002
Revises: 001
Create Date: 2025-01-12 14:30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create normalized layer tables."""

    # Create normalized_skus table
    op.create_table(
        "normalized_skus",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("product_type", sa.String(), nullable=False),
        sa.Column("variety", sa.String(), nullable=True),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_normalized_skus_product_type", "normalized_skus", ["product_type"])

    # Create dictionary_entries table
    op.create_table(
        "dictionary_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("dict_type", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("synonyms", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dict_type", "key", name="uq_dictionary_entries_type_key"),
    )
    op.create_index("ix_dictionary_entries_type_status", "dictionary_entries", ["dict_type", "status"])
    op.execute("CREATE INDEX gin_dictionary_entries_synonyms ON dictionary_entries USING gin (synonyms)")

    # Create sku_mappings table
    op.create_table(
        "sku_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("supplier_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("normalized_sku_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("method", sa.String(), nullable=False, server_default="rule"),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default="0.000"),
        sa.Column("status", sa.String(), nullable=False, server_default="proposed"),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_sku_mappings_confidence_range"),
        sa.ForeignKeyConstraint(["supplier_item_id"], ["supplier_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["normalized_sku_id"], ["normalized_skus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sku_mappings_item_status", "sku_mappings", ["supplier_item_id", "status"])
    op.create_index("ix_sku_mappings_sku_status", "sku_mappings", ["normalized_sku_id", "status"])

    # Unique constraint: only one confirmed mapping per supplier_item
    op.execute(
        "CREATE UNIQUE INDEX ux_sku_mappings_one_confirmed_per_item "
        "ON sku_mappings (supplier_item_id) WHERE status = 'confirmed'"
    )

    # Create normalization_tasks table
    op.create_table(
        "normalization_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("supplier_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["supplier_item_id"], ["supplier_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_normalization_tasks_item", "normalization_tasks", ["supplier_item_id"])
    op.create_index("ix_normalization_tasks_status_priority", "normalization_tasks", ["status", "priority"])

    # Create supplier_delivery_rules table
    op.create_table(
        "supplier_delivery_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("delivery_zone", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("min_order_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("min_order_qty", sa.Integer(), nullable=True),
        sa.Column("delivery_windows", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("min_order_amount IS NULL OR min_order_amount >= 0", name="ck_supplier_delivery_rules_min_order_amount"),
        sa.CheckConstraint("min_order_qty IS NULL OR min_order_qty >= 0", name="ck_supplier_delivery_rules_min_order_qty"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supplier_delivery_rules_supplier", "supplier_delivery_rules", ["supplier_id"])

    # Create offers table
    op.create_table(
        "offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("normalized_sku_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_import_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("length_cm", sa.Integer(), nullable=True),
        sa.Column("pack_type", sa.String(), nullable=True),
        sa.Column("pack_qty", sa.Integer(), nullable=True),
        sa.Column("price_type", sa.String(), nullable=False, server_default="fixed"),
        sa.Column("price_min", sa.Numeric(12, 2), nullable=False),
        sa.Column("price_max", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("tier_min_qty", sa.Integer(), nullable=True),
        sa.Column("tier_max_qty", sa.Integer(), nullable=True),
        sa.Column("availability", sa.String(), nullable=False, server_default="unknown"),
        sa.Column("stock_qty", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length_cm IS NULL OR length_cm > 0", name="ck_offers_length_cm_positive"),
        sa.CheckConstraint("pack_qty IS NULL OR pack_qty > 0", name="ck_offers_pack_qty_positive"),
        sa.CheckConstraint("price_min >= 0", name="ck_offers_price_min_non_negative"),
        sa.CheckConstraint("price_max IS NULL OR price_max >= 0", name="ck_offers_price_max_non_negative"),
        sa.CheckConstraint("price_max IS NULL OR price_min <= price_max", name="ck_offers_price_min_le_max"),
        sa.CheckConstraint("stock_qty IS NULL OR stock_qty >= 0", name="ck_offers_stock_qty_non_negative"),
        sa.CheckConstraint("tier_min_qty IS NULL OR tier_min_qty >= 0", name="ck_offers_tier_min_qty_non_negative"),
        sa.CheckConstraint("tier_max_qty IS NULL OR tier_max_qty >= 0", name="ck_offers_tier_max_qty_non_negative"),
        sa.CheckConstraint(
            "(tier_min_qty IS NULL AND tier_max_qty IS NULL) OR "
            "(tier_min_qty IS NOT NULL AND tier_max_qty IS NOT NULL AND tier_min_qty <= tier_max_qty)",
            name="ck_offers_tier_consistency",
        ),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["normalized_sku_id"], ["normalized_skus.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_import_batch_id"], ["import_batches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_offers_supplier_active", "offers", ["supplier_id", "is_active"])
    op.create_index("ix_offers_sku_active", "offers", ["normalized_sku_id", "is_active"])
    op.create_index("ix_offers_active_price", "offers", ["is_active", "price_min"])


def downgrade() -> None:
    """Drop normalized layer tables."""
    op.drop_table("offers")
    op.drop_table("supplier_delivery_rules")
    op.drop_table("normalization_tasks")
    op.drop_table("sku_mappings")
    op.drop_table("dictionary_entries")
    op.drop_table("normalized_skus")
