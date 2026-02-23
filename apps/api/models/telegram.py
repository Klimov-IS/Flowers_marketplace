"""Telegram integration models."""
from sqlalchemy import BigInteger, Boolean, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.models.base import Base, TimestampMixin, UUIDMixin


class TelegramLink(Base, UUIDMixin, TimestampMixin):
    """Link between a Telegram user and a platform entity (supplier/buyer)."""

    __tablename__ = "telegram_links"
    __table_args__ = (
        Index("idx_telegram_links_entity", "role", "entity_id"),
        Index("idx_telegram_links_chat", "telegram_chat_id"),
    )

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False
    )
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'supplier' or 'buyer'
    entity_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
