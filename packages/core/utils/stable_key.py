"""Stable key generation for supplier items."""
import hashlib
import re
from typing import Optional
from uuid import UUID


def normalize_name(name: str) -> str:
    """
    Normalize item name for stable key generation.

    Args:
        name: Raw item name

    Returns:
        Normalized name (lowercase, trimmed, no extra spaces)
    """
    # Lowercase
    normalized = name.lower().strip()

    # Replace multiple spaces with single space
    normalized = re.sub(r"\s+", " ", normalized)

    # Remove some common noise (optional for MVP)
    # We keep it simple - just basic normalization

    return normalized


def generate_stable_key(
    supplier_id: UUID,
    raw_name: str,
    raw_group: Optional[str] = None,
) -> str:
    """
    Generate stable key for supplier item.

    The stable key is used to identify the same item across multiple imports.
    It's based on supplier_id + normalized_name + group context.

    Args:
        supplier_id: Supplier UUID
        raw_name: Raw item name
        raw_group: Optional group/category context

    Returns:
        16-character hex stable key
    """
    # Normalize name
    name_norm = normalize_name(raw_name)

    # Build key material
    group_part = normalize_name(raw_group) if raw_group else ""
    key_material = f"{supplier_id}:{group_part}:{name_norm}"

    # Hash and truncate to 16 chars
    hash_obj = hashlib.sha256(key_material.encode("utf-8"))
    return hash_obj.hexdigest()[:16]
