"""Attribute extraction functions (length, country, etc)."""
import re
from typing import Optional


def extract_length_cm(text: str) -> Optional[int]:
    """
    Extract length in cm from text.

    Patterns supported:
    - "60см", "60 см", "60cm", "60 cm"

    Args:
        text: Text to extract from

    Returns:
        Length in cm or None if not found
    """
    if not text:
        return None

    # Pattern: digits followed by optional space and "см" or "cm"
    pattern = r"(?<!\d)(\d{2,3})\s*(?:см|cm)\b"
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        length = int(match.group(1))
        # Validate reasonable range (30-120 cm)
        if 30 <= length <= 120:
            return length

    return None


def extract_origin_country(text: str) -> Optional[str]:
    """
    Extract country of origin from text.

    Patterns supported:
    - "(Эквадор)", "(Ecuador)"
    - Text containing country name

    Args:
        text: Text to extract from

    Returns:
        Country name or None if not found
    """
    if not text:
        return None

    # Country dictionary (lowercase for matching)
    countries = {
        "эквадор": "Ecuador",
        "ecuador": "Ecuador",
        "колумбия": "Colombia",
        "colombia": "Colombia",
        "голландия": "Netherlands",
        "нидерланды": "Netherlands",
        "netherlands": "Netherlands",
        "кения": "Kenya",
        "kenya": "Kenya",
        "израиль": "Israel",
        "israel": "Israel",
    }

    text_lower = text.lower()

    # Try to find in parentheses first
    paren_pattern = r"\(([^)]+)\)"
    paren_matches = re.findall(paren_pattern, text)

    for match in paren_matches:
        match_lower = match.strip().lower()
        if match_lower in countries:
            return countries[match_lower]

    # Try to find anywhere in text
    for key, value in countries.items():
        if key in text_lower:
            return value

    return None


def extract_pack_qty(text: str) -> Optional[int]:
    """
    Extract pack quantity from text.

    Patterns supported:
    - "(10)", "(20 шт)"
    - "10 шт", "20шт"

    Args:
        text: Text to extract from

    Returns:
        Pack quantity or None if not found
    """
    if not text:
        return None

    # Pattern 1: (number) at end of string
    pattern1 = r"\((\d{1,3})\)\s*$"
    match1 = re.search(pattern1, text)
    if match1:
        qty = int(match1.group(1))
        # Reasonable pack qty range (5-50)
        if 5 <= qty <= 50:
            return qty

    # Pattern 2: (number шт)
    pattern2 = r"\((\d{1,3})\s*шт\)"
    match2 = re.search(pattern2, text, re.IGNORECASE)
    if match2:
        qty = int(match2.group(1))
        if 5 <= qty <= 50:
            return qty

    # Pattern 3: number шт (but be careful - might be tier qty)
    pattern3 = r"\b(\d{1,2})\s*шт\b"
    match3 = re.search(pattern3, text, re.IGNORECASE)
    if match3:
        qty = int(match3.group(1))
        if 5 <= qty <= 50:
            return qty

    return None
