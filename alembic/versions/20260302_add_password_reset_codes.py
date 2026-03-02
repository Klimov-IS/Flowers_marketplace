"""Add password_reset_codes table.

Revision ID: add_password_reset_codes
Revises: add_seller_profile
Create Date: 2026-03-02 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "add_password_reset_codes"
down_revision: Union[str, None] = "add_seller_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create password_reset_codes table."""
    op.create_table(
        "password_reset_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_password_reset_codes_user", "password_reset_codes", ["user_id", "role"])


def downgrade() -> None:
    """Drop password_reset_codes table."""
    op.drop_index("idx_password_reset_codes_user", table_name="password_reset_codes")
    op.drop_table("password_reset_codes")
