"""Confidence scoring for SKU mappings."""
from decimal import Decimal
from typing import Optional


def calculate_confidence(
    product_type_match: bool = False,
    variety_match: Optional[str] = None,  # "exact" | "high" | "low" | None
    subtype_match: bool = False,
    country_match: bool = False,
    has_mix_keyword: bool = False,
    name_too_short: bool = False,
    conflicting_product_type: bool = False,
) -> Decimal:
    """
    Calculate confidence score for SKU mapping.

    Based on NORMALIZATION_RULES.md scoring system:
    - Base: 0.10
    - product_type match: +0.30
    - variety exact: +0.45
    - variety high similarity: +0.30
    - variety low similarity: +0.10
    - subtype match: +0.05
    - country match: +0.05
    - has "mix": -0.25
    - name too short: -0.10
    - conflicting product type: -0.20

    Args:
        product_type_match: Product type matched
        variety_match: Variety match type ("exact", "high", "low", None)
        subtype_match: Subtype matched
        country_match: Country matched
        has_mix_keyword: Text contains "mix/микс"
        name_too_short: Name has < 3 tokens
        conflicting_product_type: Contradicting product type signals

    Returns:
        Confidence score (0.0 - 1.0)
    """
    score = Decimal("0.10")  # Base score

    # Positive signals
    if product_type_match:
        score += Decimal("0.30")

    if variety_match == "exact":
        score += Decimal("0.45")
    elif variety_match == "high":
        score += Decimal("0.30")
    elif variety_match == "low":
        score += Decimal("0.10")

    if subtype_match:
        score += Decimal("0.05")

    if country_match:
        score += Decimal("0.05")

    # Negative signals
    if has_mix_keyword:
        score -= Decimal("0.25")

    if name_too_short:
        score -= Decimal("0.10")

    if conflicting_product_type:
        score -= Decimal("0.20")

    # Clamp to [0.0, 1.0]
    score = max(Decimal("0.000"), min(Decimal("1.000"), score))

    return score


def variety_similarity(variety1: str, variety2: str) -> str:
    """
    Calculate variety similarity category.

    Args:
        variety1: First variety name
        variety2: Second variety name

    Returns:
        "exact" | "high" | "low" | "none"
    """
    if not variety1 or not variety2:
        return "none"

    v1 = variety1.lower().strip()
    v2 = variety2.lower().strip()

    # Exact match
    if v1 == v2:
        return "exact"

    # High similarity: one contains the other
    if v1 in v2 or v2 in v1:
        return "high"

    # Calculate simple token overlap
    tokens1 = set(v1.split())
    tokens2 = set(v2.split())

    if not tokens1 or not tokens2:
        return "none"

    overlap = len(tokens1 & tokens2)
    total = len(tokens1 | tokens2)

    similarity = overlap / total if total > 0 else 0.0

    if similarity >= 0.7:
        return "high"
    elif similarity >= 0.4:
        return "low"
    else:
        return "none"
