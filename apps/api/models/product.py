"""Product model — single unified entity for the marketplace catalog."""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from apps.api.models.parties import Supplier


class Product(Base, UUIDMixin, TimestampMixin):
    """Product — a single catalog item visible to buyers.

    Replaces the old 5-table pipeline:
      supplier_items → offer_candidates → sku_mappings → normalized_skus → offers
    """

    __tablename__ = "products"

    supplier_id: Mapped[UUID] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Display
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    flower_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    variety: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)

    # Attributes
    length_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color: Mapped[str | None] = mapped_column(String(100), nullable=True)
    origin_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pack_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pack_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Pricing
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")

    # Stock
    stock_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Visibility
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", index=True,
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, index=True)

    # Import traceability
    import_batch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    raw_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Migration link to old offers (for order history)
    legacy_offer_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="products")
