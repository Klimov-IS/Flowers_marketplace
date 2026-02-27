"""Order models."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base, TimestampMixin, UUIDMixin


class Order(Base, UUIDMixin, TimestampMixin):
    """Order model."""

    __tablename__ = "orders"

    buyer_id: Mapped[UUID] = mapped_column(
        ForeignKey("buyers.id"), nullable=False, index=True
    )
    supplier_id: Mapped[UUID] = mapped_column(
        ForeignKey("suppliers.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, server_default="pending", index=True
    )  # pending, confirmed, assembled, rejected, cancelled
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="RUB"
    )
    delivery_address: Mapped[str | None] = mapped_column(String, nullable=True)
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    assembled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    buyer: Mapped["Buyer"] = relationship("Buyer", back_populates="orders")
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base, UUIDMixin):
    """Order item model."""

    __tablename__ = "order_items"

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    offer_id: Mapped[UUID] = mapped_column(
        ForeignKey("offers.id"), nullable=False, index=True
    )
    normalized_sku_id: Mapped[UUID] = mapped_column(
        ForeignKey("normalized_skus.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    offer: Mapped["Offer"] = relationship("Offer")
    normalized_sku: Mapped["NormalizedSKU"] = relationship("NormalizedSKU")
