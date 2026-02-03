"""Normalization logic - token processing, product/variety detection, confidence scoring."""
from packages.core.normalization.confidence import calculate_confidence
from packages.core.normalization.detection import detect_product_type, detect_variety
from packages.core.normalization.tokens import normalize_tokens, remove_stopwords

__all__ = [
    "normalize_tokens",
    "remove_stopwords",
    "detect_product_type",
    "detect_variety",
    "calculate_confidence",
]
