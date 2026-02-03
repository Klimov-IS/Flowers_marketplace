"""Unit tests for normalization logic."""
from decimal import Decimal

import pytest

from packages.core.normalization.confidence import calculate_confidence, variety_similarity
from packages.core.normalization.detection import detect_product_type, detect_variety
from packages.core.normalization.tokens import normalize_tokens, remove_stopwords


class TestNormalization:
    """Tests for token normalization."""

    def test_normalize_tokens_basic(self):
        """Test basic normalization."""
        text = "Rose Explorer 60cm (Ecuador) 120rub"
        result = normalize_tokens(text)
        assert result == "rose explorer 60cm (ecuador) 120rub"

    def test_normalize_tokens_cyrillic(self):
        """Test Cyrillic normalization."""
        text = "Роза Эксплорер 60см (Эквадор) 120руб"
        result = normalize_tokens(text)
        assert "роза" in result.lower()
        assert "эксплорер" in result.lower()

    def test_normalize_tokens_special_chars(self):
        """Test special character removal."""
        text = "Rose! @#$ Explorer*** 60cm"
        result = normalize_tokens(text)
        # Should remove most special chars except meaningful ones
        assert "rose" in result
        assert "explorer" in result
        assert "@#$" not in result

    def test_normalize_tokens_whitespace(self):
        """Test whitespace normalization."""
        text = "Rose    Explorer   60cm"
        result = normalize_tokens(text)
        assert "  " not in result  # No double spaces

    def test_remove_stopwords(self):
        """Test stopword removal."""
        text = "rose explorer price 120 rub"
        stopwords = {"price", "rub"}
        result = remove_stopwords(text, stopwords)
        assert "price" not in result
        assert "rub" not in result
        assert "rose" in result
        assert "explorer" in result


class TestDetection:
    """Tests for product type and variety detection."""

    def test_detect_product_type_exact(self):
        """Test product type detection with exact match."""
        text = "rose explorer 60cm"
        product_type_dict = {
            "rose": {"value": "rose", "synonyms": ["роза", "roses"]},
        }
        result = detect_product_type(text, product_type_dict)
        assert result == "rose"

    def test_detect_product_type_synonym(self):
        """Test product type detection with synonym."""
        text = "роза explorer 60cm"
        product_type_dict = {
            "rose": {"value": "rose", "synonyms": ["роза", "roses"]},
        }
        result = detect_product_type(text, product_type_dict)
        assert result == "rose"

    def test_detect_product_type_not_found(self):
        """Test product type detection when not found."""
        text = "unknown item"
        product_type_dict = {
            "rose": {"value": "rose", "synonyms": ["роза"]},
        }
        result = detect_product_type(text, product_type_dict)
        assert result is None

    def test_detect_variety_single_token(self):
        """Test variety detection with consecutive capitalized words."""
        text = "Rose Explorer 60cm"
        result = detect_variety(text)
        # Extracts "Rose Explorer" as single multi-word token
        assert result == "Rose Explorer"

    def test_detect_variety_multi_word(self):
        """Test variety detection with multi-word variety."""
        text = "Rose Pink Floyd 60cm"
        result = detect_variety(text)
        # Extracts "Rose Pink Floyd" as single multi-word token
        assert result == "Rose Pink Floyd"

    def test_detect_variety_with_alias(self):
        """Test variety detection with alias."""
        text = "Mondial 60cm"  # Just variety name, no product type
        variety_alias_dict = {
            "mondial": {"value": "Mondial", "synonyms": ["мондиаль"]},
        }
        result = detect_variety(text, variety_alias_dict)
        # "Mondial" extracted, matches alias key, returns canonical value
        assert result == "Mondial"

    def test_detect_variety_not_found(self):
        """Test variety detection when no Latin tokens."""
        text = "роза 60см"
        result = detect_variety(text)
        assert result is None


class TestConfidenceScoring:
    """Tests for confidence scoring."""

    def test_base_confidence(self):
        """Test base confidence with no matches."""
        result = calculate_confidence()
        assert result == Decimal("0.10")

    def test_product_type_match(self):
        """Test confidence with product_type match."""
        result = calculate_confidence(product_type_match=True)
        assert result == Decimal("0.40")  # 0.10 + 0.30

    def test_exact_variety_match(self):
        """Test confidence with exact variety match."""
        result = calculate_confidence(
            product_type_match=True,
            variety_match="exact",
        )
        assert result == Decimal("0.85")  # 0.10 + 0.30 + 0.45

    def test_high_variety_similarity(self):
        """Test confidence with high variety similarity."""
        result = calculate_confidence(
            product_type_match=True,
            variety_match="high",
        )
        assert result == Decimal("0.70")  # 0.10 + 0.30 + 0.30

    def test_low_variety_similarity(self):
        """Test confidence with low variety similarity."""
        result = calculate_confidence(
            product_type_match=True,
            variety_match="low",
        )
        assert result == Decimal("0.50")  # 0.10 + 0.30 + 0.10

    def test_negative_signals_mix(self):
        """Test confidence with mix keyword."""
        result = calculate_confidence(
            product_type_match=True,
            has_mix_keyword=True,
        )
        assert result == Decimal("0.15")  # 0.10 + 0.30 - 0.25

    def test_negative_signals_short_name(self):
        """Test confidence with short name."""
        result = calculate_confidence(
            product_type_match=True,
            name_too_short=True,
        )
        assert result == Decimal("0.30")  # 0.10 + 0.30 - 0.10

    def test_combined_signals(self):
        """Test confidence with multiple positive signals."""
        result = calculate_confidence(
            product_type_match=True,
            variety_match="exact",
            subtype_match=True,
            country_match=True,
        )
        assert result == Decimal("0.95")  # 0.10 + 0.30 + 0.45 + 0.05 + 0.05

    def test_clamping_to_zero(self):
        """Test confidence clamping to zero."""
        result = calculate_confidence(
            product_type_match=False,
            has_mix_keyword=True,
            name_too_short=True,
            conflicting_product_type=True,
        )
        assert result >= Decimal("0.00")

    def test_clamping_to_one(self):
        """Test confidence doesn't exceed 1.0."""
        result = calculate_confidence(
            product_type_match=True,
            variety_match="exact",
            subtype_match=True,
            country_match=True,
        )
        assert result <= Decimal("1.00")


class TestVarietySimilarity:
    """Tests for variety similarity calculation."""

    def test_exact_match(self):
        """Test exact variety match."""
        result = variety_similarity("Explorer", "Explorer")
        assert result == "exact"

    def test_exact_match_case_insensitive(self):
        """Test exact match case insensitive."""
        result = variety_similarity("Explorer", "explorer")
        assert result == "exact"

    def test_one_contains_other(self):
        """Test when one variety contains the other."""
        result = variety_similarity("Explorer", "Explorer Rose")
        assert result == "high"

    def test_high_token_overlap(self):
        """Test high token overlap."""
        result = variety_similarity("Pink Floyd Rose", "Pink Floyd")
        assert result == "high"

    def test_low_token_overlap(self):
        """Test low token overlap."""
        # 1 overlap (Pink) out of 3 total = 33%, which is < 40% = none
        result = variety_similarity("Pink Rose", "Pink Floyd")
        assert result == "none"

    def test_no_overlap(self):
        """Test no token overlap."""
        result = variety_similarity("Explorer", "Mondial")
        assert result == "none"

    def test_none_variety(self):
        """Test with None variety."""
        result = variety_similarity(None, "Explorer")
        assert result == "none"
