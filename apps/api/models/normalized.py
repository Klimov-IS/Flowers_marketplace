"""Normalized layer models: SKUs, dictionary, mappings, tasks."""
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from apps.api.models.parties import Supplier


class DictionaryStatus(str, Enum):
    """Dictionary entry status."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"


class MappingMethod(str, Enum):
    """SKU mapping method."""

    RULE = "rule"
    MANUAL = "manual"
    SEMANTIC = "semantic"


class MappingStatus(str, Enum):
    """SKU mapping status."""

    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class TaskStatus(str, Enum):
    """Normalization task status."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class NormalizedSKU(Base, UUIDMixin, TimestampMixin):
    """Normalized SKU - canonical product card."""

    __tablename__ = "normalized_skus"

    product_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    variety: Mapped[str | None] = mapped_column(String, nullable=True)
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Relationships
    offers: Mapped[list["Offer"]] = relationship("Offer", back_populates="normalized_sku")


class DictionaryEntry(Base, UUIDMixin, TimestampMixin):
    """Dictionary entry for normalization rules and synonyms."""

    __tablename__ = "dictionary_entries"
    __table_args__ = (UniqueConstraint("dict_type", "key", name="uq_dictionary_entries_type_key"),)

    dict_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    synonyms: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    rules: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=DictionaryStatus.ACTIVE.value,
    )


class SKUMapping(Base, UUIDMixin, TimestampMixin):
    """Mapping between supplier item and normalized SKU."""

    __tablename__ = "sku_mappings"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_sku_mappings_confidence_range",
        ),
    )

    supplier_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("supplier_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    normalized_sku_id: Mapped[UUID] = mapped_column(
        ForeignKey("normalized_skus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    method: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=MappingMethod.RULE.value,
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
        default=Decimal("0.000"),
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=MappingStatus.PROPOSED.value,
        index=True,
    )
    decided_by: Mapped[UUID | None] = mapped_column(nullable=True)
    decided_at: Mapped[str | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class NormalizationTask(Base, UUIDMixin, TimestampMixin):
    """Manual review task for normalization."""

    __tablename__ = "normalization_tasks"

    supplier_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("supplier_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=TaskStatus.OPEN.value,
        index=True,
    )
    assigned_to: Mapped[UUID | None] = mapped_column(nullable=True)


class Offer(Base, UUIDMixin, TimestampMixin):
    """Published offer for retail."""

    __tablename__ = "offers"
    __table_args__ = (
        CheckConstraint("length_cm IS NULL OR length_cm > 0", name="ck_offers_length_cm_positive"),
        CheckConstraint("pack_qty IS NULL OR pack_qty > 0", name="ck_offers_pack_qty_positive"),
        CheckConstraint("price_min >= 0", name="ck_offers_price_min_non_negative"),
        CheckConstraint(
            "price_max IS NULL OR price_max >= 0",
            name="ck_offers_price_max_non_negative",
        ),
        CheckConstraint(
            "price_max IS NULL OR price_min <= price_max",
            name="ck_offers_price_min_le_max",
        ),
        CheckConstraint("stock_qty IS NULL OR stock_qty >= 0", name="ck_offers_stock_qty_non_negative"),
        CheckConstraint(
            "tier_min_qty IS NULL OR tier_min_qty >= 0",
            name="ck_offers_tier_min_qty_non_negative",
        ),
        CheckConstraint(
            "tier_max_qty IS NULL OR tier_max_qty >= 0",
            name="ck_offers_tier_max_qty_non_negative",
        ),
        CheckConstraint(
            "(tier_min_qty IS NULL AND tier_max_qty IS NULL) OR "
            "(tier_min_qty IS NOT NULL AND tier_max_qty IS NOT NULL AND tier_min_qty <= tier_max_qty)",
            name="ck_offers_tier_consistency",
        ),
    )

    supplier_id: Mapped[UUID] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    normalized_sku_id: Mapped[UUID] = mapped_column(
        ForeignKey("normalized_skus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_import_batch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Product attributes
    length_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pack_type: Mapped[str | None] = mapped_column(String, nullable=True)
    pack_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Pricing
    price_type: Mapped[str] = mapped_column(String, nullable=False, default="fixed")
    price_min: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")

    # Tier pricing
    tier_min_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tier_max_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Availability
    availability: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    stock_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Display
    display_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Clean name for display (Тип + Субтип + Сорт)",
    )

    # Publishing
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, index=True)
    published_at: Mapped[str] = mapped_column(nullable=False, server_default="now()")

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="offers")
    normalized_sku: Mapped["NormalizedSKU"] = relationship("NormalizedSKU", back_populates="offers")


class SupplierDeliveryRule(Base, UUIDMixin, TimestampMixin):
    """Supplier delivery rules and conditions."""

    __tablename__ = "supplier_delivery_rules"
    __table_args__ = (
        CheckConstraint(
            "min_order_amount IS NULL OR min_order_amount >= 0",
            name="ck_supplier_delivery_rules_min_order_amount",
        ),
        CheckConstraint(
            "min_order_qty IS NULL OR min_order_qty >= 0",
            name="ck_supplier_delivery_rules_min_order_qty",
        ),
    )

    supplier_id: Mapped[UUID] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    city_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cities.id", ondelete="SET NULL"),
        nullable=True,
    )
    delivery_zone: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    min_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    min_order_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_windows: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
