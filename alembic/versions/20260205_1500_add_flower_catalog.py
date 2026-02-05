"""add_flower_catalog

Adds hierarchical flower catalog tables:
- flower_categories (optional grouping)
- flower_types (Роза, Хризантема, Эвкалипт)
- flower_subtypes (Кустовая, Спрей, Пионовидная)
- flower_varieties (Explorer, Freedom, Red Naomi)
- type_synonyms, subtype_synonyms, variety_synonyms

Revision ID: add_flower_catalog
Revises: 22d7b32e747f
Create Date: 2026-02-05 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_flower_catalog'
down_revision: Union[str, None] = '22d7b32e747f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Flower Categories
    op.create_table(
        'flower_categories',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_flower_categories_slug')
    )
    op.create_index('ix_flower_categories_slug', 'flower_categories', ['slug'])

    # 2. Flower Types
    op.create_table(
        'flower_types',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('category_id', sa.UUID(), nullable=True),
        sa.Column('canonical_name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['flower_categories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('canonical_name', name='uq_flower_types_canonical_name'),
        sa.UniqueConstraint('slug', name='uq_flower_types_slug')
    )
    op.create_index('ix_flower_types_category_id', 'flower_types', ['category_id'])
    op.create_index('ix_flower_types_slug', 'flower_types', ['slug'])
    op.create_index('ix_flower_types_is_active', 'flower_types', ['is_active'])

    # 3. Flower Subtypes
    op.create_table(
        'flower_subtypes',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('type_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['type_id'], ['flower_types.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('type_id', 'slug', name='uq_flower_subtypes_type_slug')
    )
    op.create_index('ix_flower_subtypes_type_id', 'flower_subtypes', ['type_id'])

    # 4. Type Synonyms
    op.create_table(
        'type_synonyms',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('type_id', sa.UUID(), nullable=False),
        sa.Column('synonym', sa.String(length=100), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.ForeignKeyConstraint(['type_id'], ['flower_types.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('synonym', name='uq_type_synonyms_synonym'),
        sa.CheckConstraint("synonym = lower(synonym)", name='ck_type_synonyms_lowercase')
    )
    op.create_index('ix_type_synonyms_type_id', 'type_synonyms', ['type_id'])
    op.create_index('ix_type_synonyms_synonym', 'type_synonyms', ['synonym'])

    # 5. Subtype Synonyms
    op.create_table(
        'subtype_synonyms',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('subtype_id', sa.UUID(), nullable=False),
        sa.Column('synonym', sa.String(length=100), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.ForeignKeyConstraint(['subtype_id'], ['flower_subtypes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subtype_id', 'synonym', name='uq_subtype_synonyms_subtype_synonym'),
        sa.CheckConstraint("synonym = lower(synonym)", name='ck_subtype_synonyms_lowercase')
    )
    op.create_index('ix_subtype_synonyms_subtype_id', 'subtype_synonyms', ['subtype_id'])
    op.create_index('ix_subtype_synonyms_synonym', 'subtype_synonyms', ['synonym'])

    # 6. Flower Varieties
    op.create_table(
        'flower_varieties',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('type_id', sa.UUID(), nullable=False),
        sa.Column('subtype_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('official_colors', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('typical_length_min', sa.Integer(), nullable=True),
        sa.Column('typical_length_max', sa.Integer(), nullable=True),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['type_id'], ['flower_types.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subtype_id'], ['flower_subtypes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('type_id', 'slug', name='uq_flower_varieties_type_slug'),
        sa.CheckConstraint(
            "typical_length_min IS NULL OR typical_length_min > 0",
            name='ck_flower_varieties_length_min_positive'
        ),
        sa.CheckConstraint(
            "typical_length_max IS NULL OR typical_length_max > 0",
            name='ck_flower_varieties_length_max_positive'
        ),
        sa.CheckConstraint(
            "typical_length_min IS NULL OR typical_length_max IS NULL OR typical_length_min <= typical_length_max",
            name='ck_flower_varieties_length_range'
        )
    )
    op.create_index('ix_flower_varieties_type_id', 'flower_varieties', ['type_id'])
    op.create_index('ix_flower_varieties_subtype_id', 'flower_varieties', ['subtype_id'])
    op.create_index('ix_flower_varieties_is_active', 'flower_varieties', ['is_active'])

    # Enable pg_trgm extension for fuzzy search (may already exist)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # Trigram index for fuzzy name search
    op.execute("CREATE INDEX ix_flower_varieties_name_trgm ON flower_varieties USING gin(name gin_trgm_ops)")

    # 7. Variety Synonyms
    op.create_table(
        'variety_synonyms',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('variety_id', sa.UUID(), nullable=False),
        sa.Column('synonym', sa.String(length=150), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.ForeignKeyConstraint(['variety_id'], ['flower_varieties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('variety_id', 'synonym', name='uq_variety_synonyms_variety_synonym'),
        sa.CheckConstraint("synonym = lower(synonym)", name='ck_variety_synonyms_lowercase')
    )
    op.create_index('ix_variety_synonyms_variety_id', 'variety_synonyms', ['variety_id'])
    op.create_index('ix_variety_synonyms_synonym', 'variety_synonyms', ['synonym'])


def downgrade() -> None:
    # Drop in reverse order
    op.drop_table('variety_synonyms')
    op.execute("DROP INDEX IF EXISTS ix_flower_varieties_name_trgm")
    op.drop_table('flower_varieties')
    op.drop_table('subtype_synonyms')
    op.drop_table('type_synonyms')
    op.drop_table('flower_subtypes')
    op.drop_table('flower_types')
    op.drop_table('flower_categories')
