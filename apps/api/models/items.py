"""Supplier items and offer candidates models."""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.models.base import Base, TimestampMixin, UUIDMixin


class SupplierItemStatus(str, Enum):
    """Supplier item status enum."""

    ACTIVE = "active"
    AMBIGUOUS = "ambiguous"
    REJECTED = "rejected"
    HIDDEN = "hidden"
    DELETED = "deleted"


class PriceType(str, Enum):
    """Price type enum."""

    FIXED = "fixed"
    RANGE = "range"


class AvailabilityType(str, Enum):
    """Availability type enum."""

    UNKNOWN = "unknown"
    IN_STOCK = "in_stock"
    PREORDER = "preorder"


class ValidationStatus(str, Enum):
    """Validation status enum."""

    OK = "ok"
    WARN = "warn"
    ERROR = "error"


class SupplierItem(Base, UUIDMixin, TimestampMixin):
    """Supplier item - stable position from supplier."""

    __tablename__ = "supplier_items"
    __table_args__ = (
        CheckConstraint("stable_key IS NOT NULL", name="ck_supplier_items_stable_key_not_null"),
    )

    supplier_id: Mapped[UUID] = mapped_column(
        nullable=False,
        index=True,
    )
    stable_key: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    last_import_batch_id: Mapped[UUID | None] = mapped_column(nullable=True)
    raw_name: Mapped[str] = mapped_column(Text, nullable=False)
    raw_group: Mapped[str | None] = mapped_column(Text, nullable=True)
    name_norm: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=SupplierItemStatus.ACTIVE.value,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
    )


class OfferCandidate(Base, UUIDMixin):
    """Offer candidate - parsed offer ready for normalization."""

    __tablename__ = "offer_candidates"
    __table_args__ = (
        CheckConstraint("length_cm IS NULL OR length_cm > 0", name="ck_length_cm_positive"),
        CheckConstraint("pack_qty IS NULL OR pack_qty > 0", name="ck_pack_qty_positive"),
        CheckConstraint("price_min >= 0", name="ck_price_min_non_negative"),
        CheckConstraint(
            "price_max IS NULL OR price_max >= 0",
            name="ck_price_max_non_negative",
        ),
        CheckConstraint(
            "price_max IS NULL OR price_min <= price_max",
            name="ck_price_min_le_max",
        ),
        CheckConstraint("stock_qty IS NULL OR stock_qty >= 0", name="ck_stock_qty_non_negative"),
        CheckConstraint(
            "tier_min_qty IS NULL OR tier_min_qty >= 0",
            name="ck_tier_min_qty_non_negative",
        ),
        CheckConstraint(
            "tier_max_qty IS NULL OR tier_max_qty >= 0",
            name="ck_tier_max_qty_non_negative",
        ),
        CheckConstraint(
            "(tier_min_qty IS NULL AND tier_max_qty IS NULL) OR "
            "(tier_min_qty IS NOT NULL AND tier_max_qty IS NOT NULL AND tier_min_qty <= tier_max_qty)",
            name="ck_tier_consistency",
        ),
    )

    supplier_item_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    import_batch_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    raw_row_id: Mapped[UUID | None] = mapped_column(nullable=True)

    # Product attributes
    length_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pack_type: Mapped[str | None] = mapped_column(String, nullable=True)
    pack_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Pricing
    price_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=PriceType.FIXED.value,
    )
    price_min: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")

    # Tier pricing
    tier_min_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tier_max_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Availability
    availability: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=AvailabilityType.UNKNOWN.value,
    )
    stock_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Validation
    validation: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=ValidationStatus.OK.value,
    )
    validation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str] = mapped_column(
        nullable=False,
        server_default="now()",
    )