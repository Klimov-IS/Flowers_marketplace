"""Product type and variety detection."""
import re
from typing import List, Optional, Tuple

from packages.core.normalization.tokens import extract_latin_tokens, normalize_tokens


def detect_product_type(
    text: str,
    product_type_dict: dict,
) -> Optional[str]:
    """
    Detect product type from text using dictionary.

    Args:
        text: Normalized text
        product_type_dict: Dict mapping {key: {value, synonyms}}

    Returns:
        Product type value or None
    """
    if not text:
        return None

    text_lower = text.lower()

    # Check each product type and its synonyms
    for key, entry in product_type_dict.items():
        value = entry.get("value", key)
        synonyms = entry.get("synonyms", [])

        # Check main value
        if value.lower() in text_lower:
            return value

        # Check synonyms
        for synonym in synonyms:
            if synonym.lower() in text_lower:
                return value

    return None


def detect_variety(
    raw_name: str,
    variety_alias_dict: Optional[dict] = None,
) -> Optional[str]:
    """
    Detect variety name from raw_name.

    Strategy:
    1. Extract Latin tokens (capitalized words)
    2. Apply variety_alias if present
    3. Return first match or first Latin token

    Args:
        raw_name: Raw item name
        variety_alias_dict: Optional dict mapping {key: {value, synonyms}}

    Returns:
        Variety name or None
    """
    if not raw_name:
        return None

    # Extract Latin tokens (potential variety names)
    latin_tokens = extract_latin_tokens(raw_name)

    if not latin_tokens:
        return None

    # Try variety_alias lookup if available
    if variety_alias_dict:
        for token in latin_tokens:
            token_lower = token.lower()

            for key, entry in variety_alias_dict.items():
                value = entry.get("value", key)
                synonyms = entry.get("synonyms", [])

                # Check if token matches key or synonym
                if token_lower == key.lower():
                    return value

                for synonym in synonyms:
                    if token_lower == synonym.lower():
                        return value

    # Return first Latin token as variety
    return latin_tokens[0] if latin_tokens else None


def detect_subtype(
    text: str,
    regex_rules: List[dict],
) -> Optional[str]:
    """
    Detect subtype (spray, bush, etc) using regex rules.

    Args:
        text: Normalized text
        regex_rules: List of regex rule dicts

    Returns:
        Subtype value or None
    """
    if not text:
        return None

    for rule in regex_rules:
        pattern = rule.get("pattern")
        result = rule.get("result")

        if not pattern or not result:
            continue

        flags = re.IGNORECASE if rule.get("flags") == "IGNORECASE" else 0
        if re.search(pattern, text, flags):
            return result

    return None
