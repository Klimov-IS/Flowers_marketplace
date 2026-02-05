"""Parsing package - pure functions for data extraction."""
from packages.core.parsing.attributes import extract_length_cm, extract_origin_country
from packages.core.parsing.csv_parser import (
    parse_csv_content,
    detect_matrix_format,
    extract_matrix_columns,
)
from packages.core.parsing.headers import normalize_headers
from packages.core.parsing.price import parse_price
from packages.core.parsing.name_normalizer import (
    normalize_name,
    normalize_name_async,
    normalize_names_batch,
    normalize_names_batch_async,
    generate_stable_key,
    NormalizedName,
    FlowerTypeLookup,
)

__all__ = [
    "parse_csv_content",
    "detect_matrix_format",
    "extract_matrix_columns",
    "normalize_headers",
    "parse_price",
    "extract_length_cm",
    "extract_origin_country",
    "normalize_name",
    "normalize_name_async",
    "normalize_names_batch",
    "normalize_names_batch_async",
    "generate_stable_key",
    "NormalizedName",
    "FlowerTypeLookup",
]
