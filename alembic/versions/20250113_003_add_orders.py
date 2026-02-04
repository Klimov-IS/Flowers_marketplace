"""Add orders (buyers, orders, order_items)

Revision ID: 003_add_orders
Revises: 002
Create Date: 2025-01-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_add_orders'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create buyer_status enum
    buyer_status_enum = postgresql.ENUM('active', 'blocked', 'pending_verification', name='buyer_status', create_type=False)
    buyer_status_enum.create(op.get_bind(), checkfirst=True)

    # Create order_status enum
    order_status_enum = postgresql.ENUM('pending', 'confirmed', 'rejected', 'cancelled', name='order_status', create_type=False)
    order_status_enum.create(op.get_bind(), checkfirst=True)

    # Create buyers table
    op.create_table(
        'buyers',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('city_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'blocked', 'pending_verification', name='buyer_status', create_type=False), nullable=False, server_default='active'),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['city_id'], ['cities.id'], name='fk_buyers_city_id'),
        sa.PrimaryKeyConstraint('id', name='pk_buyers'),
    )

    # Create indexes for buyers
    op.create_index('ix_buyers_status', 'buyers', ['status'])
    op.create_index('ix_buyers_city_id', 'buyers', ['city_id'])
    op.create_index('ix_buyers_phone', 'buyers', ['phone'])
    op.create_index('ix_buyers_email', 'buyers', ['email'])

    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('buyer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'confirmed', 'rejected', 'cancelled', name='order_status', create_type=False), nullable=False, server_default='pending'),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='RUB'),
        sa.Column('delivery_address', sa.String(), nullable=True),
        sa.Column('delivery_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('total_amount > 0', name='ck_orders_total_amount_positive'),
        sa.ForeignKeyConstraint(['buyer_id'], ['buyers.id'], name='fk_orders_buyer_id'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], name='fk_orders_supplier_id'),
        sa.PrimaryKeyConstraint('id', name='pk_orders'),
    )

    # Create indexes for orders
    op.create_index('ix_orders_buyer_id_created_at', 'orders', ['buyer_id', 'created_at'])
    op.create_index('ix_orders_supplier_id_status_created_at', 'orders', ['supplier_id', 'status', 'created_at'])
    op.create_index('ix_orders_status', 'orders', ['status'])
    op.create_index('ix_orders_created_at', 'orders', ['created_at'])

    # Create order_items table
    op.create_table(
        'order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('offer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('normalized_sku_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('total_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('quantity > 0', name='ck_order_items_quantity_positive'),
        sa.CheckConstraint('unit_price >= 0', name='ck_order_items_unit_price_non_negative'),
        sa.CheckConstraint('total_price >= 0', name='ck_order_items_total_price_non_negative'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name='fk_order_items_order_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], name='fk_order_items_offer_id'),
        sa.ForeignKeyConstraint(['normalized_sku_id'], ['normalized_skus.id'], name='fk_order_items_normalized_sku_id'),
        sa.PrimaryKeyConstraint('id', name='pk_order_items'),
    )

    # Create indexes for order_items
    op.create_index('ix_order_items_order_id', 'order_items', ['order_id'])
    op.create_index('ix_order_items_offer_id', 'order_items', ['offer_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('ix_order_items_offer_id', table_name='order_items')
    op.drop_index('ix_order_items_order_id', table_name='order_items')
    op.drop_table('order_items')

    op.drop_index('ix_orders_created_at', table_name='orders')
    op.drop_index('ix_orders_status', table_name='orders')
    op.drop_index('ix_orders_supplier_id_status_created_at', table_name='orders')
    op.drop_index('ix_orders_buyer_id_created_at', table_name='orders')
    op.drop_table('orders')

    op.drop_index('ix_buyers_email', table_name='buyers')
    op.drop_index('ix_buyers_phone', table_name='buyers')
    op.drop_index('ix_buyers_city_id', table_name='buyers')
    op.drop_index('ix_buyers_status', table_name='buyers')
    op.drop_table('buyers')

    # Drop enums
    sa.Enum(name='order_status').drop(op.get_bind())
    sa.Enum(name='buyer_status').drop(op.get_bind())
