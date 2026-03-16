"""Make telegram_chat_id nullable for email-based password resets.

Revision ID: email_password_reset
Revises: fix_buyer_status_enum
Create Date: 2026-03-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "email_password_reset"
down_revision: Union[str, None] = "fix_buyer_status_enum"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "password_reset_codes",
        "telegram_chat_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )


def downgrade() -> None:
    # Set any NULLs to 0 before making non-nullable
    op.execute("UPDATE password_reset_codes SET telegram_chat_id = 0 WHERE telegram_chat_id IS NULL")
    op.alter_column(
        "password_reset_codes",
        "telegram_chat_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
