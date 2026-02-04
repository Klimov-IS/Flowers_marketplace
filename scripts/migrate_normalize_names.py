"""
Data migration script: Re-normalize existing supplier_items with the new name parser.

This script updates all existing supplier_items with extracted attributes:
- colors
- flower_type
- variety
- farm
- clean_name

Run: python scripts/migrate_normalize_names.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from apps.api.models.items import SupplierItem
from packages.core.parsing.name_normalizer import normalize_name

# Database URL (same as in .env)
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/flower_market"


async def migrate_supplier_items():
    """Re-normalize all supplier items with the new parser."""
    print("Starting migration: Re-normalizing supplier item names...")

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get all supplier items
        result = await session.execute(select(SupplierItem))
        items = result.scalars().all()

        print(f"Found {len(items)} supplier items to process")

        updated = 0
        for item in items:
            # Normalize the raw name
            normalized = normalize_name(item.raw_name)

            # Get existing attributes or empty dict
            attributes = item.attributes or {}

            # Update with new normalized values
            # Only update if we extracted something meaningful
            if normalized.origin_country:
                attributes["origin_country"] = normalized.origin_country
            if normalized.colors:
                attributes["colors"] = normalized.colors
            if normalized.flower_type:
                attributes["flower_type"] = normalized.flower_type
            if normalized.variety:
                attributes["variety"] = normalized.variety
            if normalized.farm:
                attributes["farm"] = normalized.farm
            if normalized.clean_name:
                attributes["clean_name"] = normalized.clean_name

            # Update the item
            item.attributes = attributes
            updated += 1

            if updated % 50 == 0:
                print(f"  Processed {updated}/{len(items)} items...")

        # Commit all changes
        await session.commit()

        print(f"\nMigration complete! Updated {updated} items.")

        # Show some examples
        print("\nExample results:")
        for item in items[:5]:
            attrs = item.attributes or {}
            print(f"  '{item.raw_name[:50]}...' ->")
            print(f"    type: {attrs.get('flower_type', '-')}, variety: {attrs.get('variety', '-')}")
            print(f"    country: {attrs.get('origin_country', '-')}, colors: {attrs.get('colors', [])}")
            print()


async def show_preview():
    """Preview what the migration will do without making changes."""
    print("Preview mode: Showing what will be normalized...\n")

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(select(SupplierItem).limit(20))
        items = result.scalars().all()

        for item in items:
            normalized = normalize_name(item.raw_name)
            print(f"Original: {item.raw_name}")
            print(f"  -> Type: {normalized.flower_type}")
            print(f"  -> Variety: {normalized.variety}")
            print(f"  -> Country: {normalized.origin_country}")
            print(f"  -> Colors: {normalized.colors}")
            print(f"  -> Farm: {normalized.farm}")
            print(f"  -> Clean: {normalized.clean_name}")
            print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--preview":
        asyncio.run(show_preview())
    else:
        print("Run with --preview to see what will be changed first")
        print("Run without arguments to apply migration\n")

        confirm = input("Apply migration? (yes/no): ")
        if confirm.lower() == "yes":
            asyncio.run(migrate_supplier_items())
        else:
            print("Migration cancelled.")
