"""Unit tests for AI service."""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from packages.core.ai.schemas import (
    AIExtractionResponse,
    FieldExtraction,
    RowSuggestion,
)
from packages.core.ai.service import (
    AIService,
    CONFIDENCE_AUTO_APPLY,
    CONFIDENCE_APPLY_WITH_MARK,
)


class TestAIServiceConfidence:
    """Test confidence tier logic."""

    def test_auto_apply_high_confidence(self):
        """High confidence (>=0.90) should auto-apply."""
        service = AIService(enabled=False)  # Don't need client for this test

        existing = {"flower_type": "Роза", "_sources": {"flower_type": "parser"}}
        suggestions = {
            "origin_country": FieldExtraction(value="Эквадор", confidence=0.95),
        }

        result, sources, auto, marked, review = service.apply_suggestions_to_attributes(
            existing, suggestions
        )

        assert result["origin_country"] == "Эквадор"
        assert sources["origin_country"] == "ai"
        assert auto == 1
        assert marked == 0
        assert review == 0

    def test_apply_with_mark_medium_confidence(self):
        """Medium confidence (0.70-0.89) should apply with mark."""
        service = AIService(enabled=False)

        existing = {"_sources": {}}
        suggestions = {
            "flower_type": FieldExtraction(value="Гвоздика", confidence=0.75),
        }

        result, sources, auto, marked, review = service.apply_suggestions_to_attributes(
            existing, suggestions
        )

        assert result["flower_type"] == "Гвоздика"
        assert sources["flower_type"] == "ai"
        assert auto == 0
        assert marked == 1
        assert review == 0

    def test_needs_review_low_confidence(self):
        """Low confidence (<0.70) should not apply, needs review."""
        service = AIService(enabled=False)

        existing = {"_sources": {}}
        suggestions = {
            "variety": FieldExtraction(value="Бабалу", confidence=0.55),
        }

        result, sources, auto, marked, review = service.apply_suggestions_to_attributes(
            existing, suggestions
        )

        assert "variety" not in result or result.get("variety") != "Бабалу"
        assert auto == 0
        assert marked == 0
        assert review == 1

    def test_skip_locked_fields(self):
        """Locked fields should not be overwritten."""
        service = AIService(enabled=False)

        existing = {
            "origin_country": "Колумбия",
            "_sources": {"origin_country": "manual"},
            "_locked": ["origin_country"],
        }
        suggestions = {
            "origin_country": FieldExtraction(value="Эквадор", confidence=0.99),
        }

        result, sources, auto, marked, review = service.apply_suggestions_to_attributes(
            existing, suggestions
        )

        assert result["origin_country"] == "Колумбия"  # Not changed
        assert auto == 0

    def test_skip_manual_fields(self):
        """Manual fields should not be overwritten."""
        service = AIService(enabled=False)

        existing = {
            "colors": ["красный"],
            "_sources": {"colors": "manual"},
        }
        suggestions = {
            "colors": FieldExtraction(value=["белый"], confidence=0.95),
        }

        result, sources, auto, marked, review = service.apply_suggestions_to_attributes(
            existing, suggestions
        )

        assert result["colors"] == ["красный"]  # Not changed
        assert auto == 0


class TestAIServiceInputHash:
    """Test input hashing for caching."""

    def test_same_input_same_hash(self):
        """Same input should produce same hash."""
        rows = [{"row_index": 0, "raw_name": "Роза Бабалу 50 см"}]

        hash1 = AIService.compute_input_hash(rows)
        hash2 = AIService.compute_input_hash(rows)

        assert hash1 == hash2

    def test_different_input_different_hash(self):
        """Different input should produce different hash."""
        rows1 = [{"row_index": 0, "raw_name": "Роза Бабалу"}]
        rows2 = [{"row_index": 0, "raw_name": "Роза Фридом"}]

        hash1 = AIService.compute_input_hash(rows1)
        hash2 = AIService.compute_input_hash(rows2)

        assert hash1 != hash2


class TestAIServiceCost:
    """Test cost estimation."""

    def test_cost_estimation(self):
        """Test cost is calculated correctly."""
        # 1M input tokens = $0.14, 1M output tokens = $0.28
        cost = AIService.estimate_cost(1_000_000, 1_000_000)

        assert cost == Decimal("0.42")

    def test_small_cost(self):
        """Test small amounts."""
        # 1000 tokens each
        cost = AIService.estimate_cost(1000, 1000)

        # Input: 1000 * 0.00000014 = 0.00014
        # Output: 1000 * 0.00000028 = 0.00028
        # Total: 0.00042
        assert cost == Decimal("0.00042")


class TestAIServiceAvailability:
    """Test service availability checks."""

    def test_disabled_by_default(self):
        """Service should be disabled by default."""
        with patch.dict("os.environ", {"AI_ENABLED": "false"}):
            service = AIService()
            assert not service.is_available()

    def test_enabled_when_configured(self):
        """Service should be enabled when configured."""
        with patch.dict("os.environ", {
            "AI_ENABLED": "true",
            "DEEPSEEK_API_KEY": "test-key",
        }):
            service = AIService(enabled=True)
            # Client won't be created without proper init, but enabled flag is set
            assert service.enabled is True

    def test_max_rows_limit(self):
        """Should respect max rows limit."""
        with patch.dict("os.environ", {"AI_MAX_ROWS": "100"}):
            service = AIService()
            assert service.max_rows == 100


class TestAIServiceExtraction:
    """Test extraction flow with mocked client."""

    @pytest.mark.asyncio
    async def test_extract_attributes_parses_response(self):
        """Test that extraction parses API response correctly."""
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.model = "deepseek-chat"
        mock_client.extract_json = AsyncMock(return_value=(
            {
                "row_suggestions": [
                    {
                        "row_index": 0,
                        "extracted": {
                            "flower_type": {"value": "Роза", "confidence": 0.98},
                            "variety": {"value": "Бабалу", "confidence": 0.92},
                        },
                        "needs_review": False,
                        "rationale": "Standard format",
                    }
                ]
            },
            100,  # tokens_input
            50,   # tokens_output
        ))

        service = AIService(client=mock_client, enabled=True, max_rows=1000)
        rows = [{"row_index": 0, "raw_name": "Роза Бабалу 50 см"}]

        response = await service.extract_attributes(rows)

        assert len(response.row_suggestions) == 1
        suggestion = response.row_suggestions[0]
        assert suggestion.row_index == 0
        assert "flower_type" in suggestion.extracted
        assert suggestion.extracted["flower_type"].value == "Роза"
        assert suggestion.extracted["flower_type"].confidence == 0.98
        assert response.tokens_input == 100
        assert response.tokens_output == 50

    @pytest.mark.asyncio
    async def test_extract_raises_when_not_available(self):
        """Should raise error when AI is not available."""
        service = AIService(enabled=False)
        rows = [{"row_index": 0, "raw_name": "Test"}]

        with pytest.raises(ValueError, match="not available"):
            await service.extract_attributes(rows)

    @pytest.mark.asyncio
    async def test_extract_raises_on_too_many_rows(self):
        """Should raise error when too many rows."""
        mock_client = MagicMock()
        mock_client.is_available.return_value = True

        service = AIService(client=mock_client, enabled=True, max_rows=10)
        rows = [{"row_index": i, "raw_name": f"Row {i}"} for i in range(20)]

        with pytest.raises(ValueError, match="Too many rows"):
            await service.extract_attributes(rows)
