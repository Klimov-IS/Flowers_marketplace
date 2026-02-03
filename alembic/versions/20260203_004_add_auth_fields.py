"""Add authentication fields to buyers and suppliers.

Revision ID: 004_add_auth_fields
Revises: 003_add_orders
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_add_auth_fields'
down_revision = '003_add_orders'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add password_hash to buyers (email already exists but update to unique)
    op.add_column('buyers', sa.Column('password_hash', sa.String(), nullable=True))

    # Drop existing index on buyers.email if exists and recreate as unique
    op.execute('DROP INDEX IF EXISTS ix_buyers_email')
    op.create_index('ix_buyers_email', 'buyers', ['email'], unique=True)

    # Add email and password_hash to suppliers
    op.add_column('suppliers', sa.Column('email', sa.String(), nullable=True))
    op.add_column('suppliers', sa.Column('password_hash', sa.String(), nullable=True))
    op.create_index('ix_suppliers_email', 'suppliers', ['email'], unique=True)


def downgrade() -> None:
    # Remove from suppliers
    op.drop_index('ix_suppliers_email', table_name='suppliers')
    op.drop_column('suppliers', 'password_hash')
    op.drop_column('suppliers', 'email')

    # Remove from buyers
    op.drop_index('ix_buyers_email', table_name='buyers')
    op.create_index('ix_buyers_email', 'buyers', ['email'], unique=False)
    op.drop_column('buyers', 'password_hash')
