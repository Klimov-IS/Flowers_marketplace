"""Add AI tables for normalization assistance.

Revision ID: 005_add_ai_tables
Revises: 004_add_auth_fields
Create Date: 2026-02-04

Tables:
- ai_runs: Track each AI invocation
- ai_suggestions: Individual suggestions per row/field
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '005_add_ai_tables'
down_revision = '004_add_auth_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ai_runs table
    op.create_table(
        'ai_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('supplier_id', UUID(as_uuid=True), sa.ForeignKey('suppliers.id'), nullable=False),
        sa.Column('import_batch_id', UUID(as_uuid=True), sa.ForeignKey('import_batches.id'), nullable=True),
        sa.Column('run_type', sa.String(50), nullable=False),  # column_mapping | attribute_extraction | combined
        sa.Column('model_name', sa.String(100), nullable=False, server_default='deepseek-chat'),
        sa.Column('status', sa.String(20), nullable=False, server_default='created'),  # created|running|succeeded|failed|skipped
        sa.Column('row_count', sa.Integer, nullable=True),
        sa.Column('input_hash', sa.String(64), nullable=True),  # SHA256 for caching
        sa.Column('tokens_input', sa.Integer, nullable=True),
        sa.Column('tokens_output', sa.Integer, nullable=True),
        sa.Column('cost_usd', sa.Numeric(10, 6), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    # Create ai_suggestions table
    op.create_table(
        'ai_suggestions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('ai_run_id', UUID(as_uuid=True), sa.ForeignKey('ai_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('suggestion_type', sa.String(50), nullable=False),  # column_mapping | attribute | sku_match
        sa.Column('target_entity', sa.String(50), nullable=True),  # supplier_item | offer_candidate
        sa.Column('target_id', UUID(as_uuid=True), nullable=True),  # supplier_item_id or offer_candidate_id
        sa.Column('row_index', sa.Integer, nullable=True),  # for pre-entity suggestions
        sa.Column('field_name', sa.String(50), nullable=True),  # flower_type, origin_country, etc.
        sa.Column('suggested_value', JSONB, nullable=False),
        sa.Column('confidence', sa.Numeric(4, 3), nullable=False),  # 0.000 to 1.000
        sa.Column('applied_status', sa.String(20), nullable=False, server_default='pending'),
        # pending|auto_applied|manual_applied|rejected|needs_review
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('applied_by', sa.String(20), nullable=True),  # system | seller | admin
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    # Create indexes
    op.create_index('idx_ai_runs_batch', 'ai_runs', ['import_batch_id'])
    op.create_index('idx_ai_runs_status', 'ai_runs', ['status'])
    op.create_index('idx_ai_runs_supplier', 'ai_runs', ['supplier_id'])
    op.create_index('idx_ai_suggestions_run', 'ai_suggestions', ['ai_run_id'])
    op.create_index('idx_ai_suggestions_target', 'ai_suggestions', ['target_entity', 'target_id'])
    op.create_index('idx_ai_suggestions_status', 'ai_suggestions', ['applied_status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_ai_suggestions_status', table_name='ai_suggestions')
    op.drop_index('idx_ai_suggestions_target', table_name='ai_suggestions')
    op.drop_index('idx_ai_suggestions_run', table_name='ai_suggestions')
    op.drop_index('idx_ai_runs_supplier', table_name='ai_runs')
    op.drop_index('idx_ai_runs_status', table_name='ai_runs')
    op.drop_index('idx_ai_runs_batch', table_name='ai_runs')

    # Drop tables
    op.drop_table('ai_suggestions')
    op.drop_table('ai_runs')
