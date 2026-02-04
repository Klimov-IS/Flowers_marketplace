"""AI Service for normalization assistance."""
import hashlib
import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from packages.core.ai.client import DeepSeekClient, DeepSeekError
from packages.core.ai.prompts import build_extraction_prompt, build_user_extraction_prompt
from packages.core.ai.schemas import (
    AIExtractionRequest,
    AIExtractionResponse,
    AIRunResult,
    FieldExtraction,
    RowSuggestion,
)

# Default known values for flower domain
DEFAULT_FLOWER_TYPES = [
    "Роза", "Гвоздика", "Хризантема", "Сантини", "Эустома", "Альстромерия",
    "Гипсофила", "Илекс", "Калла", "Гербера", "Гортензия", "Пион",
    "Тюльпан", "Лилия", "Орхидея", "Статица", "Эвкалипт", "Рускус",
    "Гиперикум", "Ранункулюс", "Анемон", "Фрезия", "Ирис", "Нарцисс",
]

DEFAULT_COUNTRIES = [
    "Эквадор", "Колумбия", "Нидерланды", "Кения", "Израиль",
    "Россия", "Эфиопия", "Италия",
]

DEFAULT_COLORS = [
    "белый", "красный", "розовый", "желтый", "оранжевый", "синий",
    "фиолетовый", "лиловый", "сиреневый", "бордовый", "зеленый",
    "кремовый", "персиковый", "коралловый", "лавандовый", "пудровый",
    "биколор", "микс",
]

# Confidence thresholds
CONFIDENCE_AUTO_APPLY = 0.90
CONFIDENCE_APPLY_WITH_MARK = 0.70
CONFIDENCE_NEEDS_REVIEW = 0.70


class AIService:
    """Service for AI-assisted normalization."""

    def __init__(
        self,
        client: Optional[DeepSeekClient] = None,
        enabled: Optional[bool] = None,
        max_rows: Optional[int] = None,
    ):
        """
        Initialize AI service.

        Args:
            client: DeepSeek client instance (created if not provided)
            enabled: Whether AI is enabled (from AI_ENABLED env var)
            max_rows: Maximum rows to process (from AI_MAX_ROWS env var)
        """
        self.enabled = enabled if enabled is not None else (
            os.getenv("AI_ENABLED", "false").lower() == "true"
        )
        self.max_rows = max_rows or int(os.getenv("AI_MAX_ROWS", "5000"))

        if self.enabled:
            self.client = client or DeepSeekClient()
        else:
            self.client = None

    def is_available(self) -> bool:
        """Check if AI service is available."""
        return self.enabled and self.client is not None and self.client.is_available()

    async def extract_attributes(
        self,
        rows: list[dict],
        flower_types: Optional[list[str]] = None,
        countries: Optional[list[str]] = None,
        colors: Optional[list[str]] = None,
    ) -> AIExtractionResponse:
        """
        Extract attributes from rows using AI.

        Args:
            rows: List of dicts with 'row_index' and 'raw_name' keys
            flower_types: Known flower types (uses defaults if not provided)
            countries: Known countries (uses defaults if not provided)
            colors: Known colors (uses defaults if not provided)

        Returns:
            AIExtractionResponse with suggestions

        Raises:
            DeepSeekError: If API call fails
            ValueError: If AI is not available
        """
        if not self.is_available():
            raise ValueError("AI service is not available")

        if len(rows) > self.max_rows:
            raise ValueError(f"Too many rows: {len(rows)} > {self.max_rows}")

        # Use defaults if not provided
        flower_types = flower_types or DEFAULT_FLOWER_TYPES
        countries = countries or DEFAULT_COUNTRIES
        colors = colors or DEFAULT_COLORS

        # Build prompts
        system_prompt = build_extraction_prompt(flower_types, countries, colors)
        user_prompt = build_user_extraction_prompt(rows)

        # Call API
        response_data, tokens_in, tokens_out = await self.client.extract_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=4096,
        )

        # Parse response
        row_suggestions = []
        for item in response_data.get("row_suggestions", []):
            extracted = {}
            for field, value_data in item.get("extracted", {}).items():
                if isinstance(value_data, dict) and "value" in value_data:
                    extracted[field] = FieldExtraction(
                        value=value_data["value"],
                        confidence=value_data.get("confidence", 0.5),
                    )

            row_suggestions.append(RowSuggestion(
                row_index=item.get("row_index", 0),
                extracted=extracted,
                needs_review=item.get("needs_review", False),
                rationale=item.get("rationale"),
            ))

        return AIExtractionResponse(
            row_suggestions=row_suggestions,
            model_used=self.client.model,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
        )

    async def extract_attributes_batch(
        self,
        rows: list[dict],
        batch_size: int = 50,
        **kwargs,
    ) -> AIExtractionResponse:
        """
        Extract attributes in batches to avoid token limits.

        Args:
            rows: List of dicts with 'row_index' and 'raw_name' keys
            batch_size: Number of rows per batch
            **kwargs: Additional args passed to extract_attributes

        Returns:
            Combined AIExtractionResponse
        """
        all_suggestions = []
        total_tokens_in = 0
        total_tokens_out = 0

        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            response = await self.extract_attributes(batch, **kwargs)

            all_suggestions.extend(response.row_suggestions)
            total_tokens_in += response.tokens_input or 0
            total_tokens_out += response.tokens_output or 0

        return AIExtractionResponse(
            row_suggestions=all_suggestions,
            model_used=self.client.model if self.client else None,
            tokens_input=total_tokens_in,
            tokens_output=total_tokens_out,
        )

    def apply_suggestions_to_attributes(
        self,
        existing_attributes: dict,
        suggestions: dict[str, FieldExtraction],
    ) -> tuple[dict, dict[str, str], int, int, int]:
        """
        Apply AI suggestions to existing attributes based on confidence tiers.

        Args:
            existing_attributes: Current item attributes
            suggestions: Dict of field name to FieldExtraction

        Returns:
            Tuple of:
            - Updated attributes dict
            - Updated sources dict
            - Count of auto-applied
            - Count of applied with mark
            - Count of needs review
        """
        attributes = dict(existing_attributes)
        sources = attributes.get("_sources", {})
        locked = attributes.get("_locked", [])

        auto_applied = 0
        applied_with_mark = 0
        needs_review = 0

        for field, extraction in suggestions.items():
            # Skip locked fields
            if field in locked:
                continue

            # Skip if already has manual value
            if sources.get(field) == "manual":
                continue

            confidence = extraction.confidence

            if confidence >= CONFIDENCE_AUTO_APPLY:
                # Auto-apply high confidence
                attributes[field] = extraction.value
                sources[field] = "ai"
                auto_applied += 1

            elif confidence >= CONFIDENCE_APPLY_WITH_MARK:
                # Apply but mark as AI (reversible)
                attributes[field] = extraction.value
                sources[field] = "ai"
                applied_with_mark += 1

            else:
                # Low confidence - needs review
                needs_review += 1

        # Update metadata
        attributes["_sources"] = sources

        return attributes, sources, auto_applied, applied_with_mark, needs_review

    @staticmethod
    def compute_input_hash(rows: list[dict]) -> str:
        """Compute hash of input for caching."""
        content = json.dumps(rows, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def estimate_cost(tokens_input: int, tokens_output: int) -> Decimal:
        """
        Estimate cost in USD based on DeepSeek pricing.

        Pricing (as of 2024):
        - Input: $0.14 per 1M tokens
        - Output: $0.28 per 1M tokens
        """
        input_cost = Decimal(str(tokens_input)) * Decimal("0.00000014")
        output_cost = Decimal(str(tokens_output)) * Decimal("0.00000028")
        return input_cost + output_cost
