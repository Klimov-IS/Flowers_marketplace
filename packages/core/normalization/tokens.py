"""Token normalization functions."""
import re
from typing import List, Set


def normalize_tokens(text: str) -> str:
    """
    Normalize text to tokens for matching.

    Steps:
    - Lowercase
    - Trim
    - Remove special characters (keep letters, digits, spaces)
    - Normalize whitespace
    - Remove currency symbols

    Args:
        text: Raw text

    Returns:
        Normalized text
    """
    if not text:
        return ""

    # Lowercase
    normalized = text.lower().strip()

    # Remove currency symbols
    normalized = re.sub(r"[₽$€]", "", normalized)

    # Replace em/en dashes with hyphen
    normalized = normalized.replace("–", "-").replace("—", "-")

    # Remove special characters (keep: letters, digits, spaces, hyphens, parentheses)
    normalized = re.sub(r"[^\w\s\-()]", " ", normalized, flags=re.UNICODE)

    # Normalize whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def remove_stopwords(text: str, stopwords: Set[str]) -> str:
    """
    Remove stopwords from text.

    Args:
        text: Normalized text
        stopwords: Set of stopwords (already lowercase)

    Returns:
        Text with stopwords removed
    """
    if not text or not stopwords:
        return text

    words = text.split()
    filtered = [word for word in words if word.lower() not in stopwords]

    return " ".join(filtered)


def apply_synonyms(text: str, synonym_map: dict) -> str:
    """
    Apply synonym replacements to text.

    Args:
        text: Normalized text
        synonym_map: Dict mapping {synonym: canonical_value}

    Returns:
        Text with synonyms replaced
    """
    if not text or not synonym_map:
        return text

    result = text
    for synonym, canonical in synonym_map.items():
        # Use word boundary to avoid partial matches
        pattern = r"\b" + re.escape(synonym.lower()) + r"\b"
        result = re.sub(pattern, canonical.lower(), result, flags=re.IGNORECASE)

    return result


def extract_latin_tokens(text: str) -> List[str]:
    """
    Extract Latin tokens (potential variety names).

    Pattern: Capitalized Latin words, possibly multi-word.
    Examples: "Explorer", "Pink Floyd", "Bombastic"

    Args:
        text: Text to extract from

    Returns:
        List of Latin tokens
    """
    # Pattern: One or more capitalized Latin words
    pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
    matches = re.findall(pattern, text)

    return matches


def tokenize(text: str) -> List[str]:
    """
    Split text into tokens (words).

    Args:
        text: Normalized text

    Returns:
        List of tokens
    """
    if not text:
        return []

    return text.split()
