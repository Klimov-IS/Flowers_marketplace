"""Create products table and migrate data from offers/supplier_items.

Consolidates the 5-table pipeline into a single products table.
Old tables are NOT dropped — soft deprecation.

Revision ID: create_products
Revises: add_sku_mapping_unique
Create Date: 2026-04-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "create_products"
down_revision: Union[str, None] = "add_sku_mapping_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Step 1: Create products table ---
    op.create_table(
        "products",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("flower_type", sa.String(100), nullable=True),
        sa.Column("variety", sa.String(255), nullable=True),
        sa.Column("length_cm", sa.Integer(), nullable=True),
        sa.Column("color", sa.String(100), nullable=True),
        sa.Column("origin_country", sa.String(100), nullable=True),
        sa.Column("pack_type", sa.String(50), nullable=True),
        sa.Column("pack_qty", sa.Integer(), nullable=True),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("stock_qty", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("import_batch_id", UUID(as_uuid=True), nullable=True),
        sa.Column("raw_name", sa.Text(), nullable=True),
        sa.Column("legacy_offer_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["import_batch_id"], ["import_batches.id"], ondelete="SET NULL"),
    )

    # Indexes
    op.create_index("ix_products_supplier_id", "products", ["supplier_id"])
    op.create_index("ix_products_flower_type", "products", ["flower_type"])
    op.create_index("ix_products_variety", "products", ["variety"])
    op.create_index("ix_products_status", "products", ["status"])
    op.create_index("ix_products_is_active", "products", ["is_active"])
    op.create_index("ix_products_legacy_offer_id", "products", ["legacy_offer_id"])

    # GIN index for title search
    op.execute(
        "CREATE INDEX ix_products_title_trgm ON products USING gin (title gin_trgm_ops)"
    )

    # --- Step 2: Migrate data from active offers ---
    # Each active offer becomes a product.
    # We join through sku_mappings → supplier_items to get photo_url and raw_name,
    # and through normalized_skus to get flower_type (product_type) and variety.
    op.execute("""
        INSERT INTO products (
            id, supplier_id, title, flower_type, variety,
            length_cm, color, origin_country, pack_type, pack_qty,
            photo_url, price, currency, stock_qty,
            status, is_active, import_batch_id, raw_name,
            legacy_offer_id, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            o.supplier_id,
            COALESCE(o.display_title, ns.title, si.raw_name, 'Без названия'),
            LEFT(ns.product_type, 100),
            LEFT(ns.variety, 255),
            o.length_cm,
            LEFT(ns.color, 100),
            LEFT(si.attributes->>'origin_country', 100),
            o.pack_type,
            o.pack_qty,
            si.photo_url,
            o.price_min,
            o.currency,
            o.stock_qty,
            CASE WHEN o.is_active THEN 'active' ELSE 'hidden' END,
            o.is_active,
            o.source_import_batch_id,
            si.raw_name,
            o.id,
            o.created_at,
            o.updated_at
        FROM offers o
        JOIN normalized_skus ns ON ns.id = o.normalized_sku_id
        LEFT JOIN sku_mappings sm ON sm.normalized_sku_id = ns.id
            AND sm.status = 'confirmed'
        LEFT JOIN supplier_items si ON si.id = sm.supplier_item_id
            AND si.supplier_id = o.supplier_id
    """)

    # --- Step 3: Migrate "stuck" supplier_items that never became offers ---
    # These are items that exist in supplier_items but have no confirmed mapping
    # or were never published. They should be visible in the seller's catalog.
    op.execute("""
        INSERT INTO products (
            id, supplier_id, title, flower_type, variety,
            length_cm, color, origin_country, pack_type, pack_qty,
            photo_url, price, currency, stock_qty,
            status, is_active, import_batch_id, raw_name,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            si.supplier_id,
            COALESCE(
                si.attributes->>'clean_name',
                si.raw_name,
                'Без названия'
            ),
            LEFT(si.attributes->>'flower_type', 100),
            LEFT(si.attributes->>'variety', 255),
            (oc.length_cm),
            LEFT(COALESCE(
                si.attributes->>'color',
                (si.attributes->'colors'->>0)
            ), 100),
            LEFT(si.attributes->>'origin_country', 100),
            oc.pack_type,
            oc.pack_qty,
            si.photo_url,
            COALESCE(oc.price_min, 0),
            COALESCE(oc.currency, 'RUB'),
            oc.stock_qty,
            CASE
                WHEN si.status = 'deleted' THEN 'deleted'
                WHEN si.status = 'hidden' THEN 'hidden'
                ELSE 'active'
            END,
            CASE
                WHEN si.status IN ('active', 'ambiguous') THEN true
                ELSE false
            END,
            si.last_import_batch_id,
            si.raw_name,
            si.created_at,
            COALESCE(si.updated_at, si.created_at)
        FROM supplier_items si
        LEFT JOIN LATERAL (
            SELECT oc2.*
            FROM offer_candidates oc2
            WHERE oc2.supplier_item_id = si.id
            ORDER BY oc2.created_at DESC
            LIMIT 1
        ) oc ON true
        WHERE NOT EXISTS (
            SELECT 1 FROM sku_mappings sm2
            JOIN offers o2 ON o2.normalized_sku_id = sm2.normalized_sku_id
                AND o2.supplier_id = si.supplier_id
            WHERE sm2.supplier_item_id = si.id
                AND sm2.status = 'confirmed'
        )
    """)

    # --- Step 4: Add product_id column to order_items ---
    op.add_column(
        "order_items",
        sa.Column("product_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_order_items_product_id",
        "order_items",
        "products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_order_items_product_id", "order_items", ["product_id"])

    # --- Step 5: Backfill order_items.product_id via legacy_offer_id ---
    op.execute("""
        UPDATE order_items oi
        SET product_id = p.id
        FROM products p
        WHERE p.legacy_offer_id = oi.offer_id
    """)


def downgrade() -> None:
    # Drop order_items.product_id
    op.drop_index("ix_order_items_product_id", table_name="order_items")
    op.drop_constraint("fk_order_items_product_id", "order_items", type_="foreignkey")
    op.drop_column("order_items", "product_id")

    # Drop products table
    op.drop_index("ix_products_title_trgm", table_name="products")
    op.drop_index("ix_products_legacy_offer_id", table_name="products")
    op.drop_index("ix_products_is_active", table_name="products")
    op.drop_index("ix_products_status", table_name="products")
    op.drop_index("ix_products_variety", table_name="products")
    op.drop_index("ix_products_flower_type", table_name="products")
    op.drop_index("ix_products_supplier_id", table_name="products")
    op.drop_table("products")
