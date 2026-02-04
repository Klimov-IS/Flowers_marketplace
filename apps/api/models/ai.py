"""AI-related models for normalization assistance."""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base, UUIDMixin


class AIRunType(str, Enum):
    """AI run type enum."""

    COLUMN_MAPPING = "column_mapping"
    ATTRIBUTE_EXTRACTION = "attribute_extraction"
    SKU_MATCH = "sku_match"
    COMBINED = "combined"


class AIRunStatus(str, Enum):
    """AI run status enum."""

    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class AISuggestionType(str, Enum):
    """AI suggestion type enum."""

    COLUMN_MAPPING = "column_mapping"
    ATTRIBUTE = "attribute"
    SKU_MATCH = "sku_match"


class AISuggestionStatus(str, Enum):
    """AI suggestion status enum."""

    PENDING = "pending"
    AUTO_APPLIED = "auto_applied"
    MANUAL_APPLIED = "manual_applied"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class AIRun(Base, UUIDMixin):
    """AI run - one AI invocation for an import batch."""

    __tablename__ = "ai_runs"

    supplier_id: Mapped[UUID] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
    )
    import_batch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    run_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AIRunType.COMBINED.value,
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="deepseek-chat",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AIRunStatus.CREATED.value,
    )
    row_count: Mapped[int | None] = mapped_column(nullable=True)
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tokens_input: Mapped[int | None] = mapped_column(nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default="now()",
    )

    # Relationships
    suggestions: Mapped[list["AISuggestion"]] = relationship(
        "AISuggestion",
        back_populates="ai_run",
        cascade="all, delete-orphan",
    )


class AISuggestion(Base, UUIDMixin):
    """AI suggestion - individual suggestion per row/field."""

    __tablename__ = "ai_suggestions"

    ai_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    suggestion_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    target_entity: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # supplier_item | offer_candidate
    target_id: Mapped[UUID | None] = mapped_column(nullable=True)
    row_index: Mapped[int | None] = mapped_column(nullable=True)
    field_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    suggested_value: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )  # 0.000 to 1.000
    applied_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AISuggestionStatus.PENDING.value,
    )
    applied_at: Mapped[datetime | None] = mapped_column(nullable=True)
    applied_by: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )  # system | seller | admin
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default="now()",
    )

    # Relationships
    ai_run: Mapped["AIRun"] = relationship("AIRun", back_populates="suggestions")
