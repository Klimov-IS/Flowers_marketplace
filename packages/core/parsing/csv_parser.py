"""CSV parsing functions."""
import csv
import io
from typing import Any, Dict, List


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

        rows = []
        headers = None

        for row_idx, row in enumerate(reader):
            # Skip empty rows
            if not row or all(not cell.strip() for cell in row):
                continue

            # First non-empty row is headers
            if headers is None:
                headers = [cell.strip() for cell in row]
                continue

            # Build row dict
            row_dict = {
                "row_number": row_idx + 1,
                "cells": row,
                "headers": headers,
            }
            rows.append(row_dict)

        if not rows:
            raise ValueError("CSV file is empty or contains only headers")

        return rows

    except csv.Error as e:
        raise ValueError(f"CSV parsing error: {str(e)}")
