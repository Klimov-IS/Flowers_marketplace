"""Add telegram_links table.

Revision ID: add_telegram_links
Revises: add_offer_display_title
Create Date: 2026-02-23 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "add_telegram_links"
down_revision: Union[str, None] = "add_offer_display_title"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create telegram_links table."""
    op.create_table(
        "telegram_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("telegram_user_id", sa.BigInteger(), unique=True, nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(100), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_telegram_links_entity", "telegram_links", ["role", "entity_id"])
    op.create_index("idx_telegram_links_chat", "telegram_links", ["telegram_chat_id"])


def downgrade() -> None:
    """Drop telegram_links table."""
    op.drop_index("idx_telegram_links_chat", table_name="telegram_links")
    op.drop_index("idx_telegram_links_entity", table_name="telegram_links")
    op.drop_table("telegram_links")
