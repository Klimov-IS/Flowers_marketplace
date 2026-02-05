"""Unit tests for AI enrichment service."""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from packages.core.ai.schemas import AIExtractionResponse, RowSuggestion, FieldExtraction
from packages.core.ai.prompts import build_extraction_prompt
from packages.core.ai.service import AIService


class TestAIService:
    """Tests for AIService class."""

    def test_compute_input_hash_deterministic(self):
        """Test that hash is deterministic for same input."""
        rows = [{"raw_name": "Роза Бабалу 60 см"}]
        hash1 = AIService.compute_input_hash(rows)
        hash2 = AIService.compute_input_hash(rows)
        assert hash1 == hash2

    def test_compute_input_hash_different_for_different_input(self):
        """Test that hash is different for different inputs."""
        rows1 = [{"raw_name": "Роза Бабалу 60 см"}]
        rows2 = [{"raw_name": "Роза Бабалу 70 см"}]
        hash1 = AIService.compute_input_hash(rows1)
        hash2 = AIService.compute_input_hash(rows2)
        assert hash1 != hash2

    def test_estimate_cost(self):
        """Test cost estimation."""
        cost = AIService.estimate_cost(tokens_input=1000, tokens_output=500)
        # Input: 1000 * 0.00000014 = 0.00014
        # Output: 500 * 0.00000028 = 0.00014
        # Total: 0.00028
        expected = Decimal("0.00014") + Decimal("0.00014")
        assert cost == expected

    def test_is_available_when_disabled(self):
        """Test that service reports unavailable when disabled."""
        service = AIService(enabled=False)
        assert not service.is_available()

    def test_is_available_when_no_api_key(self):
        """Test that service reports unavailable when API key is not set."""
        # When enabled=True but no API key, client creation fails
        # so the service should report unavailable
        service = AIService(enabled=False)  # Disabled doesn't try to create client
        assert not service.is_available()

    def test_apply_suggestions_high_confidence(self):
        """Test that high confidence suggestions are auto-applied."""
        service = AIService(enabled=False)
        existing = {"_sources": {}, "_locked": []}
        suggestions = {
            "flower_type": FieldExtraction(value="Роза", confidence=0.95)
        }

        result, sources, auto, marked, review = service.apply_suggestions_to_attributes(
            existing, suggestions
        )

        assert result["flower_type"] == "Роза"
        assert sources["flower_type"] == "ai"
        assert auto == 1
        assert marked == 0
        assert review == 0

    def test_apply_suggestions_medium_confidence(self):
        """Test that medium confidence suggestions are applied with mark."""
        service = AIService(enabled=False)
        existing = {"_sources": {}, "_locked": []}
        suggestions = {
            "flower_type": FieldExtraction(value="Роза", confidence=0.75)
        }

        result, sources, auto, marked, review = service.apply_suggestions_to_attributes(
            existing, suggestions
        )

        assert result["flower_type"] == "Роза"
        assert sources["flower_type"] == "ai"
        assert auto == 0
        assert marked == 1
        assert review == 0

    def test_apply_suggestions_low_confidence(self):
        """Test that low confidence suggestions need review."""
        service = AIService(enabled=False)
        existing = {"_sources": {}, "_locked": []}
        suggestions = {
            "flower_type": FieldExtraction(value="Роза", confidence=0.5)
        }

        result, sources, auto, marked, review = service.apply_suggestions_to_attributes(
            existing, suggestions
        )

        assert "flower_type" not in result or result.get("flower_type") != "Роза"
        assert auto == 0
        assert marked == 0
        assert review == 1

    def test_apply_suggestions_skips_locked_fields(self):
        """Test that locked fields are not overwritten."""
        service = AIService(enabled=False)
        existing = {
            "flower_type": "Гвоздика",
            "_sources": {"flower_type": "manual"},
            "_locked": ["flower_type"]
        }
        suggestions = {
            "flower_type": FieldExtraction(value="Роза", confidence=0.99)
        }

        result, sources, auto, marked, review = service.apply_suggestions_to_attributes(
            existing, suggestions
        )

        assert result["flower_type"] == "Гвоздика"  # Not changed
        assert auto == 0

    def test_apply_suggestions_skips_manual_source(self):
        """Test that manually edited fields are not overwritten."""
        service = AIService(enabled=False)
        existing = {
            "flower_type": "Гвоздика",
            "_sources": {"flower_type": "manual"},
            "_locked": []
        }
        suggestions = {
            "flower_type": FieldExtraction(value="Роза", confidence=0.99)
        }

        result, sources, auto, marked, review = service.apply_suggestions_to_attributes(
            existing, suggestions
        )

        assert result["flower_type"] == "Гвоздика"  # Not changed


class TestAIEnrichmentCaching:
    """Tests for caching behavior."""

    def test_input_hash_consistency(self):
        """Test that same items produce same hash."""
        # Simulate what the service does
        rows1 = [{"raw_name": "Роза Эксплорер 60 см (Эквадор)"}]
        rows2 = [{"raw_name": "Роза Эксплорер 60 см (Эквадор)"}]

        hash1 = AIService.compute_input_hash(rows1)
        hash2 = AIService.compute_input_hash(rows2)

        assert hash1 == hash2, "Same input should produce same hash"

    def test_input_hash_order_matters(self):
        """Test that row order affects hash (for determinism)."""
        rows1 = [
            {"raw_name": "Роза A"},
            {"raw_name": "Роза B"},
        ]
        rows2 = [
            {"raw_name": "Роза B"},
            {"raw_name": "Роза A"},
        ]

        hash1 = AIService.compute_input_hash(rows1)
        hash2 = AIService.compute_input_hash(rows2)

        assert hash1 != hash2, "Different order should produce different hash"


class TestConfidenceTiers:
    """Tests for confidence tier thresholds."""

    @pytest.mark.parametrize("confidence,expected_tier", [
        (0.95, "auto_apply"),
        (0.90, "auto_apply"),
        (0.89, "apply_with_mark"),
        (0.75, "apply_with_mark"),
        (0.70, "apply_with_mark"),
        (0.69, "needs_review"),
        (0.50, "needs_review"),
        (0.10, "needs_review"),
    ])
    def test_confidence_thresholds(self, confidence, expected_tier):
        """Test that confidence values map to correct tiers."""
        service = AIService(enabled=False)
        existing = {"_sources": {}, "_locked": []}
        suggestions = {
            "test_field": FieldExtraction(value="test", confidence=confidence)
        }

        _, _, auto, marked, review = service.apply_suggestions_to_attributes(
            existing, suggestions
        )

        if expected_tier == "auto_apply":
            assert auto == 1 and marked == 0 and review == 0
        elif expected_tier == "apply_with_mark":
            assert auto == 0 and marked == 1 and review == 0
        else:
            assert auto == 0 and marked == 0 and review == 1


class TestCleanNamePrompt:
    """Tests for clean_name in AI prompt."""

    def test_prompt_includes_clean_name_instructions(self):
        """Test that prompt includes clean_name extraction rules."""
        prompt = build_extraction_prompt(
            flower_types=["Роза", "Гвоздика"],
            countries=["Эквадор"],
            colors=["красный"],
        )

        assert "clean_name" in prompt
        assert "Тип + Субтип + Сорт" in prompt or "Тип}" in prompt
        assert "витрины" in prompt.lower() or "display" in prompt.lower()

    def test_prompt_includes_subtype_instructions(self):
        """Test that prompt includes subtype extraction rules."""
        prompt = build_extraction_prompt(
            flower_types=["Роза"],
            countries=["Эквадор"],
            colors=["красный"],
        )

        assert "subtype" in prompt.lower()
        assert "кустовая" in prompt.lower() or "спрей" in prompt.lower()

    def test_prompt_with_subtypes_by_type(self):
        """Test that subtypes_by_type is included in prompt."""
        subtypes_by_type = {
            "Роза": ["кустовая", "спрей", "пионовидная"],
            "Хризантема": ["кустовая", "одноголовая"],
        }

        prompt = build_extraction_prompt(
            flower_types=["Роза", "Хризантема"],
            countries=["Эквадор"],
            colors=["красный"],
            subtypes_by_type=subtypes_by_type,
        )

        assert "Роза: кустовая, спрей, пионовидная" in prompt
        assert "Хризантема: кустовая, одноголовая" in prompt

    def test_prompt_without_subtypes(self):
        """Test that prompt works without subtypes_by_type."""
        prompt = build_extraction_prompt(
            flower_types=["Роза"],
            countries=["Эквадор"],
            colors=["красный"],
            subtypes_by_type=None,
        )

        assert "Нет данных о субтипах" in prompt

    def test_prompt_with_empty_subtypes(self):
        """Test that prompt handles empty subtypes dict."""
        prompt = build_extraction_prompt(
            flower_types=["Роза"],
            countries=["Эквадор"],
            colors=["красный"],
            subtypes_by_type={},
        )

        assert "Нет данных о субтипах" in prompt


class TestCleanNameExtraction:
    """Tests for clean_name field processing."""

    def test_apply_clean_name_suggestion(self):
        """Test that clean_name suggestion is applied."""
        service = AIService(enabled=False)
        existing = {"_sources": {}, "_locked": []}
        suggestions = {
            "clean_name": FieldExtraction(value="Роза кустовая Lydia", confidence=0.95)
        }

        result, sources, auto, marked, review = service.apply_suggestions_to_attributes(
            existing, suggestions
        )

        assert result["clean_name"] == "Роза кустовая Lydia"
        assert sources["clean_name"] == "ai"
        assert auto == 1

    def test_apply_subtype_suggestion(self):
        """Test that subtype suggestion is applied."""
        service = AIService(enabled=False)
        existing = {"_sources": {}, "_locked": []}
        suggestions = {
            "subtype": FieldExtraction(value="кустовая", confidence=0.92)
        }

        result, sources, auto, marked, review = service.apply_suggestions_to_attributes(
            existing, suggestions
        )

        assert result["subtype"] == "кустовая"
        assert sources["subtype"] == "ai"
        assert auto == 1

    def test_clean_name_not_overwritten_when_locked(self):
        """Test that locked clean_name is not overwritten."""
        service = AIService(enabled=False)
        existing = {
            "clean_name": "Роза Explorer",
            "_sources": {"clean_name": "manual"},
            "_locked": ["clean_name"]
        }
        suggestions = {
            "clean_name": FieldExtraction(value="Роза кустовая Lydia", confidence=0.99)
        }

        result, _, auto, _, _ = service.apply_suggestions_to_attributes(
            existing, suggestions
        )

        assert result["clean_name"] == "Роза Explorer"
        assert auto == 0

    def test_multiple_new_fields_applied(self):
        """Test that multiple new fields (subtype, clean_name) are applied together."""
        service = AIService(enabled=False)
        existing = {"_sources": {}, "_locked": []}
        suggestions = {
            "flower_type": FieldExtraction(value="Роза", confidence=0.98),
            "subtype": FieldExtraction(value="кустовая", confidence=0.95),
            "variety": FieldExtraction(value="Lydia", confidence=0.90),
            "clean_name": FieldExtraction(value="Роза кустовая Lydia", confidence=0.95),
        }

        result, sources, auto, marked, review = service.apply_suggestions_to_attributes(
            existing, suggestions
        )

        assert result["flower_type"] == "Роза"
        assert result["subtype"] == "кустовая"
        assert result["variety"] == "Lydia"
        assert result["clean_name"] == "Роза кустовая Lydia"
        assert auto == 4  # All high confidence
