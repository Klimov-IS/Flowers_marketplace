"""CLI script for importing CSV price lists."""
import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import settings
from apps.api.database import AsyncSessionLocal
from apps.api.logging_config import get_logger, setup_logging
from apps.api.models import Supplier
from apps.api.services.import_service import ImportService

setup_logging()
logger = get_logger(__name__)


async def import_csv_file(supplier_name: str, file_path: str) -> None:
    """
    Import CSV file for a supplier.

    Args:
        supplier_name: Supplier name (must exist in DB)
        file_path: Path to CSV file
    """
    # Check file exists
    csv_file = Path(file_path)
    if not csv_file.exists():
        logger.error("file_not_found", file_path=file_path)
        sys.exit(1)

    # Read file
    content = csv_file.read_bytes()
    logger.info("file_read", file_path=file_path, size=len(content))

    # Import via service
    async with AsyncSessionLocal() as db:
        try:
            # Find supplier
            result = await db.execute(
                select(Supplier).where(Supplier.name == supplier_name)
            )
            supplier = result.scalar_one_or_none()

            if not supplier:
                logger.error("supplier_not_found", name=supplier_name)
                print(f"Error: Supplier '{supplier_name}' not found in database")
                print("Please create supplier first via API or add to database")
                sys.exit(1)

            logger.info("supplier_found", supplier_id=str(supplier.id), name=supplier.name)

            # Import
            import_service = ImportService(db)
            import_batch = await import_service.import_csv(
                supplier_id=supplier.id,
                filename=csv_file.name,
                content=content,
            )

            # Get summary
            summary = await import_service.get_import_summary(import_batch.id)

            logger.info("import_success", batch_id=str(import_batch.id), summary=summary)

            print("\n✓ Import completed successfully!")
            print(f"  Batch ID: {import_batch.id}")
            print(f"  Status: {import_batch.status}")
            print(f"  Raw rows: {summary['raw_rows_count']}")
            print(f"  Supplier items: {summary['supplier_items_count']}")
            print(f"  Offer candidates: {summary['offer_candidates_count']}")
            print(f"  Parse events: {summary['parse_events_count']}")

        except Exception as e:
            logger.error("import_failed", error=str(e))
            print(f"\n✗ Import failed: {str(e)}")
            sys.exit(1)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Import CSV price list for a supplier"
    )
    parser.add_argument(
        "--supplier",
        required=True,
        help="Supplier name (must exist in database)",
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to CSV file",
    )

    args = parser.parse_args()

    # Run async import
    asyncio.run(import_csv_file(args.supplier, args.file))


if __name__ == "__main__":
    main()
