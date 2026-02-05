"""Pydantic schemas for AI service input/output."""
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FieldExtraction(BaseModel):
    """Single field extraction with confidence."""

    value: Any
    confidence: float = Field(ge=0.0, le=1.0)


class RowSuggestion(BaseModel):
    """AI suggestions for a single row."""

    row_index: int
    extracted: dict[str, FieldExtraction] = Field(default_factory=dict)
    needs_review: bool = False
    rationale: Optional[str] = None


class ColumnMapping(BaseModel):
    """Column mapping suggestion."""

    source_index: int
    target_field: str
    confidence: float = Field(ge=0.0, le=1.0)


class ParserExtracted(BaseModel):
    """What the deterministic parser already extracted."""

    flower_type: Optional[str] = None
    subtype: Optional[str] = None  # кустовая, спрей, пионовидная...
    variety: Optional[str] = None
    origin_country: Optional[str] = None
    length_cm: Optional[int] = None
    colors: list[str] = Field(default_factory=list)
    farm: Optional[str] = None
    clean_name: Optional[str] = None  # Чистое название: Тип + Субтип + Сорт


class RowInput(BaseModel):
    """Input row for AI processing."""

    row_index: int
    raw_name: str
    cells: list[str] = Field(default_factory=list)
    parser_extracted: Optional[ParserExtracted] = None
    supplier_item_id: Optional[str] = None


class KnownValues(BaseModel):
    """Known values for validation/suggestion."""

    flower_types: list[str] = Field(default_factory=list)
    subtypes_by_type: dict[str, list[str]] = Field(default_factory=dict)  # {"Роза": ["кустовая", "спрей"]}
    countries: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)


class AIExtractionRequest(BaseModel):
    """Request to AI for attribute extraction."""

    task: str = "extract_attributes"
    supplier_id: Optional[str] = None
    import_batch_id: Optional[str] = None
    headers: list[str] = Field(default_factory=list)
    rows: list[RowInput]
    known_values: KnownValues = Field(default_factory=KnownValues)


class AIExtractionResponse(BaseModel):
    """Response from AI with extraction results."""

    column_mapping: list[ColumnMapping] = Field(default_factory=list)
    row_suggestions: list[RowSuggestion] = Field(default_factory=list)
    model_used: Optional[str] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None


class AIRunResult(BaseModel):
    """Result of an AI run operation."""

    status: str  # succeeded | failed | skipped
    ai_run_id: Optional[UUID] = None
    suggestions_count: int = 0
    applied_count: int = 0
    needs_review_count: int = 0
    reason: Optional[str] = None
    error: Optional[str] = None
