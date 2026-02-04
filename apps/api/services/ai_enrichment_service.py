"""AI Enrichment Service for normalizing supplier items."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from apps.api.logging_config import get_logger
from apps.api.models.ai import AIRun, AISuggestion, AIRunStatus, AISuggestionStatus
from apps.api.models.items import SupplierItem
from packages.core.ai import AIService
from packages.core.ai.schemas import FieldExtraction

logger = get_logger(__name__)

# Confidence thresholds
CONFIDENCE_AUTO_APPLY = 0.90
CONFIDENCE_APPLY_WITH_MARK = 0.70


class AIEnrichmentService:
    """Service for AI-assisted enrichment of supplier items."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.ai_service = AIService()

    async def enrich_supplier_items(
        self,
        supplier_id: UUID,
        import_batch_id: UUID,
        items: list[SupplierItem],
    ) -> dict:
        """
        Enrich supplier items with AI-extracted attributes.

        Args:
            supplier_id: Supplier UUID
            import_batch_id: Import batch UUID
            items: List of SupplierItem objects to enrich

        Returns:
            Dict with enrichment statistics
        """
        # Check if AI is available
        if not self.ai_service.is_available():
            logger.info("ai_enrichment_skipped", reason="ai_not_available")
            return {"status": "skipped", "reason": "AI not available"}

        # Filter items that need enrichment (missing key attributes)
        items_needing_ai = self._filter_items_needing_enrichment(items)

        if not items_needing_ai:
            logger.info("ai_enrichment_skipped", reason="all_items_complete")
            return {"status": "skipped", "reason": "All items already complete"}

        # Check row limit
        if len(items_needing_ai) > self.ai_service.max_rows:
            logger.info(
                "ai_enrichment_skipped",
                reason="too_many_rows",
                count=len(items_needing_ai),
                limit=self.ai_service.max_rows,
            )
            return {
                "status": "skipped",
                "reason": f"Too many rows: {len(items_needing_ai)} > {self.ai_service.max_rows}",
            }

        # Create AI run record
        ai_run = AIRun(
            supplier_id=supplier_id,
            import_batch_id=import_batch_id,
            run_type="attribute_extraction",
            model_name=self.ai_service.client.model if self.ai_service.client else "unknown",
            status=AIRunStatus.RUNNING.value,
            row_count=len(items_needing_ai),
            input_hash=self._compute_input_hash(items_needing_ai),
            started_at=datetime.utcnow(),
        )
        self.db.add(ai_run)
        await self.db.flush()

        try:
            # Prepare rows for AI
            rows = [
                {
                    "row_index": i,
                    "raw_name": item.raw_name,
                    "supplier_item_id": str(item.id),
                }
                for i, item in enumerate(items_needing_ai)
            ]

            # Call AI service
            response = await self.ai_service.extract_attributes_batch(rows)

            # Update AI run with token usage
            ai_run.tokens_input = response.tokens_input
            ai_run.tokens_output = response.tokens_output
            ai_run.cost_usd = AIService.estimate_cost(
                response.tokens_input or 0,
                response.tokens_output or 0,
            )

            # Process suggestions and apply to items
            stats = await self._process_suggestions(
                ai_run=ai_run,
                items=items_needing_ai,
                suggestions=response.row_suggestions,
            )

            # Mark run as succeeded
            ai_run.status = AIRunStatus.SUCCEEDED.value
            ai_run.finished_at = datetime.utcnow()

            await self.db.commit()

            logger.info(
                "ai_enrichment_complete",
                ai_run_id=str(ai_run.id),
                items_processed=len(items_needing_ai),
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                cost_usd=str(ai_run.cost_usd),
                **stats,
            )

            return {
                "status": "succeeded",
                "ai_run_id": str(ai_run.id),
                **stats,
            }

        except Exception as e:
            # Mark run as failed
            ai_run.status = AIRunStatus.FAILED.value
            ai_run.error_message = str(e)
            ai_run.finished_at = datetime.utcnow()
            await self.db.commit()

            logger.error(
                "ai_enrichment_failed",
                ai_run_id=str(ai_run.id),
                error=str(e),
            )

            return {
                "status": "failed",
                "ai_run_id": str(ai_run.id),
                "error": str(e),
            }

    async def _process_suggestions(
        self,
        ai_run: AIRun,
        items: list[SupplierItem],
        suggestions: list,
    ) -> dict:
        """
        Process AI suggestions and apply to items.

        Returns statistics dict.
        """
        stats = {
            "auto_applied": 0,
            "applied_with_mark": 0,
            "needs_review": 0,
            "suggestions_created": 0,
        }

        for suggestion in suggestions:
            row_index = suggestion.row_index
            if row_index >= len(items):
                continue

            item = items[row_index]

            for field_name, extraction in suggestion.extracted.items():
                # Skip empty or zero-confidence extractions
                if extraction.confidence <= 0:
                    continue

                # Create suggestion record
                ai_suggestion = AISuggestion(
                    ai_run_id=ai_run.id,
                    suggestion_type="attribute",
                    target_entity="supplier_item",
                    target_id=item.id,
                    row_index=row_index,
                    field_name=field_name,
                    suggested_value={"value": extraction.value},
                    confidence=Decimal(str(extraction.confidence)),
                )

                # Determine status based on confidence
                if extraction.confidence >= CONFIDENCE_AUTO_APPLY:
                    ai_suggestion.applied_status = AISuggestionStatus.AUTO_APPLIED.value
                    ai_suggestion.applied_at = datetime.utcnow()
                    ai_suggestion.applied_by = "system"
                    stats["auto_applied"] += 1

                    # Apply to item
                    self._apply_suggestion_to_item(item, field_name, extraction)

                elif extraction.confidence >= CONFIDENCE_APPLY_WITH_MARK:
                    ai_suggestion.applied_status = AISuggestionStatus.AUTO_APPLIED.value
                    ai_suggestion.applied_at = datetime.utcnow()
                    ai_suggestion.applied_by = "system"
                    stats["applied_with_mark"] += 1

                    # Apply to item
                    self._apply_suggestion_to_item(item, field_name, extraction)

                else:
                    ai_suggestion.applied_status = AISuggestionStatus.NEEDS_REVIEW.value
                    stats["needs_review"] += 1

                self.db.add(ai_suggestion)
                stats["suggestions_created"] += 1

            # Mark item attributes as modified
            flag_modified(item, "attributes")

        return stats

    def _apply_suggestion_to_item(
        self,
        item: SupplierItem,
        field_name: str,
        extraction: FieldExtraction,
    ) -> None:
        """Apply a single AI suggestion to a supplier item."""
        attributes = item.attributes or {}
        sources = attributes.get("_sources", {})
        locked = attributes.get("_locked", [])
        confidences = attributes.get("_confidences", {})

        # Skip locked fields
        if field_name in locked:
            return

        # Skip manually edited fields
        if sources.get(field_name) == "manual":
            return

        # Apply the value
        attributes[field_name] = extraction.value
        sources[field_name] = "ai"
        confidences[field_name] = extraction.confidence

        # Update metadata
        attributes["_sources"] = sources
        attributes["_confidences"] = confidences

        item.attributes = attributes

    def _filter_items_needing_enrichment(
        self,
        items: list[SupplierItem],
    ) -> list[SupplierItem]:
        """Filter items that need AI enrichment."""
        needing_enrichment = []

        for item in items:
            attributes = item.attributes or {}

            # Check if key attributes are missing
            has_flower_type = bool(attributes.get("flower_type"))
            has_country = bool(attributes.get("origin_country"))
            has_variety = bool(attributes.get("variety"))

            # If any key attribute is missing, needs enrichment
            if not (has_flower_type and has_country and has_variety):
                needing_enrichment.append(item)

        return needing_enrichment

    def _compute_input_hash(self, items: list[SupplierItem]) -> str:
        """Compute hash of input for caching."""
        rows = [{"raw_name": item.raw_name} for item in items]
        return AIService.compute_input_hash(rows)


async def run_ai_enrichment_for_batch(
    db: AsyncSession,
    supplier_id: UUID,
    import_batch_id: UUID,
) -> dict:
    """
    Run AI enrichment for all items in an import batch.

    This is the main entry point for AI enrichment.
    """
    # Load supplier items for this batch
    result = await db.execute(
        select(SupplierItem).where(
            SupplierItem.supplier_id == supplier_id,
            SupplierItem.last_import_batch_id == import_batch_id,
        )
    )
    items = result.scalars().all()

    if not items:
        return {"status": "skipped", "reason": "No items found"}

    # Run enrichment
    service = AIEnrichmentService(db)
    return await service.enrich_supplier_items(
        supplier_id=supplier_id,
        import_batch_id=import_batch_id,
        items=list(items),
    )
