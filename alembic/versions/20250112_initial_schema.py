"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema."""
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Create cities table
    op.create_table(
        "cities",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create suppliers table
    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("contacts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_suppliers_city_status", "suppliers", ["city_id", "status"])

    # Create import_batches table
    op.create_table(
        "import_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False, server_default="other"),
        sa.Column("source_filename", sa.String(), nullable=True),
        sa.Column("declared_effective_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="received"),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_batches_supplier_time", "import_batches", ["supplier_id", "imported_at"])

    # Create raw_rows table
    op.create_table(
        "raw_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_kind", sa.String(), nullable=False, server_default="data"),
        sa.Column("row_ref", sa.String(), nullable=True),
        sa.Column("raw_cells", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["import_batch_id"], ["import_batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raw_rows_batch_kind", "raw_rows", ["import_batch_id", "row_kind"])
    op.execute("CREATE INDEX gin_raw_rows_raw_text_trgm ON raw_rows USING gin (raw_text gin_trgm_ops)")

    # Create parse_runs table
    op.create_table(
        "parse_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parser_version", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["import_batch_id"], ["import_batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parse_runs_batch_time", "parse_runs", ["import_batch_id", "started_at"])

    # Create parse_events table
    op.create_table(
        "parse_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("parse_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_row_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("severity", sa.String(), nullable=False, server_default="info"),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parse_run_id"], ["parse_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_row_id"], ["raw_rows.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parse_events_run_sev", "parse_events", ["parse_run_id", "severity"])

    # Create supplier_items table
    op.create_table(
        "supplier_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stable_key", sa.String(), nullable=False),
        sa.Column("last_import_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("raw_name", sa.Text(), nullable=False),
        sa.Column("raw_group", sa.Text(), nullable=True),
        sa.Column("name_norm", sa.Text(), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("stable_key IS NOT NULL", name="ck_supplier_items_stable_key_not_null"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_id", "stable_key", name="uq_supplier_items_supplier_stable_key"),
    )
    op.create_index("ix_supplier_items_supplier_status", "supplier_items", ["supplier_id", "status"])
    op.execute("CREATE INDEX gin_supplier_items_raw_name_trgm ON supplier_items USING gin (raw_name gin_trgm_ops)")
    op.execute("CREATE INDEX gin_supplier_items_name_norm_trgm ON supplier_items USING gin (name_norm gin_trgm_ops)")

    # Create offer_candidates table
    op.create_table(
        "offer_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("supplier_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_row_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.Column("validation", sa.String(), nullable=False, server_default="ok"),
        sa.Column("validation_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length_cm IS NULL OR length_cm > 0", name="ck_length_cm_positive"),
        sa.CheckConstraint("pack_qty IS NULL OR pack_qty > 0", name="ck_pack_qty_positive"),
        sa.CheckConstraint("price_min >= 0", name="ck_price_min_non_negative"),
        sa.CheckConstraint("price_max IS NULL OR price_max >= 0", name="ck_price_max_non_negative"),
        sa.CheckConstraint("price_max IS NULL OR price_min <= price_max", name="ck_price_min_le_max"),
        sa.CheckConstraint("stock_qty IS NULL OR stock_qty >= 0", name="ck_stock_qty_non_negative"),
        sa.CheckConstraint("tier_min_qty IS NULL OR tier_min_qty >= 0", name="ck_tier_min_qty_non_negative"),
        sa.CheckConstraint("tier_max_qty IS NULL OR tier_max_qty >= 0", name="ck_tier_max_qty_non_negative"),
        sa.CheckConstraint(
            "(tier_min_qty IS NULL AND tier_max_qty IS NULL) OR "
            "(tier_min_qty IS NOT NULL AND tier_max_qty IS NOT NULL AND tier_min_qty <= tier_max_qty)",
            name="ck_tier_consistency",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_offer_candidates_item_batch", "offer_candidates", ["supplier_item_id", "import_batch_id"])
    op.create_index("ix_offer_candidates_batch_validation", "offer_candidates", ["import_batch_id", "validation"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("offer_candidates")
    op.drop_table("supplier_items")
    op.drop_table("parse_events")
    op.drop_table("parse_runs")
    op.drop_table("raw_rows")
    op.drop_table("import_batches")
    op.drop_table("suppliers")
    op.drop_table("cities")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
