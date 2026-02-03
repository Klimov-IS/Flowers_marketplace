"""Buyer model."""
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base, TimestampMixin, UUIDMixin


class Buyer(Base, UUIDMixin, TimestampMixin):
    """Retail buyer model."""

    __tablename__ = "buyers"

    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    city_id: Mapped[UUID] = mapped_column(
        ForeignKey("cities.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, server_default="active", index=True
    )  # active, blocked, pending_verification
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    city: Mapped["City"] = relationship("City", back_populates="buyers")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="buyer")
