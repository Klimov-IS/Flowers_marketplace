"""Import service - orchestrates CSV import pipeline."""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.logging_config import get_logger
from apps.api.models import (
    ImportBatch,
    OfferCandidate,
    ParseEvent,
    ParseRun,
    RawRow,
    SupplierItem,
)
from packages.core.parsing import (
    extract_length_cm,
    extract_origin_country,
    parse_csv_content,
    parse_price,
)
from packages.core.parsing.attributes import extract_pack_qty
from packages.core.parsing.headers import normalize_headers
from packages.core.utils.stable_key import generate_stable_key, normalize_name

logger = get_logger(__name__)

PARSER_VERSION = "1.0.0-f1"  # Format F1: simple row table


class ImportService:
    """Service for importing CSV price lists."""

    def __init__(self, db: AsyncSession):
        """Initialize import service."""
        self.db = db

    async def import_csv(
        self,
        supplier_id: UUID,
        filename: str,
        content: bytes,
    ) -> ImportBatch:
        """
        Import CSV price list for supplier.

        Pipeline stages:
        1. Create import_batch (status=received)
        2. Parse CSV and store raw_rows
        3. Create parse_run
        4. Process rows: create/update supplier_items and offer_candidates
        5. Mark batch as parsed/failed

        Args:
            supplier_id: Supplier UUID
            filename: Original filename
            content: CSV file bytes

        Returns:
            Import batch

        Raises:
            ValueError: If import fails
        """
        logger.info("import_started", supplier_id=str(supplier_id), filename=filename)

        # Stage 1: Create import batch
        import_batch = ImportBatch(
            supplier_id=supplier_id,
            source_type="csv",
            source_filename=filename,
            status="received",
            meta={"file_size": len(content)},
        )
        self.db.add(import_batch)
        await self.db.flush()

        try:
            # Stage 2: Parse CSV
            rows = parse_csv_content(content)
            logger.info("csv_parsed", batch_id=str(import_batch.id), rows_count=len(rows))

            # Store raw rows
            raw_rows = []
            for row_data in rows:
                raw_row = RawRow(
                    import_batch_id=import_batch.id,
                    row_kind="data",
                    row_ref=f"row_{row_data['row_number']}",
                    raw_cells={"cells": row_data["cells"], "headers": row_data["headers"]},
                    raw_text=" | ".join(row_data["cells"]),
                )
                self.db.add(raw_row)
                raw_rows.append(raw_row)

            await self.db.flush()

            # Stage 3: Create parse run
            parse_run = ParseRun(
                import_batch_id=import_batch.id,
                parser_version=PARSER_VERSION,
            )
            self.db.add(parse_run)
            await self.db.flush()

            # Stage 4: Process rows
            summary = await self._process_rows(
                supplier_id=supplier_id,
                import_batch_id=import_batch.id,
                parse_run_id=parse_run.id,
                rows=rows,
                raw_rows=raw_rows,
            )

            # Stage 5: Finalize
            parse_run.finished_at = datetime.utcnow()
            parse_run.summary = summary
            import_batch.status = "parsed"

            await self.db.commit()

            logger.info(
                "import_completed",
                batch_id=str(import_batch.id),
                summary=summary,
            )

            return import_batch

        except Exception as e:
            import_batch.status = "failed"
            import_batch.meta["error"] = str(e)
            await self.db.commit()

            logger.error(
                "import_failed",
                batch_id=str(import_batch.id),
                error=str(e),
            )
            raise ValueError(f"Import failed: {str(e)}")

    async def _process_rows(
        self,
        supplier_id: UUID,
        import_batch_id: UUID,
        parse_run_id: UUID,
        rows: List[Dict],
        raw_rows: List[RawRow],
    ) -> Dict:
        """
        Process parsed rows: create supplier_items and offer_candidates.

        Args:
            supplier_id: Supplier UUID
            import_batch_id: Import batch UUID
            parse_run_id: Parse run UUID
            rows: Parsed CSV rows
            raw_rows: Corresponding RawRow models

        Returns:
            Summary dict with counts
        """
        summary = {
            "rows_total": len(rows),
            "supplier_items_created": 0,
            "supplier_items_updated": 0,
            "offer_candidates_created": 0,
            "parse_events_count": 0,
        }

        for row_data, raw_row in zip(rows, raw_rows):
            try:
                await self._process_single_row(
                    supplier_id=supplier_id,
                    import_batch_id=import_batch_id,
                    parse_run_id=parse_run_id,
                    row_data=row_data,
                    raw_row=raw_row,
                    summary=summary,
                )
            except Exception as e:
                # Log error but continue
                logger.warning(
                    "row_processing_failed",
                    raw_row_id=str(raw_row.id),
                    error=str(e),
                )
                await self._create_parse_event(
                    parse_run_id=parse_run_id,
                    raw_row_id=raw_row.id,
                    severity="error",
                    code="ROW_PROCESSING_FAILED",
                    message=f"Failed to process row: {str(e)}",
                )
                summary["parse_events_count"] += 1

        return summary

    async def _process_single_row(
        self,
        supplier_id: UUID,
        import_batch_id: UUID,
        parse_run_id: UUID,
        row_data: Dict,
        raw_row: RawRow,
        summary: Dict,
    ) -> None:
        """Process a single CSV row."""
        # Normalize headers
        headers = row_data["headers"]
        cells = row_data["cells"]
        header_map = normalize_headers(headers)

        # Extract required fields
        name_idx = header_map.get("name")
        price_idx = header_map.get("price")

        if name_idx is None or name_idx >= len(cells):
            await self._create_parse_event(
                parse_run_id=parse_run_id,
                raw_row_id=raw_row.id,
                severity="error",
                code="MISSING_NAME",
                message="Name column not found or empty",
            )
            summary["parse_events_count"] += 1
            return

        if price_idx is None or price_idx >= len(cells):
            await self._create_parse_event(
                parse_run_id=parse_run_id,
                raw_row_id=raw_row.id,
                severity="error",
                code="MISSING_PRICE",
                message="Price column not found or empty",
            )
            summary["parse_events_count"] += 1
            return

        raw_name = cells[name_idx].strip()
        raw_price = cells[price_idx].strip()

        if not raw_name:
            await self._create_parse_event(
                parse_run_id=parse_run_id,
                raw_row_id=raw_row.id,
                severity="error",
                code="EMPTY_NAME",
                message="Name is empty",
            )
            summary["parse_events_count"] += 1
            return

        # Parse price
        price_data = parse_price(raw_price)
        if price_data["error"] or price_data["price_min"] is None:
            await self._create_parse_event(
                parse_run_id=parse_run_id,
                raw_row_id=raw_row.id,
                severity="error",
                code="INVALID_PRICE",
                message=f"Invalid price: {price_data.get('error', 'unknown')}",
                payload={"raw_price": raw_price},
            )
            summary["parse_events_count"] += 1
            return

        # Extract pack_qty if column exists
        pack_qty = None
        pack_qty_idx = header_map.get("pack_qty")
        if pack_qty_idx is not None and pack_qty_idx < len(cells):
            pack_qty_str = cells[pack_qty_idx].strip()
            if pack_qty_str.isdigit():
                pack_qty = int(pack_qty_str)

        # Extract attributes from name
        length_cm = extract_length_cm(raw_name)
        origin_country = extract_origin_country(raw_name)
        if not pack_qty:
            pack_qty = extract_pack_qty(raw_name)

        # Generate stable key
        name_norm = normalize_name(raw_name)
        stable_key = generate_stable_key(
            supplier_id=supplier_id,
            raw_name=raw_name,
            raw_group=None,  # F1 format has no groups
        )

        # Create or update supplier_item
        result = await self.db.execute(
            select(SupplierItem).where(
                SupplierItem.supplier_id == supplier_id,
                SupplierItem.stable_key == stable_key,
            )
        )
        supplier_item = result.scalar_one_or_none()

        if supplier_item:
            # Update existing
            supplier_item.last_import_batch_id = import_batch_id
            supplier_item.raw_name = raw_name
            supplier_item.name_norm = name_norm
            supplier_item.attributes = {
                "origin_country": origin_country,
            }
            summary["supplier_items_updated"] += 1
        else:
            # Create new
            supplier_item = SupplierItem(
                supplier_id=supplier_id,
                stable_key=stable_key,
                last_import_batch_id=import_batch_id,
                raw_name=raw_name,
                raw_group=None,
                name_norm=name_norm,
                attributes={
                    "origin_country": origin_country,
                },
                status="active",
            )
            self.db.add(supplier_item)
            await self.db.flush()
            summary["supplier_items_created"] += 1

        # Create offer_candidate
        offer_candidate = OfferCandidate(
            supplier_item_id=supplier_item.id,
            import_batch_id=import_batch_id,
            raw_row_id=raw_row.id,
            length_cm=length_cm,
            pack_type=None,  # F1 format doesn't have pack_type in MVP
            pack_qty=pack_qty,
            price_type=price_data["price_type"],
            price_min=price_data["price_min"],
            price_max=price_data["price_max"],
            currency="RUB",
            tier_min_qty=None,
            tier_max_qty=None,
            availability="unknown",
            stock_qty=None,
            validation="ok",
            validation_notes=None,
        )
        self.db.add(offer_candidate)
        summary["offer_candidates_created"] += 1

    async def _create_parse_event(
        self,
        parse_run_id: UUID,
        raw_row_id: Optional[UUID],
        severity: str,
        code: str,
        message: str,
        payload: Optional[Dict] = None,
    ) -> None:
        """Create a parse event."""
        event = ParseEvent(
            parse_run_id=parse_run_id,
            raw_row_id=raw_row_id,
            severity=severity,
            code=code,
            message=message,
            payload=payload or {},
        )
        self.db.add(event)

    async def get_import_summary(self, import_batch_id: UUID) -> Optional[Dict]:
        """
        Get import summary with counts.

        Args:
            import_batch_id: Import batch UUID

        Returns:
            Summary dict or None if not found
        """
        # Get import batch
        result = await self.db.execute(
            select(ImportBatch).where(ImportBatch.id == import_batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            return None

        # Count raw rows
        raw_rows_count = await self.db.scalar(
            select(func.count(RawRow.id)).where(RawRow.import_batch_id == import_batch_id)
        )

        # Count supplier items
        supplier_items_count = await self.db.scalar(
            select(func.count(SupplierItem.id)).where(
                SupplierItem.last_import_batch_id == import_batch_id
            )
        )

        # Count offer candidates
        offer_candidates_count = await self.db.scalar(
            select(func.count(OfferCandidate.id)).where(
                OfferCandidate.import_batch_id == import_batch_id
            )
        )

        # Count parse events
        parse_events_count = await self.db.scalar(
            select(func.count(ParseEvent.id))
            .join(ParseRun)
            .where(ParseRun.import_batch_id == import_batch_id)
        )

        return {
            "batch_id": batch.id,
            "status": batch.status,
            "raw_rows_count": raw_rows_count or 0,
            "supplier_items_count": supplier_items_count or 0,
            "offer_candidates_count": offer_candidates_count or 0,
            "parse_events_count": parse_events_count or 0,
        }
