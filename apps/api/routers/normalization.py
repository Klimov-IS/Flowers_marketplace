"""Normalization endpoints (propose, tasks, confirm)."""
import structlog
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.database import get_db
from apps.api.models import (
    ImportBatch,
    NormalizationTask,
    NormalizedSKU,
    OfferCandidate,
    RawRow,
    SKUMapping,
    Supplier,
    SupplierItem,
)
from apps.api.services.normalization_service import NormalizationService

logger = structlog.get_logger()
router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================


class ProposeRequest(BaseModel):
    """Request to propose mappings."""

    supplier_id: UUID | None = None
    import_batch_id: UUID | None = None
    limit: int = Field(default=1000, ge=1, le=10000)


class ProposeResponse(BaseModel):
    """Response from propose endpoint."""

    processed_items: int
    proposed_mappings: int
    tasks_created: int


class SupplierItemDetail(BaseModel):
    """Supplier item details for task response."""

    id: UUID
    raw_name: str
    raw_group: str | None
    name_norm: str
    attributes: dict[str, Any]

    class Config:
        from_attributes = True


class ProposedMappingDetail(BaseModel):
    """Proposed mapping details for task response."""

    id: UUID
    normalized_sku_id: UUID
    confidence: Decimal
    sku_title: str
    sku_variety: str | None

    class Config:
        from_attributes = True


class SampleRawRow(BaseModel):
    """Sample raw row for context."""

    raw_text: str


class TaskDetail(BaseModel):
    """Enriched normalization task."""

    id: UUID
    supplier_item_id: UUID
    reason: str
    priority: int
    status: str
    assigned_to: str | None
    created_at: datetime
    supplier_item: SupplierItemDetail
    proposed_mappings: list[ProposedMappingDetail]
    sample_raw_rows: list[SampleRawRow]

    class Config:
        from_attributes = True


class TasksListResponse(BaseModel):
    """Response from list tasks endpoint."""

    tasks: list[TaskDetail]
    total: int
    limit: int
    offset: int


class ConfirmRequest(BaseModel):
    """Request to confirm a mapping."""

    supplier_item_id: UUID
    normalized_sku_id: UUID
    notes: str | None = None


class MappingDetail(BaseModel):
    """Confirmed mapping details."""

    id: UUID
    supplier_item_id: UUID
    normalized_sku_id: UUID
    status: str
    confidence: Decimal
    method: str
    decided_at: datetime | None
    notes: str | None

    class Config:
        from_attributes = True


class ConfirmResponse(BaseModel):
    """Response from confirm endpoint."""

    mapping: MappingDetail


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/propose", response_model=ProposeResponse)
async def propose_mappings(
    request: ProposeRequest,
    db: AsyncSession = Depends(get_db),
) -> ProposeResponse:
    """
    Trigger normalization proposal for supplier items.

    At least one of supplier_id or import_batch_id must be provided.
    Calls NormalizationService.propose() to create proposed mappings
    and manual review tasks.
    """
    log = logger.bind(
        supplier_id=str(request.supplier_id) if request.supplier_id else None,
        import_batch_id=str(request.import_batch_id) if request.import_batch_id else None,
    )
    log.info("normalization.propose.start")

    # Validate: at least one filter required
    if not request.supplier_id and not request.import_batch_id:
        log.warning("normalization.propose.no_filters")
        raise HTTPException(
            status_code=400,
            detail="At least one of supplier_id or import_batch_id must be provided",
        )

    # Verify supplier exists if provided
    if request.supplier_id:
        result = await db.execute(
            select(Supplier).where(Supplier.id == request.supplier_id)
        )
        supplier = result.scalar_one_or_none()
        if not supplier:
            log.warning("normalization.propose.supplier_not_found")
            raise HTTPException(status_code=404, detail="Supplier not found")

    # Verify import_batch exists if provided
    if request.import_batch_id:
        result = await db.execute(
            select(ImportBatch).where(ImportBatch.id == request.import_batch_id)
        )
        batch = result.scalar_one_or_none()
        if not batch:
            log.warning("normalization.propose.batch_not_found")
            raise HTTPException(status_code=404, detail="Import batch not found")

    # Call normalization service
    try:
        normalization_service = NormalizationService(db)
        summary = await normalization_service.propose(
            supplier_id=request.supplier_id,
            import_batch_id=request.import_batch_id,
            limit=request.limit,
        )
        await db.commit()

        log.info("normalization.propose.success", summary=summary)
        return ProposeResponse(**summary)

    except Exception as e:
        await db.rollback()
        log.error("normalization.propose.error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Propose failed: {str(e)}")


@router.get("/tasks", response_model=TasksListResponse)
async def list_tasks(
    status: str | None = Query(None, description="Filter by task status"),
    supplier_id: UUID | None = Query(None, description="Filter by supplier"),
    limit: int = Query(50, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
) -> TasksListResponse:
    """
    List normalization tasks with enriched context.

    Returns tasks with:
    - Supplier item details
    - Proposed mappings (top proposals)
    - Sample raw rows for context

    Ordered by priority DESC, created_at ASC.
    """
    log = logger.bind(status=status, supplier_id=str(supplier_id) if supplier_id else None)
    log.info("normalization.tasks.list.start")

    # Build base query
    query = select(NormalizationTask).options(
        selectinload(NormalizationTask.supplier_item)
    )

    # Apply filters
    if status:
        query = query.where(NormalizationTask.status == status)

    if supplier_id:
        # Join with supplier_items to filter by supplier
        query = query.join(
            SupplierItem,
            SupplierItem.id == NormalizationTask.supplier_item_id,
        ).where(SupplierItem.supplier_id == supplier_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Order and paginate
    query = query.order_by(
        NormalizationTask.priority.desc(),
        NormalizationTask.created_at.asc(),
    )
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await db.execute(query)
    tasks = result.scalars().all()

    # Enrich tasks with mappings and samples
    enriched_tasks = []
    for task in tasks:
        # Get proposed mappings for this item
        mappings_query = (
            select(SKUMapping)
            .options(selectinload(SKUMapping.normalized_sku))
            .where(
                SKUMapping.supplier_item_id == task.supplier_item_id,
                SKUMapping.status == "proposed",
            )
            .order_by(SKUMapping.confidence.desc())
            .limit(5)
        )
        mappings_result = await db.execute(mappings_query)
        mappings = mappings_result.scalars().all()

        # Get sample raw rows (via offer_candidates)
        samples_query = (
            select(RawRow.raw_text)
            .join(
                OfferCandidate,
                OfferCandidate.raw_row_id == RawRow.id,
            )
            .where(OfferCandidate.supplier_item_id == task.supplier_item_id)
            .limit(3)
        )
        samples_result = await db.execute(samples_query)
        sample_texts = samples_result.scalars().all()

        # Build enriched task
        enriched_tasks.append(
            TaskDetail(
                id=task.id,
                supplier_item_id=task.supplier_item_id,
                reason=task.reason,
                priority=task.priority,
                status=task.status,
                assigned_to=task.assigned_to,
                created_at=task.created_at,
                supplier_item=SupplierItemDetail(
                    id=task.supplier_item.id,
                    raw_name=task.supplier_item.raw_name,
                    raw_group=task.supplier_item.raw_group,
                    name_norm=task.supplier_item.name_norm,
                    attributes=task.supplier_item.attributes or {},
                ),
                proposed_mappings=[
                    ProposedMappingDetail(
                        id=m.id,
                        normalized_sku_id=m.normalized_sku_id,
                        confidence=m.confidence,
                        sku_title=m.normalized_sku.title,
                        sku_variety=m.normalized_sku.variety,
                    )
                    for m in mappings
                ],
                sample_raw_rows=[
                    SampleRawRow(raw_text=text) for text in sample_texts
                ],
            )
        )

    log.info("normalization.tasks.list.success", total=total, returned=len(enriched_tasks))
    return TasksListResponse(
        tasks=enriched_tasks,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/confirm", response_model=ConfirmResponse)
async def confirm_mapping(
    request: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
) -> ConfirmResponse:
    """
    Confirm a mapping (manual decision).

    TRANSACTIONAL:
    1. Reject all existing mappings for this supplier_item
    2. Update/Create confirmed mapping
    3. Mark related task as done

    Only ONE confirmed mapping per supplier_item (DB constraint enforced).
    """
    log = logger.bind(
        supplier_item_id=str(request.supplier_item_id),
        normalized_sku_id=str(request.normalized_sku_id),
    )
    log.info("normalization.confirm.start")

    try:
        # Start transaction (implicit with db session)

        # 1. Verify supplier_item exists
        result = await db.execute(
            select(SupplierItem).where(SupplierItem.id == request.supplier_item_id)
        )
        supplier_item = result.scalar_one_or_none()
        if not supplier_item:
            log.warning("normalization.confirm.item_not_found")
            raise HTTPException(status_code=404, detail="Supplier item not found")

        # 2. Verify normalized_sku exists
        result = await db.execute(
            select(NormalizedSKU).where(NormalizedSKU.id == request.normalized_sku_id)
        )
        normalized_sku = result.scalar_one_or_none()
        if not normalized_sku:
            log.warning("normalization.confirm.sku_not_found")
            raise HTTPException(status_code=404, detail="Normalized SKU not found")

        # 3. Reject ALL existing mappings for this supplier_item
        await db.execute(
            update(SKUMapping)
            .where(SKUMapping.supplier_item_id == request.supplier_item_id)
            .values(status="rejected")
        )
        log.debug("normalization.confirm.rejected_existing")

        # 4. Check if selected mapping exists
        result = await db.execute(
            select(SKUMapping).where(
                SKUMapping.supplier_item_id == request.supplier_item_id,
                SKUMapping.normalized_sku_id == request.normalized_sku_id,
            )
        )
        existing_mapping = result.scalar_one_or_none()

        if existing_mapping:
            # Update existing mapping to confirmed
            existing_mapping.status = "confirmed"
            existing_mapping.method = "manual"
            existing_mapping.confidence = Decimal("1.0")
            existing_mapping.decided_at = datetime.utcnow()
            existing_mapping.decided_by = None  # MVP: no auth
            existing_mapping.notes = request.notes
            confirmed_mapping = existing_mapping
            log.debug("normalization.confirm.updated_existing")
        else:
            # Create new confirmed mapping
            confirmed_mapping = SKUMapping(
                supplier_item_id=request.supplier_item_id,
                normalized_sku_id=request.normalized_sku_id,
                status="confirmed",
                method="manual",
                confidence=Decimal("1.0"),
                decided_at=datetime.utcnow(),
                decided_by=None,  # MVP: no auth
                notes=request.notes,
            )
            db.add(confirmed_mapping)
            log.debug("normalization.confirm.created_new")

        await db.flush()

        # 5. Mark related task as done (if exists)
        result = await db.execute(
            select(NormalizationTask).where(
                NormalizationTask.supplier_item_id == request.supplier_item_id,
                NormalizationTask.status.in_(["open", "in_progress"]),
            )
        )
        tasks = result.scalars().all()
        for task in tasks:
            task.status = "done"
        log.debug("normalization.confirm.tasks_marked_done", count=len(tasks))

        # Commit transaction
        await db.commit()

        log.info("normalization.confirm.success")
        return ConfirmResponse(
            mapping=MappingDetail(
                id=confirmed_mapping.id,
                supplier_item_id=confirmed_mapping.supplier_item_id,
                normalized_sku_id=confirmed_mapping.normalized_sku_id,
                status=confirmed_mapping.status,
                confidence=confirmed_mapping.confidence,
                method=confirmed_mapping.method,
                decided_at=confirmed_mapping.decided_at,
                notes=confirmed_mapping.notes,
            )
        )

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error("normalization.confirm.error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Confirm failed: {str(e)}")
