"""Header normalization for CSV files."""
import re
from typing import Dict


# Header mapping (cyrillic variants -> normalized name)
HEADER_MAPPINGS = {
    "name": [
        "наименование",
        "название",
        "номенклатура",
        "товар",
        "product",
        "name",
        "item",
    ],
    "price": [
        "цена",
        "price",
        "стоимость",
        "cost",
        "оптовая",
    ],
    "pack_qty": [
        "кол-во",
        "количество",
        "qty",
        "quantity",
        "упаковка",
        "pack",
    ],
    "order": [
        "заказ",
        "order",
    ],
    "amount": [
        "сумма",
        "amount",
        "total",
    ],
}


def normalize_header(header: str) -> str:
    """
    Normalize a single header to standard name.

    Args:
        header: Raw header string

    Returns:
        Normalized header name or original if no mapping found
    """
    # Clean header
    cleaned = header.strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)  # normalize whitespace
    cleaned = re.sub(r"[^\w\s-]", "", cleaned)  # remove special chars except dash

    # Try to find mapping - check if any variant is contained in header
    for normalized_name, variants in HEADER_MAPPINGS.items():
        for variant in variants:
            if variant in cleaned or cleaned in variant:
                return normalized_name

    # Return original if no mapping
    return header


def normalize_headers(headers: list[str]) -> Dict[str, int]:
    """
    Normalize CSV headers and create column index mapping.

    Args:
        headers: List of raw header strings

    Returns:
        Dictionary mapping normalized header names to column indices
    """
    column_map = {}

    for idx, header in enumerate(headers):
        if not header or not header.strip():
            continue

        normalized = normalize_header(header)
        column_map[normalized] = idx

    return column_map
