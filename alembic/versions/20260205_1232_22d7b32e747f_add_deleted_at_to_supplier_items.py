"""add_deleted_at_to_supplier_items

Revision ID: 22d7b32e747f
Revises: 005_add_ai_tables
Create Date: 2026-02-05 12:32:29.556539

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '22d7b32e747f'
down_revision: Union[str, None] = '005_add_ai_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add deleted_at column to supplier_items for soft delete support
    op.add_column('supplier_items', sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove deleted_at column
    op.drop_column('supplier_items', 'deleted_at')
