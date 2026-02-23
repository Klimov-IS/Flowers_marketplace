"""Tests for name sanitizer pipeline and clean_variety improvements."""
import pytest

from packages.core.parsing.name_normalizer import (
    _sanitize_text,
    _clean_variety,
    normalize_name,
)


class TestSanitizeText:
    """Tests for _sanitize_text() multi-stage pipeline."""

    # Stage 1: Unicode garbage removal
    def test_removes_registered_trademark(self):
        assert "Explorer" in _sanitize_text("Explorer®")
        assert "®" not in _sanitize_text("Explorer®")

    def test_removes_trademark_symbol(self):
        assert "™" not in _sanitize_text("Mondial™")

    def test_removes_smart_quotes(self):
        result = _sanitize_text("«Роза» Explorer")
        assert "«" not in result
        assert "»" not in result

    def test_removes_zero_width_chars(self):
        result = _sanitize_text("Explorer\u200b Freedom")
        assert "\u200b" not in result

    def test_removes_nbsp(self):
        result = _sanitize_text("Роза\u00a0Explorer")
        assert "\u00a0" not in result

    # Stage 2: Supplier markers
    def test_removes_leading_asterisk(self):
        assert _sanitize_text("*Explorer") == "Explorer"

    def test_removes_leading_hash(self):
        assert _sanitize_text("#Explorer") == "Explorer"

    def test_removes_new_marker(self):
        result = _sanitize_text("NEW! Роза Explorer")
        assert "NEW" not in result
        assert "Explorer" in result

    def test_removes_novinка_marker(self):
        result = _sanitize_text("НОВИНКА Роза Explorer")
        assert "НОВИНКА" not in result
        assert "Explorer" in result

    def test_removes_hit_marker(self):
        result = _sanitize_text("ХИТ Роза Explorer")
        assert "ХИТ" not in result

    def test_removes_sale_marker(self):
        result = _sanitize_text("SALE Роза Explorer")
        assert "SALE" not in result

    def test_removes_aktsiya_marker(self):
        result = _sanitize_text("АКЦИЯ Роза Explorer")
        assert "АКЦИЯ" not in result

    # Stage 3: Leading numbering
    def test_removes_dot_numbering(self):
        assert _sanitize_text("1. Explorer") == "Explorer"

    def test_removes_paren_numbering(self):
        assert _sanitize_text("1) Explorer") == "Explorer"

    def test_removes_colon_numbering(self):
        assert _sanitize_text("12: Explorer") == "Explorer"

    def test_removes_dash_numbering(self):
        assert _sanitize_text("3 - Explorer") == "Explorer"

    def test_preserves_numbers_in_variety(self):
        # "Miss Piggy 5+" should not lose content
        result = _sanitize_text("Miss Piggy")
        assert "Miss Piggy" == result

    # Stage 4: Parentheses with noise
    def test_removes_parens_with_price(self):
        result = _sanitize_text("Explorer (120руб)")
        assert "120" not in result
        assert "Explorer" in result

    def test_removes_parens_with_sht(self):
        result = _sanitize_text("Explorer (25 шт)")
        assert "25 шт" not in result

    def test_removes_parens_with_nalichie(self):
        result = _sanitize_text("Explorer (наличие)")
        assert "наличие" not in result

    def test_removes_parens_with_aktsiya(self):
        result = _sanitize_text("Explorer (акция)")
        assert "акция" not in result

    def test_removes_parens_with_new(self):
        result = _sanitize_text("Explorer (new)")
        assert "new" not in result.lower() or "Explorer" in result

    def test_preserves_parens_with_country(self):
        # Country in parens should NOT be removed by sanitizer
        result = _sanitize_text("Explorer (Эквадор)")
        assert "Эквадор" in result

    # Stage 5: Duplicate flower type
    def test_removes_duplicate_type(self):
        result = _sanitize_text("Роза Роза Explorer", flower_type="Роза")
        # Should keep only one "Роза"
        assert result.lower().count("роза") == 1
        assert "Explorer" in result

    # Stage 6: Excessive punctuation
    def test_removes_ellipsis(self):
        result = _sanitize_text("Explorer... test")
        assert "..." not in result

    def test_removes_multiple_exclamations(self):
        result = _sanitize_text("Explorer!!! test")
        assert "!!!" not in result

    def test_collapses_dashes(self):
        result = _sanitize_text("Explorer --- test")
        assert "---" not in result

    # Combined scenarios
    def test_combined_garbage(self):
        result = _sanitize_text("*NEW! 1. Explorer® (120руб)")
        assert "Explorer" in result
        assert "*" not in result
        assert "NEW" not in result
        assert "®" not in result
        assert "120" not in result


class TestCleanVariety:
    """Tests for _clean_variety() with flower_type dedup."""

    def test_removes_leading_digits(self):
        assert _clean_variety("1 Explorer") == "Explorer"

    def test_removes_leading_digits_before_cyrillic(self):
        assert _clean_variety("25 Бабалу") == "Бабалу"

    def test_removes_flower_type_from_variety(self):
        result = _clean_variety("Роза Explorer", flower_type="Роза")
        assert result == "Explorer"

    def test_removes_flower_type_case_insensitive(self):
        result = _clean_variety("роза Explorer", flower_type="Роза")
        assert result == "Explorer"

    def test_preserves_variety_without_type(self):
        result = _clean_variety("Explorer", flower_type="Роза")
        assert result == "Explorer"

    def test_handles_empty(self):
        assert _clean_variety("") == ""
        assert _clean_variety(None) == ""

    def test_removes_trailing_numbers(self):
        result = _clean_variety("Explorer 50")
        assert result == "Explorer"

    def test_removes_country_abbreviations(self):
        result = _clean_variety("Explorer Экв")
        assert result == "Explorer"

    def test_removes_unicode_garbage(self):
        result = _clean_variety("Explorer®")
        assert "®" not in result

    def test_capitalizes_properly(self):
        result = _clean_variety("pink floyd")
        assert result == "Pink Floyd"


class TestNormalizeNameSanitized:
    """Integration tests: normalize_name with sanitizer."""

    def test_dirty_name_with_markers(self):
        result = normalize_name("*NEW! Роза Explorer® 50 см (Эквадор)")
        assert result.flower_type == "Роза"
        assert result.variety == "Explorer"
        assert result.length_cm == 50
        assert result.origin_country == "Эквадор"

    def test_dirty_name_with_numbering(self):
        result = normalize_name("1. Роза Explorer 60 см")
        assert result.flower_type == "Роза"
        assert result.variety == "Explorer"

    def test_dirty_name_with_price_in_parens(self):
        result = normalize_name("Роза Explorer (150руб) 50 см")
        assert result.flower_type == "Роза"
        assert result.variety == "Explorer"

    def test_clean_name_no_garbage(self):
        result = normalize_name("Роза Explorer 50 см (Эквадор)")
        assert result.variety == "Explorer"
        assert result.clean_name == "Роза Explorer"

    def test_spray_rose_clean(self):
        result = normalize_name("Роза кустовая Lydia 40 см (Эквадор)")
        assert result.flower_type == "Роза"
        assert result.flower_subtype == "Кустовая"
        assert result.variety == "Lydia"

    def test_variety_does_not_repeat_type(self):
        result = normalize_name("Роза Роза Explorer 50 см")
        assert result.flower_type == "Роза"
        # variety should not start with "Роза"
        assert result.variety and not result.variety.lower().startswith("роза")
