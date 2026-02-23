"""Party models (suppliers, buyers)."""
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from apps.api.models.geo import City
    from apps.api.models.normalized import Offer
    from apps.api.models.order import Order


class SupplierStatus(str, Enum):
    """Supplier status enum."""

    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"


class Supplier(Base, UUIDMixin, TimestampMixin):
    """Supplier (wholesale base) model."""

    __tablename__ = "suppliers"

    city_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cities.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=SupplierStatus.PENDING.value,
    )
    contacts: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Relationships
    city: Mapped["City | None"] = relationship("City", back_populates="suppliers")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="supplier")
    offers: Mapped[list["Offer"]] = relationship("Offer", back_populates="supplier")