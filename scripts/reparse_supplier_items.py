#!/usr/bin/env python3
"""
Re-parse all supplier_items with updated parser.

Usage:
    python scripts/reparse_supplier_items.py [--supplier-id UUID] [--dry-run]
"""
import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from apps.api.models import SupplierItem
from packages.core.parsing.name_normalizer import normalize_name


async def reparse_items(
    db: AsyncSession,
    supplier_id: UUID | None = None,
    dry_run: bool = False,
) -> dict:
    """Re-parse supplier items with updated parser."""

    # Build query
    stmt = select(SupplierItem).where(SupplierItem.status != "deleted")
    if supplier_id:
        stmt = stmt.where(SupplierItem.supplier_id == supplier_id)

    result = await db.execute(stmt)
    items = result.scalars().all()

    stats = {
        "total": len(items),
        "updated": 0,
        "unchanged": 0,
        "errors": 0,
        "changes": [],
    }

    for item in items:
        try:
            # Parse with new parser
            normalized = normalize_name(item.raw_name)

            # Build new attributes
            new_attrs = {
                "flower_type": normalized.flower_type,
                "subtype": normalized.flower_subtype,
                "variety": normalized.variety,
                "clean_name": normalized.clean_name,
                "farm": normalized.farm,
            }

            # Add bundle detection
            if normalized.is_bundle_list:
                new_attrs["is_bundle_list"] = True
                new_attrs["bundle_varieties"] = normalized.bundle_varieties
                new_attrs["needs_review"] = True
                new_attrs["review_reason"] = "bundle_list_detected"

            if normalized.warnings:
                new_attrs["warnings"] = normalized.warnings

            # Compare with existing
            existing = item.attributes or {}
            old_clean = existing.get("clean_name")
            new_clean = new_attrs.get("clean_name")

            # Check if anything changed
            changed = False
            for key in ["flower_type", "subtype", "variety", "clean_name"]:
                if existing.get(key) != new_attrs.get(key):
                    changed = True
                    break

            if changed:
                # Preserve existing fields that shouldn't be overwritten
                merged = dict(existing)

                # Preserve locked fields
                locked = merged.get("_locked", [])
                existing_sources = merged.get("_sources", {})

                # Update with new parser values (except locked)
                for key, value in new_attrs.items():
                    if key not in locked and value is not None:
                        merged[key] = value
                        if key not in ["_sources", "_confidences", "_locked"]:
                            existing_sources[key] = "parser"

                merged["_sources"] = existing_sources

                # Also preserve colors and origin_country from existing
                if "colors" not in new_attrs and "colors" in existing:
                    merged["colors"] = existing["colors"]
                if "origin_country" not in new_attrs and "origin_country" in existing:
                    merged["origin_country"] = existing["origin_country"]

                stats["changes"].append({
                    "id": str(item.id),
                    "raw_name": item.raw_name[:50],
                    "old_clean": old_clean,
                    "new_clean": new_clean,
                    "old_type": existing.get("flower_type"),
                    "new_type": new_attrs.get("flower_type"),
                })

                if not dry_run:
                    item.attributes = merged

                stats["updated"] += 1
            else:
                stats["unchanged"] += 1

        except Exception as e:
            stats["errors"] += 1
            print(f"Error parsing {item.id}: {e}")

    if not dry_run:
        await db.commit()

    return stats


async def main():
    import argparse
    import os
    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(description="Re-parse supplier items")
    parser.add_argument("--supplier-id", type=str, help="Specific supplier UUID")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes")
    args = parser.parse_args()

    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        db_url = "postgresql+asyncpg://flower_user:flower_password@localhost:5432/flower_market"

    # Make sure it's async
    if "postgresql://" in db_url and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    print(f"Connecting to database...")
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        supplier_id = UUID(args.supplier_id) if args.supplier_id else None

        print(f"Re-parsing items...")
        print(f"  Supplier: {supplier_id or 'ALL'}")
        print(f"  Dry run: {args.dry_run}")
        print()

        stats = await reparse_items(db, supplier_id, args.dry_run)

        print(f"Results:")
        print(f"  Total items: {stats['total']}")
        print(f"  Updated: {stats['updated']}")
        print(f"  Unchanged: {stats['unchanged']}")
        print(f"  Errors: {stats['errors']}")
        print()

        if stats["changes"]:
            print("Sample changes (first 20):")
            for change in stats["changes"][:20]:
                print(f"  {change['raw_name'][:40]}...")
                print(f"    Type: {change['old_type']} → {change['new_type']}")
                print(f"    Clean: {change['old_clean']} → {change['new_clean']}")
                print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
