"""Unit tests for parsing functions."""
from decimal import Decimal

import pytest

from packages.core.parsing.attributes import extract_length_cm, extract_origin_country
from packages.core.parsing.price import parse_price


class TestPriceParser:
    """Tests for price parsing."""

    def test_parse_fixed_price(self):
        """Test parsing fixed price."""
        result = parse_price("100")
        assert result["price_type"] == "fixed"
        assert result["price_min"] == Decimal("100")
        assert result["price_max"] is None
        assert result["error"] is None

    def test_parse_fixed_price_with_decimal(self):
        """Test parsing fixed price with decimals."""
        result = parse_price("99.50")
        assert result["price_type"] == "fixed"
        assert result["price_min"] == Decimal("99.50")
        assert result["price_max"] is None

    def test_parse_price_range_hyphen(self):
        """Test parsing price range with hyphen."""
        result = parse_price("95-99")
        assert result["price_type"] == "range"
        assert result["price_min"] == Decimal("95")
        assert result["price_max"] == Decimal("99")
        assert result["error"] is None

    def test_parse_price_range_endash(self):
        """Test parsing price range with en-dash."""
        result = parse_price("95–99")
        assert result["price_type"] == "range"
        assert result["price_min"] == Decimal("95")
        assert result["price_max"] == Decimal("99")

    def test_parse_price_range_with_spaces(self):
        """Test parsing price range with spaces."""
        result = parse_price("95 - 99")
        assert result["price_type"] == "range"
        assert result["price_min"] == Decimal("95")
        assert result["price_max"] == Decimal("99")

    def test_parse_price_empty(self):
        """Test parsing empty price."""
        result = parse_price("")
        assert result["error"] == "Empty price"

    def test_parse_price_invalid(self):
        """Test parsing invalid price."""
        result = parse_price("abc")
        assert result["error"] is not None
        assert result["price_min"] is None

    def test_parse_price_negative(self):
        """Test parsing negative price."""
        result = parse_price("-100")
        assert result["error"] == "Negative price"

    def test_parse_price_range_reversed(self):
        """Test parsing price range where min > max."""
        result = parse_price("99-95")
        assert result["price_type"] == "range"
        assert result["error"] == "price_min > price_max"


class TestLengthExtractor:
    """Tests for length extraction."""

    def test_extract_length_cyrillic_cm(self):
        """Test extracting length with cyrillic 'см'."""
        assert extract_length_cm("Роза Explorer 60см") == 60

    def test_extract_length_latin_cm(self):
        """Test extracting length with latin 'cm'."""
        assert extract_length_cm("Rose Explorer 60cm") == 60

    def test_extract_length_with_space(self):
        """Test extracting length with space before unit."""
        assert extract_length_cm("Роза Explorer 60 см") == 60

    def test_extract_length_multiple_numbers(self):
        """Test extracting length when multiple numbers present."""
        # Should extract length pattern, not just any number
        assert extract_length_cm("Роза Explorer (10) 60см") == 60

    def test_extract_length_out_of_range(self):
        """Test that out-of-range lengths are rejected."""
        assert extract_length_cm("Роза 150см") is None  # Too long
        assert extract_length_cm("Роза 20см") is None  # Too short

    def test_extract_length_valid_range(self):
        """Test lengths within valid range."""
        assert extract_length_cm("Роза 40см") == 40
        assert extract_length_cm("Роза 80см") == 80
        assert extract_length_cm("Роза 120см") == 120

    def test_extract_length_not_found(self):
        """Test when length is not in text."""
        assert extract_length_cm("Роза Explorer") is None
        assert extract_length_cm("Просто текст") is None


class TestOriginExtractor:
    """Tests for origin country extraction."""

    def test_extract_origin_in_parentheses_cyrillic(self):
        """Test extracting country in parentheses (cyrillic)."""
        assert extract_origin_country("Роза Explorer (Эквадор)") == "Ecuador"
        assert extract_origin_country("Роза (Голландия)") == "Netherlands"

    def test_extract_origin_in_parentheses_latin(self):
        """Test extracting country in parentheses (latin)."""
        assert extract_origin_country("Rose (Ecuador)") == "Ecuador"

    def test_extract_origin_without_parentheses(self):
        """Test extracting country from text."""
        assert extract_origin_country("Роза Эквадор") == "Ecuador"

    def test_extract_origin_multiple_countries(self):
        """Test when multiple countries mentioned - should get first."""
        text = "Роза (Эквадор) Голландия"
        # Should prioritize parentheses
        assert extract_origin_country(text) == "Ecuador"

    def test_extract_origin_not_found(self):
        """Test when country not in text."""
        assert extract_origin_country("Роза Explorer 60см") is None
        assert extract_origin_country("Просто текст") is None

    def test_extract_origin_case_insensitive(self):
        """Test case insensitivity."""
        assert extract_origin_country("Роза (ЭКВАДОР)") == "Ecuador"
        assert extract_origin_country("Роза эквАдор") == "Ecuador"
