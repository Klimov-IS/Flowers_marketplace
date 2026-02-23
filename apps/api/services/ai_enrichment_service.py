"""AI Enrichment Service for normalizing supplier items."""
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from apps.api.logging_config import get_logger
from apps.api.models.ai import AIRun, AISuggestion, AIRunStatus, AISuggestionStatus
from apps.api.models.catalog import FlowerType, FlowerSubtype, FlowerVariety
from apps.api.models.items import SupplierItem
from packages.core.ai import AIService
from packages.core.ai.schemas import FieldExtraction

logger = get_logger(__name__)

# Confidence thresholds
CONFIDENCE_AUTO_APPLY = 0.90
CONFIDENCE_APPLY_WITH_MARK = 0.70

# Rate limiting (configurable via env vars)
RATE_LIMIT_PER_SUPPLIER_PER_DAY = int(os.getenv("AI_RATE_LIMIT_PER_SUPPLIER", "10"))
RATE_LIMIT_GLOBAL_PER_DAY = int(os.getenv("AI_RATE_LIMIT_GLOBAL", "100"))


class AIEnrichmentService:
    """Service for AI-assisted enrichment of supplier items."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.ai_service = AIService()

    async def _get_catalog_context(self) -> dict:
        """
        Load flower types and subtypes from database for AI prompt.

        Returns:
            Dict with:
            - flower_types: list of canonical type names
            - subtypes_by_type: dict mapping type name to list of subtype names
        """
        # Load active flower types
        types_result = await self.db.execute(
            select(FlowerType.canonical_name)
            .where(FlowerType.is_active == True)
            .order_by(FlowerType.canonical_name)
        )
        flower_types = [t for t in types_result.scalars()]

        # Load subtypes with their type names
        subtypes_result = await self.db.execute(
            select(FlowerSubtype.name, FlowerType.canonical_name)
            .join(FlowerType, FlowerSubtype.type_id == FlowerType.id)
            .where(FlowerSubtype.is_active == True)
            .where(FlowerType.is_active == True)
        )

        # Group subtypes by type
        subtypes_by_type: dict[str, list[str]] = {}
        for row in subtypes_result:
            subtype_name, type_name = row
            if type_name not in subtypes_by_type:
                subtypes_by_type[type_name] = []
            subtypes_by_type[type_name].append(subtype_name.lower())

        # Load known varieties grouped by type (for AI prompt)
        varieties_result = await self.db.execute(
            select(FlowerVariety.name, FlowerType.canonical_name)
            .join(FlowerType, FlowerVariety.type_id == FlowerType.id)
            .where(FlowerVariety.is_active == True)
            .where(FlowerType.is_active == True)
            .order_by(FlowerType.canonical_name, FlowerVariety.name)
        )

        known_varieties: dict[str, list[str]] = {}
        for row in varieties_result:
            variety_name, type_name = row
            if type_name not in known_varieties:
                known_varieties[type_name] = []
            known_varieties[type_name].append(variety_name)

        logger.debug(
            "catalog_context_loaded",
            flower_types_count=len(flower_types),
            subtypes_count=sum(len(v) for v in subtypes_by_type.values()),
            varieties_count=sum(len(v) for v in known_varieties.values()),
        )

        return {
            "flower_types": flower_types,
            "subtypes_by_type": subtypes_by_type,
            "known_varieties": known_varieties,
        }

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

        # Compute input hash for caching
        input_hash = self._compute_input_hash(items_needing_ai)

        # Check for cached AI run with same input
        cached_result = await self._check_cache(input_hash, items_needing_ai)
        if cached_result:
            logger.info(
                "ai_enrichment_cached",
                cached_ai_run_id=cached_result["cached_from_ai_run_id"],
                items_applied=cached_result["items_applied"],
            )
            return cached_result

        # Check rate limits
        rate_limit_result = await self._check_rate_limits(supplier_id)
        if rate_limit_result:
            logger.warning(
                "ai_enrichment_rate_limited",
                supplier_id=str(supplier_id),
                reason=rate_limit_result["reason"],
            )
            return rate_limit_result

        # Create AI run record
        ai_run = AIRun(
            supplier_id=supplier_id,
            import_batch_id=import_batch_id,
            run_type="attribute_extraction",
            model_name=self.ai_service.client.model if self.ai_service.client else "unknown",
            status=AIRunStatus.RUNNING.value,
            row_count=len(items_needing_ai),
            input_hash=input_hash,
            started_at=datetime.utcnow(),
        )
        self.db.add(ai_run)
        await self.db.flush()

        try:
            # Load catalog context from DB (flower types, subtypes)
            catalog_context = await self._get_catalog_context()

            # Prepare rows for AI
            rows = [
                {
                    "row_index": i,
                    "raw_name": item.raw_name,
                    "supplier_item_id": str(item.id),
                }
                for i, item in enumerate(items_needing_ai)
            ]

            # Call AI service with catalog context (including known varieties)
            response = await self.ai_service.extract_attributes_batch(
                rows,
                flower_types=catalog_context["flower_types"] or None,
                subtypes_by_type=catalog_context["subtypes_by_type"] or None,
                known_varieties=catalog_context.get("known_varieties") or None,
            )

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
        """Filter items that need AI enrichment.

        Sends ALL items that don't have a clean_name yet (i.e., all new items),
        plus any items missing key attributes. This ensures AI generates
        clean_name for every position in every price list.
        """
        needing_enrichment = []

        for item in items:
            attributes = item.attributes or {}

            # Always enrich if clean_name is missing (every new item)
            has_clean_name = bool(attributes.get("clean_name"))
            if not has_clean_name:
                needing_enrichment.append(item)
                continue

            # Also enrich if key attributes are missing
            has_flower_type = bool(attributes.get("flower_type"))
            has_country = bool(attributes.get("origin_country"))
            has_variety = bool(attributes.get("variety"))

            if not (has_flower_type and has_country and has_variety):
                needing_enrichment.append(item)

        return needing_enrichment

    def _compute_input_hash(self, items: list[SupplierItem]) -> str:
        """Compute hash of input for caching."""
        rows = [{"raw_name": item.raw_name} for item in items]
        return AIService.compute_input_hash(rows)

    async def _check_cache(
        self,
        input_hash: str,
        items: list[SupplierItem],
    ) -> Optional[dict]:
        """
        Check if there's a cached AI run with same input.

        If found, apply cached suggestions to current items.
        Returns result dict if cache hit, None otherwise.
        """
        # Look for succeeded AI run with same input hash
        result = await self.db.execute(
            select(AIRun).where(
                AIRun.input_hash == input_hash,
                AIRun.status == AIRunStatus.SUCCEEDED.value,
            ).order_by(AIRun.created_at.desc()).limit(1)
        )
        cached_run = result.scalar_one_or_none()

        if not cached_run:
            return None

        # Get suggestions from cached run
        suggestions_result = await self.db.execute(
            select(AISuggestion).where(
                AISuggestion.ai_run_id == cached_run.id,
            )
        )
        cached_suggestions = suggestions_result.scalars().all()

        if not cached_suggestions:
            return None

        # Build mapping from row_index to item
        # For cache reuse, we match by raw_name since items are new instances
        name_to_item = {item.raw_name: item for item in items}

        # Get original items' raw_names from cached suggestions
        # We need to reconstruct row_index -> raw_name mapping
        original_items_result = await self.db.execute(
            select(SupplierItem.id, SupplierItem.raw_name).where(
                SupplierItem.id.in_([s.target_id for s in cached_suggestions])
            )
        )
        original_items = {row.id: row.raw_name for row in original_items_result.fetchall()}

        # Apply cached suggestions to current items
        stats = {
            "auto_applied": 0,
            "applied_with_mark": 0,
            "needs_review": 0,
            "items_applied": 0,
        }
        applied_items = set()

        for suggestion in cached_suggestions:
            # Get original raw_name
            original_raw_name = original_items.get(suggestion.target_id)
            if not original_raw_name:
                continue

            # Find matching item in current batch
            item = name_to_item.get(original_raw_name)
            if not item:
                continue

            # Create FieldExtraction-like object for application
            extraction = FieldExtraction(
                value=suggestion.suggested_value.get("value"),
                confidence=float(suggestion.confidence),
            )

            # Apply based on confidence
            if suggestion.confidence >= Decimal(str(CONFIDENCE_AUTO_APPLY)):
                self._apply_suggestion_to_item(item, suggestion.field_name, extraction)
                stats["auto_applied"] += 1
                applied_items.add(item.id)
            elif suggestion.confidence >= Decimal(str(CONFIDENCE_APPLY_WITH_MARK)):
                self._apply_suggestion_to_item(item, suggestion.field_name, extraction)
                stats["applied_with_mark"] += 1
                applied_items.add(item.id)
            else:
                stats["needs_review"] += 1

        # Mark modified items
        for item in items:
            if item.id in applied_items:
                flag_modified(item, "attributes")

        stats["items_applied"] = len(applied_items)

        await self.db.commit()

        return {
            "status": "cached",
            "cached_from_ai_run_id": str(cached_run.id),
            **stats,
        }

    async def _check_rate_limits(self, supplier_id: UUID) -> Optional[dict]:
        """
        Check if rate limits are exceeded.

        Returns error dict if rate limited, None otherwise.
        """
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Check supplier-specific limit
        supplier_count_result = await self.db.execute(
            select(func.count(AIRun.id)).where(
                AIRun.supplier_id == supplier_id,
                AIRun.created_at >= today_start,
                AIRun.status != AIRunStatus.FAILED.value,  # Don't count failed runs
            )
        )
        supplier_count = supplier_count_result.scalar() or 0

        if supplier_count >= RATE_LIMIT_PER_SUPPLIER_PER_DAY:
            return {
                "status": "rate_limited",
                "reason": f"Supplier limit exceeded: {supplier_count}/{RATE_LIMIT_PER_SUPPLIER_PER_DAY} runs today",
                "retry_after": "tomorrow",
            }

        # Check global limit
        global_count_result = await self.db.execute(
            select(func.count(AIRun.id)).where(
                AIRun.created_at >= today_start,
                AIRun.status != AIRunStatus.FAILED.value,
            )
        )
        global_count = global_count_result.scalar() or 0

        if global_count >= RATE_LIMIT_GLOBAL_PER_DAY:
            return {
                "status": "rate_limited",
                "reason": f"Global limit exceeded: {global_count}/{RATE_LIMIT_GLOBAL_PER_DAY} runs today",
                "retry_after": "tomorrow",
            }

        return None


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
