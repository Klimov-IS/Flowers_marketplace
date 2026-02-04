"""CSV parsing functions."""
import csv
import io
from typing import Any, Dict, List


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
