"""Flower catalog models: types, subtypes, varieties, synonyms.

Hierarchical structure:
  FlowerCategory (optional)
    └── FlowerType (Роза, Хризантема)
          ├── FlowerSubtype (Кустовая, Спрей)
          └── FlowerVariety (Explorer, Freedom)
"""
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base, TimestampMixin, UUIDMixin


class FlowerCategory(Base, UUIDMixin, TimestampMixin):
    """Flower category: Cut flowers, Greenery, Dried flowers."""

    __tablename__ = "flower_categories"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_flower_categories_slug"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    types: Mapped[list["FlowerType"]] = relationship(
        "FlowerType",
        back_populates="category",
        lazy="selectin",
    )


class FlowerType(Base, UUIDMixin, TimestampMixin):
    """Flower type: Rose, Chrysanthemum, Eucalyptus."""

    __tablename__ = "flower_types"
    __table_args__ = (
        UniqueConstraint("canonical_name", name="uq_flower_types_canonical_name"),
        UniqueConstraint("slug", name="uq_flower_types_slug"),
    )

    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("flower_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    canonical_name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    meta: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, index=True)

    # Relationships
    category: Mapped["FlowerCategory | None"] = relationship(
        "FlowerCategory",
        back_populates="types",
    )
    subtypes: Mapped[list["FlowerSubtype"]] = relationship(
        "FlowerSubtype",
        back_populates="flower_type",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    synonyms: Mapped[list["TypeSynonym"]] = relationship(
        "TypeSynonym",
        back_populates="flower_type",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    varieties: Mapped[list["FlowerVariety"]] = relationship(
        "FlowerVariety",
        back_populates="flower_type",
        lazy="noload",
    )


class FlowerSubtype(Base, UUIDMixin, TimestampMixin):
    """Flower subtype: Shrub, Spray, Peony-style."""

    __tablename__ = "flower_subtypes"
    __table_args__ = (
        UniqueConstraint("type_id", "slug", name="uq_flower_subtypes_type_slug"),
    )

    type_id: Mapped[UUID] = mapped_column(
        ForeignKey("flower_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False)
    meta: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    # Relationships
    flower_type: Mapped["FlowerType"] = relationship(
        "FlowerType",
        back_populates="subtypes",
    )
    synonyms: Mapped[list["SubtypeSynonym"]] = relationship(
        "SubtypeSynonym",
        back_populates="subtype",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class TypeSynonym(Base, UUIDMixin):
    """Synonyms for flower types: роза, розы, rose -> Роза."""

    __tablename__ = "type_synonyms"
    __table_args__ = (
        UniqueConstraint("synonym", name="uq_type_synonyms_synonym"),
        CheckConstraint("synonym = lower(synonym)", name="ck_type_synonyms_lowercase"),
    )

    type_id: Mapped[UUID] = mapped_column(
        ForeignKey("flower_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    synonym: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    # Relationships
    flower_type: Mapped["FlowerType"] = relationship(
        "FlowerType",
        back_populates="synonyms",
    )


class SubtypeSynonym(Base, UUIDMixin):
    """Synonyms for flower subtypes: кустовая, куст, shrub -> Кустовая."""

    __tablename__ = "subtype_synonyms"
    __table_args__ = (
        UniqueConstraint("subtype_id", "synonym", name="uq_subtype_synonyms_subtype_synonym"),
        CheckConstraint("synonym = lower(synonym)", name="ck_subtype_synonyms_lowercase"),
    )

    subtype_id: Mapped[UUID] = mapped_column(
        ForeignKey("flower_subtypes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    synonym: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    # Relationships
    subtype: Mapped["FlowerSubtype"] = relationship(
        "FlowerSubtype",
        back_populates="synonyms",
    )


class FlowerVariety(Base, UUIDMixin, TimestampMixin):
    """Flower variety: Explorer, Freedom, Red Naomi."""

    __tablename__ = "flower_varieties"
    __table_args__ = (
        UniqueConstraint("type_id", "slug", name="uq_flower_varieties_type_slug"),
        CheckConstraint(
            "typical_length_min IS NULL OR typical_length_min > 0",
            name="ck_flower_varieties_length_min_positive",
        ),
        CheckConstraint(
            "typical_length_max IS NULL OR typical_length_max > 0",
            name="ck_flower_varieties_length_max_positive",
        ),
        CheckConstraint(
            "typical_length_min IS NULL OR typical_length_max IS NULL OR typical_length_min <= typical_length_max",
            name="ck_flower_varieties_length_range",
        ),
    )

    type_id: Mapped[UUID] = mapped_column(
        ForeignKey("flower_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subtype_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("flower_subtypes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)

    # Known attributes
    official_colors: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    typical_length_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    typical_length_max: Mapped[int | None] = mapped_column(Integer, nullable=True)

    meta: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    is_verified: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, index=True)

    # Relationships
    flower_type: Mapped["FlowerType"] = relationship(
        "FlowerType",
        back_populates="varieties",
    )
    subtype: Mapped["FlowerSubtype | None"] = relationship("FlowerSubtype")
    synonyms: Mapped[list["VarietySynonym"]] = relationship(
        "VarietySynonym",
        back_populates="variety",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class VarietySynonym(Base, UUIDMixin):
    """Synonyms for varieties: эксплорер -> Explorer."""

    __tablename__ = "variety_synonyms"
    __table_args__ = (
        UniqueConstraint("variety_id", "synonym", name="uq_variety_synonyms_variety_synonym"),
        CheckConstraint("synonym = lower(synonym)", name="ck_variety_synonyms_lowercase"),
    )

    variety_id: Mapped[UUID] = mapped_column(
        ForeignKey("flower_varieties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    synonym: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    # Relationships
    variety: Mapped["FlowerVariety"] = relationship(
        "FlowerVariety",
        back_populates="synonyms",
    )
