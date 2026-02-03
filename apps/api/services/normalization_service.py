"""Normalization service - propose SKU mappings for supplier items."""
from decimal import Decimal
from typing import Dict, List, Optional, Set
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.logging_config import get_logger
from apps.api.models import (
    DictionaryEntry,
    NormalizedSKU,
    NormalizationTask,
    OfferCandidate,
    SKUMapping,
    Supplier,
    SupplierItem,
)
from packages.core.normalization.confidence import calculate_confidence, variety_similarity
from packages.core.normalization.detection import detect_product_type, detect_subtype, detect_variety
from packages.core.normalization.tokens import normalize_tokens, remove_stopwords

logger = get_logger(__name__)


class NormalizationService:
    """Service for proposing SKU mappings."""

    def __init__(self, db: AsyncSession):
        """Initialize normalization service."""
        self.db = db

    async def propose(
        self,
        supplier_id: Optional[UUID] = None,
        import_batch_id: Optional[UUID] = None,
        limit: int = 1000,
    ) -> Dict[str, int]:
        """
        Propose SKU mappings for supplier_items.

        Args:
            supplier_id: Filter by supplier
            import_batch_id: Filter by import batch
            limit: Max items to process

        Returns:
            Summary dict with counts

        Raises:
            ValueError: If neither filter provided
        """
        if not supplier_id and not import_batch_id:
            raise ValueError("At least one of supplier_id or import_batch_id must be provided")

        logger.info(
            "normalization_propose_started",
            supplier_id=str(supplier_id) if supplier_id else None,
            import_batch_id=str(import_batch_id) if import_batch_id else None,
            limit=limit,
        )

        # Step 1: Load dictionaries
        dictionaries = await self._load_dictionaries()

        # Step 2: Get supplier_items to process
        query = select(SupplierItem).where(SupplierItem.status == "active")

        if supplier_id:
            query = query.where(SupplierItem.supplier_id == supplier_id)

        if import_batch_id:
            query = query.where(SupplierItem.last_import_batch_id == import_batch_id)

        query = query.limit(limit)

        result = await self.db.execute(query)
        supplier_items = result.scalars().all()

        logger.info("supplier_items_loaded", count=len(supplier_items))

        # Step 3: Process each supplier_item
        summary = {
            "processed_items": 0,
            "proposed_mappings": 0,
            "tasks_created": 0,
        }

        for supplier_item in supplier_items:
            try:
                item_summary = await self._process_supplier_item(supplier_item, dictionaries)
                summary["processed_items"] += 1
                summary["proposed_mappings"] += item_summary["mappings_created"]
                summary["tasks_created"] += item_summary["task_created"]
            except Exception as e:
                logger.error(
                    "supplier_item_processing_failed",
                    supplier_item_id=str(supplier_item.id),
                    error=str(e),
                )
                # Continue with next item

        await self.db.commit()

        logger.info("normalization_propose_completed", summary=summary)

        return summary

    async def _load_dictionaries(self) -> Dict:
        """Load all active dictionary entries grouped by type."""
        result = await self.db.execute(
            select(DictionaryEntry).where(DictionaryEntry.status == "active")
        )
        entries = result.scalars().all()

        # Group by dict_type
        dictionaries = {}
        for entry in entries:
            if entry.dict_type not in dictionaries:
                dictionaries[entry.dict_type] = {}

            dictionaries[entry.dict_type][entry.key] = {
                "value": entry.value,
                "synonyms": entry.synonyms or [],
                "rules": entry.rules or {},
            }

        logger.info(
            "dictionaries_loaded",
            types=list(dictionaries.keys()),
            total_entries=len(entries),
        )

        return dictionaries

    async def _process_supplier_item(
        self,
        supplier_item: SupplierItem,
        dictionaries: Dict,
    ) -> Dict:
        """
        Process single supplier_item.

        Returns:
            {
                "mappings_created": int,
                "task_created": int (0 or 1),
            }
        """
        summary = {"mappings_created": 0, "task_created": 0}

        # Step 2: Build normalized context
        raw_text = supplier_item.raw_name
        if supplier_item.raw_group:
            raw_text = f"{supplier_item.raw_group} {raw_text}"

        normalized_text = normalize_tokens(raw_text)

        # Build stopwords set
        stopwords = set()
        if "stopword" in dictionaries:
            for key, entry in dictionaries["stopword"].items():
                stopwords.add(entry["value"].lower())
                stopwords.update([s.lower() for s in entry["synonyms"]])

        # Remove stopwords
        cleaned_text = remove_stopwords(normalized_text, stopwords)

        # Step 3: Extract attributes
        product_type_dict = dictionaries.get("product_type", {})
        variety_alias_dict = dictionaries.get("variety_alias", {})
        regex_rules = []
        if "regex_rule" in dictionaries:
            for key, entry in dictionaries["regex_rule"].items():
                if "subtype" in key.lower() or "grade" in key.lower():
                    regex_rules.append(entry["rules"])

        product_type = detect_product_type(cleaned_text, product_type_dict)
        variety = detect_variety(supplier_item.raw_name, variety_alias_dict)
        subtype = detect_subtype(cleaned_text, regex_rules) if regex_rules else None

        # Extract country from attributes
        country = supplier_item.attributes.get("origin_country") if supplier_item.attributes else None

        logger.debug(
            "attributes_extracted",
            supplier_item_id=str(supplier_item.id),
            product_type=product_type,
            variety=variety,
            subtype=subtype,
            country=country,
        )

        # Step 4: Search candidate SKUs
        candidates = await self._search_candidate_skus(product_type, variety)

        if not candidates:
            # No candidates found
            priority = await self._calculate_priority(supplier_item)
            task_created = await self._create_task_if_needed(
                supplier_item_id=supplier_item.id,
                reason="No candidate SKUs found" if product_type else "Product type not detected",
                priority=priority,
            )
            summary["task_created"] = 1 if task_created else 0
            return summary

        # Step 5: Calculate confidence for each candidate
        # Check for negative signals
        has_mix = "mix" in cleaned_text.lower() or "микс" in cleaned_text.lower()
        name_too_short = len(cleaned_text.split()) < 3

        scored_candidates = []
        for candidate in candidates:
            # Determine variety match quality
            variety_match_quality = None
            if variety and candidate.variety:
                variety_match_quality = variety_similarity(variety, candidate.variety)

            # Country match
            country_match = False
            if country and candidate.meta:
                sku_country = candidate.meta.get("origin_default")
                country_match = sku_country == country if sku_country else False

            # Subtype match
            subtype_match = False
            if subtype and candidate.meta:
                sku_subtype = candidate.meta.get("subtype")
                subtype_match = sku_subtype == subtype if sku_subtype else False

            # Calculate confidence
            confidence = calculate_confidence(
                product_type_match=(product_type == candidate.product_type),
                variety_match=variety_match_quality,
                subtype_match=subtype_match,
                country_match=country_match,
                has_mix_keyword=has_mix,
                name_too_short=name_too_short,
                conflicting_product_type=False,  # TODO: implement detection
            )

            scored_candidates.append({
                "sku": candidate,
                "confidence": confidence,
            })

        # Sort by confidence desc
        scored_candidates.sort(key=lambda x: x["confidence"], reverse=True)

        # Keep top 5
        top_candidates = scored_candidates[:5]

        # Step 6: Create mappings
        for candidate_info in top_candidates:
            if candidate_info["confidence"] > Decimal("0.10"):
                created = await self._create_mapping_if_not_exists(
                    supplier_item_id=supplier_item.id,
                    normalized_sku_id=candidate_info["sku"].id,
                    confidence=candidate_info["confidence"],
                    method="rule",
                )
                if created:
                    summary["mappings_created"] += 1

        # Step 7: Create task if needed
        task_needed = False
        reason = ""

        if not top_candidates:
            task_needed = True
            reason = "No candidates with sufficient confidence"
        elif top_candidates[0]["confidence"] < Decimal("0.70"):
            task_needed = True
            reason = f"Low confidence: {top_candidates[0]['confidence']}"
        elif len(top_candidates) >= 2:
            diff = top_candidates[0]["confidence"] - top_candidates[1]["confidence"]
            if diff < Decimal("0.05"):
                task_needed = True
                reason = f"Ambiguous: top 2 candidates with similar scores ({diff})"

        if task_needed:
            priority = await self._calculate_priority(supplier_item)
            task_created = await self._create_task_if_needed(
                supplier_item_id=supplier_item.id,
                reason=reason,
                priority=priority,
            )
            summary["task_created"] = 1 if task_created else 0

        return summary

    async def _search_candidate_skus(
        self,
        product_type: Optional[str],
        variety: Optional[str],
    ) -> List[NormalizedSKU]:
        """Search for candidate SKUs."""
        if not product_type:
            return []

        # Strategy 1: Exact match (product_type + variety)
        if variety:
            result = await self.db.execute(
                select(NormalizedSKU).where(
                    NormalizedSKU.product_type == product_type,
                    NormalizedSKU.variety == variety,
                )
            )
            exact_match = result.scalar_one_or_none()
            if exact_match:
                return [exact_match]

        # Strategy 2: Product type only (variety IS NULL)
        result = await self.db.execute(
            select(NormalizedSKU).where(
                NormalizedSKU.product_type == product_type,
                NormalizedSKU.variety.is_(None),
            )
        )
        generic_match = result.scalar_one_or_none()
        if generic_match and not variety:
            return [generic_match]

        # Strategy 3: Similarity search (all with same product_type)
        result = await self.db.execute(
            select(NormalizedSKU)
            .where(NormalizedSKU.product_type == product_type)
            .limit(10)
        )
        candidates = result.scalars().all()

        # If we have generic match, include it
        if generic_match:
            candidates = [generic_match] + [c for c in candidates if c.id != generic_match.id]

        return list(candidates)

    async def _calculate_priority(
        self,
        supplier_item: SupplierItem,
    ) -> int:
        """Calculate task priority."""
        base_priority = 100

        # Count offer_candidates for this supplier_item
        result = await self.db.execute(
            select(func.count(OfferCandidate.id)).where(
                OfferCandidate.supplier_item_id == supplier_item.id
            )
        )
        offer_count = result.scalar() or 0
        base_priority += offer_count * 2

        # Check if supplier is "key" tier
        result = await self.db.execute(
            select(Supplier).where(Supplier.id == supplier_item.supplier_id)
        )
        supplier = result.scalar_one_or_none()
        if supplier and supplier.meta:
            if supplier.meta.get("tier") == "key":
                base_priority += 50

        return base_priority

    async def _create_mapping_if_not_exists(
        self,
        supplier_item_id: UUID,
        normalized_sku_id: UUID,
        confidence: Decimal,
        method: str = "rule",
    ) -> bool:
        """Create mapping if not exists. Returns True if created."""
        # Check if exists
        result = await self.db.execute(
            select(SKUMapping).where(
                SKUMapping.supplier_item_id == supplier_item_id,
                SKUMapping.normalized_sku_id == normalized_sku_id,
                SKUMapping.status == "proposed",
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return False

        # Create new
        mapping = SKUMapping(
            supplier_item_id=supplier_item_id,
            normalized_sku_id=normalized_sku_id,
            method=method,
            confidence=confidence,
            status="proposed",
        )
        self.db.add(mapping)

        logger.debug(
            "mapping_created",
            supplier_item_id=str(supplier_item_id),
            normalized_sku_id=str(normalized_sku_id),
            confidence=float(confidence),
        )

        return True

    async def _create_task_if_needed(
        self,
        supplier_item_id: UUID,
        reason: str,
        priority: int,
    ) -> bool:
        """Create task if not exists. Returns True if created."""
        # Check if open task already exists
        result = await self.db.execute(
            select(NormalizationTask).where(
                NormalizationTask.supplier_item_id == supplier_item_id,
                NormalizationTask.status == "open",
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return False

        # Create new task
        task = NormalizationTask(
            supplier_item_id=supplier_item_id,
            reason=reason,
            priority=priority,
            status="open",
        )
        self.db.add(task)

        logger.debug(
            "task_created",
            supplier_item_id=str(supplier_item_id),
            reason=reason,
            priority=priority,
        )

        return True
