"""Import and parsing models."""
from datetime import date, datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.models.base import Base, TimestampMixin, UUIDMixin


class SourceType(str, Enum):
    """Source type enum."""

    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"
    IMAGE = "image"
    API = "api"
    OTHER = "other"


class ImportBatchStatus(str, Enum):
    """Import batch status enum."""

    RECEIVED = "received"
    PARSED = "parsed"
    PUBLISHED = "published"
    FAILED = "failed"


class RawRowKind(str, Enum):
    """Raw row kind enum."""

    DATA = "data"
    HEADER = "header"
    GROUP = "group"
    COMMENT = "comment"
    EMPTY = "empty"


class ParseSeverity(str, Enum):
    """Parse event severity enum."""

    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class ImportBatch(Base, UUIDMixin, TimestampMixin):
    """Import batch - one price list upload."""

    __tablename__ = "import_batches"

    supplier_id: Mapped[UUID] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=SourceType.OTHER.value,
    )
    source_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    declared_effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=ImportBatchStatus.RECEIVED.value,
    )
    imported_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default="now()",
    )
    meta: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )


class RawRow(Base, UUIDMixin):
    """Raw row - immutable source data."""

    __tablename__ = "raw_rows"

    import_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    row_kind: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=RawRowKind.DATA.value,
    )
    row_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_cells: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default="now()",
    )


class ParseRun(Base, UUIDMixin):
    """Parse run - one parsing execution."""

    __tablename__ = "parse_runs"

    import_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    parser_version: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default="now()",
    )
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    summary: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )


class ParseEvent(Base, UUIDMixin):
    """Parse event - errors and warnings during parsing."""

    __tablename__ = "parse_events"

    parse_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("parse_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_row_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("raw_rows.id", ondelete="SET NULL"),
        nullable=True,
    )
    severity: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=ParseSeverity.INFO.value,
    )
    code: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default="now()",
    )