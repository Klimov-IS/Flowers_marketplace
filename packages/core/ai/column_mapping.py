"""AI-based column mapping detection for price list files.

When keyword-based header normalization fails to identify key columns
(e.g. price), this module uses DeepSeek to analyze headers + sample data
and determine the correct column mapping.
"""
import json
import logging
import os
from typing import Dict, List, Optional

from packages.core.ai.client import DeepSeekClient, DeepSeekError
from packages.core.ai.prompts import SYSTEM_PROMPT_COLUMN_MAPPING, build_column_mapping_prompt

logger = logging.getLogger(__name__)


async def ai_detect_column_mapping(
    headers: list[str],
    sample_rows: list[list[str]],
) -> Dict[str, int]:
    """Detect column mapping using AI when keyword matching fails.

    Sends headers and a few sample data rows to DeepSeek, which returns
    a structured JSON mapping of column indices to field names.

    Args:
        headers: List of raw header strings from the file
        sample_rows: First 3-5 data rows (list of cell values each)

    Returns:
        Dict mapping normalized field names to column indices,
        same format as normalize_headers(). Empty dict if AI unavailable
        or detection fails.
    """
    # Check if AI is enabled
    ai_enabled = os.getenv("AI_ENABLED", "false").lower() == "true"
    if not ai_enabled:
        logger.info("ai_column_mapping_skipped: AI_ENABLED is false")
        return {}

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        logger.info("ai_column_mapping_skipped: DEEPSEEK_API_KEY not set")
        return {}

    try:
        client = DeepSeekClient(timeout=30.0, max_retries=1)

        user_prompt = build_column_mapping_prompt(headers, sample_rows)

        response_data, tokens_in, tokens_out = await client.extract_json(
            system_prompt=SYSTEM_PROMPT_COLUMN_MAPPING,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=1024,
        )

        logger.info(
            "ai_column_mapping_response: tokens_in=%d, tokens_out=%d, response=%s",
            tokens_in, tokens_out, response_data,
        )

        # Parse response: {"column_mapping": [{"source_index": 0, "target_field": "raw_name", ...}]}
        column_mapping = response_data.get("column_mapping", [])
        result: Dict[str, int] = {}

        for entry in column_mapping:
            source_index = entry.get("source_index")
            target_field = entry.get("target_field")
            confidence = entry.get("confidence", 0)

            if source_index is None or not target_field:
                continue

            # Only accept mappings with reasonable confidence
            if confidence < 0.60:
                logger.info(
                    "ai_column_mapping_low_confidence: field=%s, index=%d, confidence=%.2f",
                    target_field, source_index, confidence,
                )
                continue

            # Validate index is within bounds
            if source_index < 0 or source_index >= len(headers):
                continue

            # Map raw_name -> name for compatibility with normalize_headers()
            field_name = target_field
            if field_name == "raw_name":
                field_name = "name"

            result[field_name] = source_index

        logger.info(
            "ai_column_mapping_result: mapping=%s, headers=%s",
            result, headers,
        )

        return result

    except DeepSeekError as e:
        logger.warning("ai_column_mapping_error: %s", e)
        return {}
    except Exception as e:
        logger.warning("ai_column_mapping_unexpected_error: %s", e)
        return {}
