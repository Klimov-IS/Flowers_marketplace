"""Publish service - convert offer_candidates to published offers."""
import structlog
from datetime import datetime
from typing import Dict
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models import (
    ImportBatch,
    Offer,
    OfferCandidate,
    SKUMapping,
    Supplier,
    SupplierItem,
)

logger = structlog.get_logger()


class PublishService:
    """Service for publishing offers from confirmed mappings."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def publish_supplier_offers(
        self,
        supplier_id: UUID,
    ) -> Dict[str, int | UUID]:
        """
        Publish offers for supplier from latest import.

        Algorithm:
        1. Validate supplier exists and is active
        2. Find latest successful import_batch
        3. Fetch offer_candidates from that batch
        4. Fetch confirmed mappings for those candidates
        5. Deactivate old offers (is_active = false)
        6. Create new offers for candidates with confirmed mappings
        7. Update import_batch status to 'published'
        8. Return summary

        Args:
            supplier_id: Supplier UUID

        Returns:
            Dict with:
                - import_batch_id: UUID of published batch
                - offers_deactivated: Count of old offers deactivated
                - offers_created: Count of new offers created
                - skipped_unmapped: Count of candidates without mapping

        Raises:
            ValueError: If supplier not found or not active
            ValueError: If no parsed imports found
        """
        log = logger.bind(supplier_id=str(supplier_id))
        log.info("publish.start")

        # Step 1: Validate supplier
        result = await self.db.execute(
            select(Supplier).where(Supplier.id == supplier_id)
        )
        supplier = result.scalar_one_or_none()

        if not supplier:
            log.warning("publish.supplier_not_found")
            raise ValueError(f"Supplier not found: {supplier_id}")

        if supplier.status != "active":
            log.warning("publish.supplier_not_active", status=supplier.status)
            raise ValueError(f"Supplier is not active: {supplier.status}")

        # Step 2: Find latest successful import_batch
        result = await self.db.execute(
            select(ImportBatch)
            .where(
                ImportBatch.supplier_id == supplier_id,
                ImportBatch.status == "parsed",
            )
            .order_by(ImportBatch.imported_at.desc())
            .limit(1)
        )
        import_batch = result.scalar_one_or_none()

        if not import_batch:
            log.warning("publish.no_parsed_imports")
            raise ValueError(f"No parsed imports found for supplier {supplier_id}")

        log = log.bind(import_batch_id=str(import_batch.id))
        log.info("publish.found_batch", imported_at=import_batch.imported_at)

        # Step 3: Fetch offer_candidates from this batch
        result = await self.db.execute(
            select(OfferCandidate)
            .where(
                OfferCandidate.import_batch_id == import_batch.id,
                OfferCandidate.validation.in_(["ok", "warn"]),
            )
        )
        candidates = result.scalars().all()
        log.debug("publish.candidates_fetched", count=len(candidates))

        if not candidates:
            log.warning("publish.no_valid_candidates")
            return {
                "import_batch_id": import_batch.id,
                "offers_deactivated": 0,
                "offers_created": 0,
                "skipped_unmapped": 0,
            }

        # Get supplier_item_ids for candidates
        candidate_item_ids = {c.supplier_item_id for c in candidates}

        # Step 4: Fetch confirmed mappings
        result = await self.db.execute(
            select(SKUMapping)
            .where(
                SKUMapping.supplier_item_id.in_(candidate_item_ids),
                SKUMapping.status == "confirmed",
            )
        )
        mappings = result.scalars().all()

        # Build mapping dict: {supplier_item_id → normalized_sku_id}
        mapping_dict = {m.supplier_item_id: m.normalized_sku_id for m in mappings}
        log.debug("publish.mappings_fetched", count=len(mapping_dict))

        # Load supplier items to get clean_name from attributes
        result = await self.db.execute(
            select(SupplierItem).where(SupplierItem.id.in_(candidate_item_ids))
        )
        supplier_items = result.scalars().all()
        item_dict = {item.id: item for item in supplier_items}

        # Step 5: Deactivate old offers (transaction)
        result = await self.db.execute(
            update(Offer)
            .where(
                Offer.supplier_id == supplier_id,
                Offer.is_active == True,
            )
            .values(is_active=False)
        )
        offers_deactivated = result.rowcount or 0
        log.info("publish.offers_deactivated", count=offers_deactivated)

        # Step 6: Create new offers
        offers_created = 0
        skipped_unmapped = 0

        for candidate in candidates:
            # Check if has confirmed mapping
            sku_id = mapping_dict.get(candidate.supplier_item_id)

            if not sku_id:
                # No confirmed mapping - skip
                skipped_unmapped += 1
                log.debug(
                    "publish.skip_unmapped",
                    candidate_id=str(candidate.id),
                    supplier_item_id=str(candidate.supplier_item_id),
                )
                continue

            # Get clean_name from supplier_item attributes
            supplier_item = item_dict.get(candidate.supplier_item_id)
            display_title = None
            if supplier_item and supplier_item.attributes:
                display_title = supplier_item.attributes.get("clean_name")
                # Fallback: build from attributes if clean_name not set
                # Format: Тип + Субтип + Сорт + Страна + Цвет + Длина
                if not display_title:
                    attrs = supplier_item.attributes
                    parts = []
                    # Тип цветка
                    if attrs.get("flower_type"):
                        parts.append(attrs["flower_type"])
                    # Субтип (кустовая, спрей)
                    if attrs.get("subtype"):
                        parts.append(attrs["subtype"].lower())
                    # Сорт
                    if attrs.get("variety"):
                        parts.append(attrs["variety"])
                    # Страна
                    if attrs.get("origin_country"):
                        parts.append(attrs["origin_country"])
                    # Только первый цвет
                    colors = attrs.get("colors", [])
                    if colors and len(colors) > 0:
                        parts.append(colors[0])
                    # Длина из candidate
                    if candidate.length_cm:
                        parts.append(f"{candidate.length_cm} см")
                    display_title = " ".join(parts) if parts else None

            # Create new offer
            offer = Offer(
                supplier_id=supplier_id,
                normalized_sku_id=sku_id,
                source_import_batch_id=import_batch.id,
                display_title=display_title,
                length_cm=candidate.length_cm,
                pack_type=candidate.pack_type,
                pack_qty=candidate.pack_qty,
                price_type=candidate.price_type,
                price_min=candidate.price_min,
                price_max=candidate.price_max,
                currency=candidate.currency,
                tier_min_qty=candidate.tier_min_qty,
                tier_max_qty=candidate.tier_max_qty,
                availability=candidate.availability,
                stock_qty=candidate.stock_qty,
                is_active=True,
                published_at=datetime.utcnow(),
            )
            self.db.add(offer)
            offers_created += 1

        log.info(
            "publish.offers_created",
            created=offers_created,
            skipped=skipped_unmapped,
        )

        # Step 7: Flush to ensure offers are created
        await self.db.flush()

        # Step 8: Update import_batch status to 'published'
        import_batch.status = "published"
        log.info("publish.batch_status_updated", status="published")

        # Return summary
        summary = {
            "import_batch_id": import_batch.id,
            "offers_deactivated": offers_deactivated,
            "offers_created": offers_created,
            "skipped_unmapped": skipped_unmapped,
        }

        log.info("publish.complete", summary=summary)
        return summary
