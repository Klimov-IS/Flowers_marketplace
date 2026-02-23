"""AI-based price extraction from raw text.

When PDF table extraction fails (no tables found), this module extracts
raw text from PDF pages and sends it to DeepSeek to identify product
names and prices. Results are converted to the standard row format
compatible with the import pipeline.
"""
import logging
import os
from typing import Any, Dict, List

from packages.core.ai.client import DeepSeekClient, DeepSeekError
from packages.core.ai.prompts import (
    SYSTEM_PROMPT_TEXT_PRICE_EXTRACTION,
    build_text_price_extraction_prompt,
)

logger = logging.getLogger(__name__)


async def ai_extract_price_from_text(
    raw_text: str,
) -> List[Dict[str, Any]]:
    """Extract price data from raw text using AI.

    Sends raw document text to DeepSeek, which returns structured
    product-price pairs. Converts them to the standard row format
    used by the import pipeline.

    Args:
        raw_text: Raw text extracted from PDF pages

    Returns:
        List of row dicts compatible with _process_rows():
        [{"row_number": int, "cells": [name, unit, price], "headers": [...]}]
        Empty list if AI unavailable or extraction fails.
    """
    ai_enabled = os.getenv("AI_ENABLED", "false").lower() == "true"
    if not ai_enabled:
        logger.info("ai_text_extraction_skipped: AI_ENABLED is false")
        return []

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        logger.info("ai_text_extraction_skipped: DEEPSEEK_API_KEY not set")
        return []

    # Skip if text is too short to contain useful data
    stripped = raw_text.strip()
    if len(stripped) < 20:
        logger.info("ai_text_extraction_skipped: text too short (%d chars)", len(stripped))
        return []

    try:
        client = DeepSeekClient(timeout=60.0, max_retries=1)

        user_prompt = build_text_price_extraction_prompt(stripped)

        response_data, tokens_in, tokens_out = await client.extract_json(
            system_prompt=SYSTEM_PROMPT_TEXT_PRICE_EXTRACTION,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=4096,
        )

        logger.info(
            "ai_text_extraction_response: tokens_in=%d, tokens_out=%d, items=%d, type=%s",
            tokens_in,
            tokens_out,
            len(response_data.get("items", [])),
            response_data.get("document_type", "unknown"),
        )

        items = response_data.get("items", [])
        if not items:
            logger.info("ai_text_extraction_no_items")
            return []

        # Convert AI response to standard row format
        headers = ["Наименование", "Ед. отгрузки", "Цена"]
        rows = []

        for idx, item in enumerate(items):
            name = str(item.get("name", "")).strip()
            price = item.get("price")
            unit = str(item.get("unit", "шт.")).strip() if item.get("unit") else "шт."
            pack_qty = item.get("pack_qty")

            if not name or price is None:
                continue

            price_str = str(price)

            # If pack_qty is present, include it in unit info
            if pack_qty and pack_qty > 1:
                unit = f"{unit} ({pack_qty} шт)"

            rows.append({
                "row_number": idx + 1,
                "cells": [name, unit, price_str],
                "headers": headers,
            })

        logger.info(
            "ai_text_extraction_result: rows=%d, type=%s, notes=%s",
            len(rows),
            response_data.get("document_type", "unknown"),
            response_data.get("notes", ""),
        )

        return rows

    except DeepSeekError as e:
        logger.warning("ai_text_extraction_error: %s", e)
        return []
    except Exception as e:
        logger.warning("ai_text_extraction_unexpected_error: %s", e)
        return []
