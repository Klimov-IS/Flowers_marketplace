"""Geographic models."""
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from apps.api.models.buyer import Buyer
    from apps.api.models.parties import Supplier


class City(Base, UUIDMixin, TimestampMixin):
    """City model."""

    __tablename__ = "cities"

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    buyers: Mapped[list["Buyer"]] = relationship("Buyer", back_populates="city")
    suppliers: Mapped[list["Supplier"]] = relationship("Supplier", back_populates="city")