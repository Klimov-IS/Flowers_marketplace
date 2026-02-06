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
        assert extract_length_cm("Роза 160см") is None  # Too long (>150)
        assert extract_length_cm("Роза 20см") is None  # Too short

    def test_extract_length_valid_range(self):
        """Test lengths within valid range (30-150cm)."""
        assert extract_length_cm("Роза 40см") == 40
        assert extract_length_cm("Роза 80см") == 80
        assert extract_length_cm("Роза 120см") == 120
        assert extract_length_cm("Магнолия 150см") == 150  # Extended range for tall stems

    def test_extract_length_with_trailing_parenthesis(self):
        """Test extracting length when parenthesis follows (e.g., 120см(1))."""
        assert extract_length_cm("Магнолия 120см(1)") == 120
        assert extract_length_cm("Оксипеталум 60 см (10)") == 60

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


class TestNameNormalizer:
    """Tests for name normalizer (normalize_name function)."""

    def test_new_flower_types(self):
        """Test newly added flower types are recognized."""
        from packages.core.parsing.name_normalizer import normalize_name

        # Декоративная зелень
        result = normalize_name("Аспарагус Экстра")
        assert result.flower_type == "Аспарагус"

        result = normalize_name("Магнолия 120см(1)")
        assert result.flower_type == "Магнолия"

        result = normalize_name("Брассика Крэйн Куин")
        assert result.flower_type == "Брассика"

        # Цветы
        result = normalize_name("Амариллис Прополис")
        assert result.flower_type == "Амариллис"

        result = normalize_name("Матиола Ирон Дип Пинк")
        assert result.flower_type == "Матиола"

    def test_pack_qty_not_in_variety(self):
        """Test that pack_qty patterns are removed from variety."""
        from packages.core.parsing.name_normalizer import normalize_name

        # Pattern: (20) at end
        result = normalize_name("Гвоздика Алтаир (20)")
        assert result.variety == "Алтаир"
        assert "(20" not in (result.variety or "")

        # Pattern: х12 at end
        result = normalize_name("Амариллис лавли Нимф х12")
        assert result.variety is not None
        assert "х12" not in result.variety

        # Pattern: (1) at end
        result = normalize_name("Амариллис Прополис(1)")
        assert result.variety is not None
        assert "(1" not in result.variety

    def test_length_extraction_with_trailing_parenthesis(self):
        """Test length extraction when pack_qty follows."""
        from packages.core.parsing.name_normalizer import normalize_name

        result = normalize_name("Магнолия 120см(1)")
        assert result.length_cm == 120
        assert result.flower_type == "Магнолия"

        result = normalize_name("Оксипеталум 60 см (10)")
        assert result.length_cm == 60

    def test_bundle_list_detection(self):
        """Test detection of multiple varieties in one row (bundle list)."""
        from packages.core.parsing.name_normalizer import normalize_name

        # Clear bundle list: many varieties comma-separated
        result = normalize_name(
            "Роза Аннабель, Амор Амор, Баттеркап, Джумилия, Ивана"
        )
        assert result.is_bundle_list is True
        assert result.flower_type == "Роза"
        assert len(result.bundle_varieties) >= 4
        assert "Аннабель" in result.bundle_varieties
        assert result.variety is None  # Should not have a single variety

    def test_bundle_list_with_garbage_text(self):
        """Test detection of bundle list with garbage header text."""
        from packages.core.parsing.name_normalizer import normalize_name

        # This contains "Цена За Шт./ Руб" garbage from CSV header
        result = normalize_name(
            "Роза Аннабель, Амор Амор, Баттеркап Цена За Шт./ Руб"
        )
        assert result.is_bundle_list is True
        assert "garbage_text_detected" in result.warnings or len(result.warnings) > 0
        # Garbage should be cleaned
        assert "Руб" not in (result.clean_name or "")

    def test_non_bundle_list(self):
        """Test that normal names are not detected as bundles."""
        from packages.core.parsing.name_normalizer import normalize_name

        # Normal name with one variety
        result = normalize_name("Роза Фридом 60 см (Эквадор)")
        assert result.is_bundle_list is False
        assert result.flower_type == "Роза"
        assert result.variety == "Фридом"
        assert result.bundle_varieties == []
