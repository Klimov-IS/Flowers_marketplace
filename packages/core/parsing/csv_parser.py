"""CSV parsing functions."""
import csv
import io
import re
from typing import Any, Dict, List, Tuple


# Known header keywords for detection
KNOWN_HEADERS = [
    "наименование",
    "название",
    "номенклатура",
    "товар",
    "продукт",
    "сорт",
    "цена",
    "price",
    "стоимость",
    "кол-во",
    "количество",
    "высота",
    "см",  # Common in flower prices (40 см, 50 см)
]


def detect_header_row(all_rows: List[List[str]], max_rows: int = 20) -> int:
    """
    Find the row index that most likely contains headers.

    Scans up to max_rows rows looking for rows containing known header keywords.

    Args:
        all_rows: List of all CSV rows (as lists of strings)
        max_rows: Maximum number of rows to scan

    Returns:
        Index of the header row (0-based), or 0 if no headers detected
    """
    best_idx = 0
    best_score = 0

    for idx, row in enumerate(all_rows[:max_rows]):
        if not row:
            continue

        # Convert row cells to lowercase for matching
        row_text = " ".join(cell.lower().strip() for cell in row if cell)

        # Count how many known headers appear in this row
        score = sum(1 for kw in KNOWN_HEADERS if kw in row_text)

        # Require at least 1 known header to be confident
        if score >= 1 and score > best_score:
            best_score = score
            best_idx = idx

    return best_idx


def parse_csv_content(content: bytes, encoding: str = "utf-8") -> List[Dict[str, Any]]:
    """
    Parse CSV content into list of dictionaries.

    Args:
        content: Raw CSV bytes
        encoding: Text encoding (default: utf-8, fallback: cp1251 for Cyrillic)

    Returns:
        List of row dictionaries with raw cell values

    Raises:
        ValueError: If CSV cannot be parsed
    """
    # Try to decode with specified encoding
    try:
        text = content.decode(encoding)
    except UnicodeDecodeError:
        # Fallback to cp1251 (common for Russian Excel exports)
        try:
            text = content.decode("cp1251")
        except UnicodeDecodeError:
            # Last resort: latin-1 (never fails but might be wrong)
            text = content.decode("latin-1")

    # Parse CSV
    try:
        # Use StringIO to treat string as file
        csv_file = io.StringIO(text)

        # Detect delimiter (comma or semicolon)
        sample = text[:1024]
        if sample.count(";") > sample.count(","):
            delimiter = ";"
        else:
            delimiter = ","

        reader = csv.reader(csv_file, delimiter=delimiter)

        # Read all rows first
        all_rows = list(reader)

        if not all_rows:
            raise ValueError("CSV file is empty")

        # Smart header detection - find row with known headers
        header_idx = detect_header_row(all_rows)

        # Extract headers from detected row
        headers = [cell.strip() for cell in all_rows[header_idx]]

        # Process data rows (everything after header row)
        rows = []
        for row_idx, row in enumerate(all_rows[header_idx + 1 :], start=header_idx + 2):
            # Skip empty rows
            if not row or all(not cell.strip() for cell in row):
                continue

            # Build row dict
            row_dict = {
                "row_number": row_idx,
                "cells": row,
                "headers": headers,
            }
            rows.append(row_dict)

        if not rows:
            raise ValueError("CSV file is empty or contains only headers")

        return rows

    except csv.Error as e:
        raise ValueError(f"CSV parsing error: {str(e)}")


# Pattern for matrix column headers like "40 см Бак", "50 cm упак"
MATRIX_COLUMN_PATTERN = re.compile(
    r"(\d{2,3})\s*(см|cm)\.?\s*(бак|упак|pack|bucket)?",
    re.IGNORECASE
)


def detect_matrix_format(headers: List[str]) -> bool:
    """
    Determine if CSV is in matrix format (multiple dimension columns).

    Matrix format example:
        Наименование | 40 см Бак | 40 см Упак | 50 см Бак
        Роза         | 60        | 65         | 70

    Args:
        headers: List of header strings

    Returns:
        True if matrix format detected (2+ dimension columns)
    """
    if not headers:
        return False

    dimension_count = 0
    # Skip first column (usually product name)
    for header in headers[1:]:
        if header and MATRIX_COLUMN_PATTERN.search(header.lower()):
            dimension_count += 1

    return dimension_count >= 2


def extract_matrix_columns(headers: List[str]) -> List[Tuple[int, int, str | None]]:
    """
    Extract matrix column information from headers.

    Args:
        headers: List of header strings

    Returns:
        List of tuples: (column_index, length_cm, pack_type)
        Example: [(1, 40, "bak"), (2, 40, "pack"), (3, 50, "bak")]
    """
    columns = []
    for idx, header in enumerate(headers):
        if not header:
            continue

        match = MATRIX_COLUMN_PATTERN.search(header.lower())
        if match:
            length_cm = int(match.group(1))
            raw_pack_type = match.group(3)

            # Normalize pack_type
            pack_type = None
            if raw_pack_type:
                if raw_pack_type in ("бак", "bucket"):
                    pack_type = "bak"
                elif raw_pack_type in ("упак", "pack"):
                    pack_type = "pack"

            columns.append((idx, length_cm, pack_type))

    return columns
