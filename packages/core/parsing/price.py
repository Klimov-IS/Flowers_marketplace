"""Price parsing functions."""
import re
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional


def parse_price(price_str: str) -> Dict[str, Optional[Decimal]]:
    """
    Parse price string into structured format.

    Supports:
    - Fixed price: "100", "100.50"
    - Range: "95-99", "95–99", "95 - 99"

    Args:
        price_str: Raw price string

    Returns:
        Dictionary with keys:
        - price_type: "fixed" or "range"
        - price_min: Decimal
        - price_max: Decimal | None
        - error: str | None (if parsing failed)
    """
    if not price_str or not str(price_str).strip():
        return {
            "price_type": "fixed",
            "price_min": None,
            "price_max": None,
            "error": "Empty price",
        }

    # Clean price string
    price_clean = str(price_str).strip()
    # Remove currency symbols
    price_clean = re.sub(r"[₽рубруб\.\s]", "", price_clean, flags=re.IGNORECASE)
    # Replace comma with dot for decimal
    price_clean = price_clean.replace(",", ".")

    # Try to detect range (with various dash types)
    range_pattern = r"^(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)$"
    range_match = re.match(range_pattern, price_clean)

    if range_match:
        try:
            price_min = Decimal(range_match.group(1))
            price_max = Decimal(range_match.group(2))

            if price_min > price_max:
                return {
                    "price_type": "range",
                    "price_min": price_min,
                    "price_max": price_max,
                    "error": "price_min > price_max",
                }

            return {
                "price_type": "range",
                "price_min": price_min,
                "price_max": price_max,
                "error": None,
            }
        except (InvalidOperation, ValueError) as e:
            return {
                "price_type": "fixed",
                "price_min": None,
                "price_max": None,
                "error": f"Invalid range format: {str(e)}",
            }

    # Try fixed price
    try:
        price = Decimal(price_clean)
        if price < 0:
            return {
                "price_type": "fixed",
                "price_min": price,
                "price_max": None,
                "error": "Negative price",
            }

        return {
            "price_type": "fixed",
            "price_min": price,
            "price_max": None,
            "error": None,
        }
    except (InvalidOperation, ValueError) as e:
        return {
            "price_type": "fixed",
            "price_min": None,
            "price_max": None,
            "error": f"Invalid price format: {str(e)}",
        }
