"""PDF parsing functions.

Extracts tables from text-based PDFs using PyMuPDF's find_tables().
Returns data in the same row format as csv_parser.parse_csv_content().
"""
import re
from typing import Any, Dict, List

import fitz  # PyMuPDF


def parse_pdf_content(content: bytes) -> List[Dict[str, Any]]:
    """Parse PDF content into list of dictionaries.

    Uses PyMuPDF's find_tables() to extract structured tables from
    text-based PDFs.  Returns the same format as parse_csv_content().

    Args:
        content: Raw PDF bytes.

    Returns:
        List of row dicts:
        [{"row_number": int, "cells": List[str], "headers": List[str]}]

    Raises:
        ValueError: If PDF cannot be parsed or contains no tables.
    """
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Failed to open PDF: {e}")

    if doc.page_count == 0:
        raise ValueError("PDF file has no pages")

    all_rows: List[Dict[str, Any]] = []
    headers: List[str] = []
    global_row_number = 1

    for page_num in range(doc.page_count):
        page = doc[page_num]
        tables = page.find_tables()

        if not tables.tables:
            continue

        for table in tables.tables:
            extracted = table.extract()
            if not extracted:
                continue

            # First table with data — row 0 becomes header
            if not headers:
                headers = [_clean_cell(c) for c in extracted[0]]
                data_start = 1
            else:
                # Multi-page: check if first row repeats the header
                first_cleaned = [_clean_cell(c) for c in extracted[0]]
                if first_cleaned == headers:
                    data_start = 1
                else:
                    data_start = 0

            for row_idx in range(data_start, len(extracted)):
                cells = [_clean_cell(c) for c in extracted[row_idx]]

                # Skip empty rows
                if not any(c.strip() for c in cells):
                    continue

                # Skip metadata rows
                first = cells[0].strip().lower() if cells else ""
                if first.startswith("последн") or first.startswith("обновлен"):
                    continue

                all_rows.append({
                    "row_number": global_row_number,
                    "cells": cells,
                    "headers": headers,
                })
                global_row_number += 1

    doc.close()

    if len(all_rows) < 2:
        raise ValueError("PDF contains no extractable table data")

    return all_rows


def extract_pdf_text(content: bytes) -> str:
    """Extract raw text from all PDF pages.

    Used as fallback when find_tables() returns no tables.
    Concatenates text from all pages with page separators.

    Args:
        content: Raw PDF bytes.

    Returns:
        Extracted text string (may be empty for scanned/image PDFs).
    """
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception:
        return ""

    text_parts = []
    for page_num in range(doc.page_count):
        page = doc[page_num]
        page_text = page.get_text("text").strip()
        if page_text:
            text_parts.append(page_text)

    doc.close()
    return "\n\n".join(text_parts)


def _clean_cell(cell) -> str:
    """Clean a single cell value from PDF table extraction.

    Handles None values and normalises whitespace (PyMuPDF may return
    multi-line strings with newlines for cells that span lines).
    """
    if cell is None:
        return ""
    text = str(cell).replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text
