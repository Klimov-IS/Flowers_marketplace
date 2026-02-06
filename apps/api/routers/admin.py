"""Admin endpoints for suppliers and imports."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import cast, func, or_, select, literal
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from apps.api.database import get_db
from apps.api.logging_config import get_logger
from apps.api.models import ImportBatch, Supplier, AISuggestion, AIRun
from apps.api.models.ai import AISuggestionStatus
from apps.api.models.items import OfferCandidate, SupplierItem
from apps.api.services.ai_enrichment_service import run_ai_enrichment_for_batch
from apps.api.services.import_service import ImportService
from apps.api.services.order_service import OrderService

router = APIRouter()
logger = get_logger(__name__)


# Pydantic schemas
class SupplierCreate(BaseModel):
    """Schema for creating a supplier."""

    name: str
    city_id: UUID | None = None
    contacts: dict = {}


class SupplierResponse(BaseModel):
    """Schema for supplier response."""

    id: UUID
    name: str
    status: str
    city_id: UUID | None
    contacts: dict

    class Config:
        from_attributes = True


class ImportBatchResponse(BaseModel):
    """Schema for import batch response."""

    id: UUID
    supplier_id: UUID
    source_type: str
    source_filename: str | None
    status: str
    imported_at: datetime

    class Config:
        from_attributes = True


class ImportSummaryResponse(BaseModel):
    """Schema for import summary response."""

    batch_id: UUID
    status: str
    raw_rows_count: int
    supplier_items_count: int
    offer_candidates_count: int
    parse_events_count: int


# AI Enrichment schemas
class AIEnrichmentResponse(BaseModel):
    """Schema for AI enrichment response."""

    status: str
    ai_run_id: Optional[UUID] = None
    auto_applied: int = 0
    applied_with_mark: int = 0
    needs_review: int = 0
    suggestions_created: int = 0
    reason: Optional[str] = None
    error: Optional[str] = None


# AI Suggestions Review schemas
class AISuggestionResponse(BaseModel):
    """Schema for a single AI suggestion."""

    id: UUID
    ai_run_id: UUID
    suggestion_type: str
    target_entity: Optional[str] = None
    target_id: Optional[UUID] = None
    field_name: Optional[str] = None
    suggested_value: dict
    confidence: Decimal
    applied_status: str
    applied_at: Optional[datetime] = None
    applied_by: Optional[str] = None
    created_at: datetime
    # Joined data
    item_raw_name: Optional[str] = None
    supplier_name: Optional[str] = None

    class Config:
        from_attributes = True


class AISuggestionsListResponse(BaseModel):
    """Schema for paginated list of AI suggestions."""

    items: List[AISuggestionResponse]
    total: int
    page: int
    per_page: int


class AISuggestionActionResponse(BaseModel):
    """Schema for accept/reject action response."""

    id: UUID
    applied_status: str
    applied_at: Optional[datetime] = None
    message: str


# Supplier Items schemas (Seller Cabinet)
class OfferVariantResponse(BaseModel):
    """Schema for offer variant (OfferCandidate) response."""

    id: UUID
    length_cm: Optional[int] = None
    pack_type: Optional[str] = None
    pack_qty: Optional[int] = None
    price: Decimal
    price_max: Optional[Decimal] = None
    stock: Optional[int] = None
    validation: str = "ok"

    class Config:
        from_attributes = True


class SupplierItemResponse(BaseModel):
    """Schema for supplier item with aggregated variants."""

    id: UUID
    raw_name: str
    origin_country: Optional[str] = None
    colors: List[str] = []
    length_min: Optional[int] = None
    length_max: Optional[int] = None
    price_min: Optional[Decimal] = None
    price_max: Optional[Decimal] = None
    stock_total: int = 0
    status: str
    source_file: Optional[str] = None
    variants_count: int = 0
    variants: List[OfferVariantResponse] = []
    attributes: Optional[dict] = None
    possible_duplicate: bool = False  # Items with same flower_type + variety

    class Config:
        from_attributes = True


class SupplierItemsListResponse(BaseModel):
    """Schema for paginated list of supplier items."""

    items: List[SupplierItemResponse]
    total: int
    page: int
    per_page: int


# Update schemas for editable table
class SupplierItemUpdate(BaseModel):
    """Schema for updating a supplier item."""

    raw_name: Optional[str] = None
    origin_country: Optional[str] = None
    colors: Optional[List[str]] = None
    variety: Optional[str] = None  # Сорт цветка


class OfferCandidateUpdate(BaseModel):
    """Schema for updating an offer candidate (variant)."""

    length_cm: Optional[int] = None
    pack_type: Optional[str] = None
    pack_qty: Optional[int] = None
    price_min: Optional[Decimal] = None
    stock_qty: Optional[int] = None


# Supplier endpoints
@router.post("/suppliers", response_model=SupplierResponse)
async def create_supplier(
    supplier_data: SupplierCreate,
    db: AsyncSession = Depends(get_db),
) -> Supplier:
    """
    Create a new supplier.

    Args:
        supplier_data: Supplier creation data
        db: Database session

    Returns:
        Created supplier
    """
    # Check if supplier with this name already exists
    result = await db.execute(
        select(Supplier).where(Supplier.name == supplier_data.name)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Supplier with this name already exists")

    supplier = Supplier(
        name=supplier_data.name,
        city_id=supplier_data.city_id,
        contacts=supplier_data.contacts,
        status="active",  # Default to active for MVP
    )
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)

    logger.info("supplier_created", supplier_id=str(supplier.id), name=supplier.name)
    return supplier


@router.get("/suppliers", response_model=List[SupplierResponse])
async def list_suppliers(db: AsyncSession = Depends(get_db)) -> List[Supplier]:
    """
    List all suppliers.

    Args:
        db: Database session

    Returns:
        List of suppliers
    """
    result = await db.execute(select(Supplier).order_by(Supplier.name))
    suppliers = result.scalars().all()
    return list(suppliers)


@router.get("/suppliers/{supplier_id}/items", response_model=SupplierItemsListResponse)
async def get_supplier_items(
    supplier_id: UUID,
    q: Optional[str] = Query(None, description="Search query for item name"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    status: Optional[List[str]] = Query(
        default=["active"],
        description="Filter by status (active, hidden, deleted). Default: active only"
    ),
    # Additional column filters
    origin_country: Optional[List[str]] = Query(
        None, description="Filter by origin country (use '__null__' for items without country)"
    ),
    colors: Optional[List[str]] = Query(
        None, description="Filter by color (use '__null__' for items without color)"
    ),
    price_min: Optional[Decimal] = Query(None, description="Minimum price filter"),
    price_max: Optional[Decimal] = Query(None, description="Maximum price filter"),
    length_min: Optional[int] = Query(None, description="Minimum length filter (cm)"),
    length_max: Optional[int] = Query(None, description="Maximum length filter (cm)"),
    stock_min: Optional[int] = Query(None, description="Minimum stock filter"),
    stock_max: Optional[int] = Query(None, description="Maximum stock filter"),
    sort_by: Optional[str] = Query(
        None,
        description="Sort by field (raw_name, origin_country, price_min, length_min, stock_total)"
    ),
    sort_dir: Optional[str] = Query(
        "asc",
        description="Sort direction (asc, desc)"
    ),
    db: AsyncSession = Depends(get_db),
) -> SupplierItemsListResponse:
    """
    Get paginated list of supplier items with aggregated variants.

    Args:
        supplier_id: Supplier UUID
        q: Optional search query
        page: Page number (1-based)
        per_page: Items per page
        status: Filter by item status (active, hidden, deleted)
        db: Database session

    Returns:
        Paginated list of supplier items with variants
    """
    # Verify supplier exists
    supplier_result = await db.execute(
        select(Supplier).where(Supplier.id == supplier_id)
    )
    supplier = supplier_result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Create aggregation subquery from offer_candidates
    aggregates_subq = (
        select(
            OfferCandidate.supplier_item_id,
            func.min(OfferCandidate.price_min).label('agg_price_min'),
            func.max(OfferCandidate.price_min).label('agg_price_max'),
            func.min(OfferCandidate.length_cm).label('agg_length_min'),
            func.max(OfferCandidate.length_cm).label('agg_length_max'),
            func.coalesce(func.sum(OfferCandidate.stock_qty), 0).label('agg_stock_total'),
        )
        .group_by(OfferCandidate.supplier_item_id)
        .subquery('aggregates')
    )

    # Build base query with aggregates join
    base_query = (
        select(SupplierItem)
        .outerjoin(aggregates_subq, SupplierItem.id == aggregates_subq.c.supplier_item_id)
        .where(SupplierItem.supplier_id == supplier_id)
    )

    # Apply status filter
    if status:
        base_query = base_query.where(SupplierItem.status.in_(status))

    # Apply search filter if provided
    if q:
        search_term = f"%{q.lower()}%"
        base_query = base_query.where(
            or_(
                SupplierItem.raw_name.ilike(search_term),
                SupplierItem.name_norm.ilike(search_term),
                SupplierItem.attributes['clean_name'].astext.ilike(search_term),
            )
        )

    # Apply origin_country filter (from JSONB attributes)
    if origin_country:
        origin_col = SupplierItem.attributes['origin_country'].astext
        include_null = "__null__" in origin_country
        actual_countries = [c for c in origin_country if c != "__null__"]
        if include_null and actual_countries:
            base_query = base_query.where(
                or_(
                    origin_col.in_(actual_countries),
                    origin_col.is_(None),
                    ~SupplierItem.attributes.has_key('origin_country'),
                )
            )
        elif include_null:
            base_query = base_query.where(
                or_(
                    origin_col.is_(None),
                    ~SupplierItem.attributes.has_key('origin_country'),
                )
            )
        elif actual_countries:
            base_query = base_query.where(origin_col.in_(actual_countries))

    # Apply colors filter (from JSONB attributes)
    if colors:
        colors_col = SupplierItem.attributes['colors']
        include_null = "__null__" in colors
        actual_colors = [c for c in colors if c != "__null__"]
        if include_null and actual_colors:
            # Items with any of the specified colors OR empty/missing colors
            base_query = base_query.where(
                or_(
                    colors_col.op('?|')(actual_colors),  # contains any
                    colors_col == cast('[]', JSONB),
                    ~SupplierItem.attributes.has_key('colors'),
                )
            )
        elif include_null:
            base_query = base_query.where(
                or_(
                    colors_col == cast('[]', JSONB),
                    ~SupplierItem.attributes.has_key('colors'),
                )
            )
        elif actual_colors:
            base_query = base_query.where(colors_col.op('?|')(actual_colors))

    # Apply price range filter (from aggregated offer_candidates)
    if price_min is not None:
        base_query = base_query.where(aggregates_subq.c.agg_price_max >= price_min)
    if price_max is not None:
        base_query = base_query.where(aggregates_subq.c.agg_price_min <= price_max)

    # Apply length range filter (from aggregated offer_candidates)
    if length_min is not None:
        base_query = base_query.where(aggregates_subq.c.agg_length_max >= length_min)
    if length_max is not None:
        base_query = base_query.where(aggregates_subq.c.agg_length_min <= length_max)

    # Apply stock filter (from aggregated offer_candidates)
    if stock_min is not None:
        base_query = base_query.where(aggregates_subq.c.agg_stock_total >= stock_min)
    if stock_max is not None:
        base_query = base_query.where(aggregates_subq.c.agg_stock_total <= stock_max)

    # Count total items
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * per_page

    # Build order clause based on sort_by parameter
    sort_column_map = {
        "raw_name": SupplierItem.raw_name,
        "origin_country": SupplierItem.attributes['origin_country'].astext,
        "price_min": aggregates_subq.c.agg_price_min,
        "length_min": aggregates_subq.c.agg_length_min,
        "stock_total": aggregates_subq.c.agg_stock_total,
    }

    order_column = sort_column_map.get(sort_by, SupplierItem.raw_name)
    if sort_dir == "desc":
        order_clause = order_column.desc().nullslast()
    else:
        order_clause = order_column.asc().nullslast()

    items_query = base_query.order_by(order_clause).offset(offset).limit(per_page)

    items_result = await db.execute(items_query)
    supplier_items = items_result.scalars().all()

    # Get all item IDs for batch loading variants
    item_ids = [item.id for item in supplier_items]

    # Fetch duplicate (flower_type, variety) combinations for this supplier
    # Use raw SQL to avoid SQLAlchemy parameter binding issues with GROUP BY
    from sqlalchemy import text
    duplicate_sql = text("""
        SELECT
            attributes->>'flower_type' as ft,
            attributes->>'variety' as var
        FROM supplier_items
        WHERE supplier_id = :supplier_id
            AND status != 'deleted'
            AND attributes->>'flower_type' IS NOT NULL
            AND attributes->>'variety' IS NOT NULL
        GROUP BY attributes->>'flower_type', attributes->>'variety'
        HAVING COUNT(*) > 1
    """)
    duplicate_result = await db.execute(duplicate_sql, {"supplier_id": supplier_id})
    duplicate_combos = {(row.ft, row.var) for row in duplicate_result.all()}

    # Load all offer candidates for these items
    if item_ids:
        variants_query = select(OfferCandidate).where(
            OfferCandidate.supplier_item_id.in_(item_ids)
        )
        variants_result = await db.execute(variants_query)
        all_variants = variants_result.scalars().all()

        # Group variants by supplier_item_id
        variants_by_item: dict[UUID, list[OfferCandidate]] = {}
        for variant in all_variants:
            if variant.supplier_item_id not in variants_by_item:
                variants_by_item[variant.supplier_item_id] = []
            variants_by_item[variant.supplier_item_id].append(variant)
    else:
        variants_by_item = {}

    # Get import batch info for source_file
    batch_ids = [item.last_import_batch_id for item in supplier_items if item.last_import_batch_id]
    batches_by_id: dict[UUID, ImportBatch] = {}
    if batch_ids:
        batches_query = select(ImportBatch).where(ImportBatch.id.in_(batch_ids))
        batches_result = await db.execute(batches_query)
        for batch in batches_result.scalars().all():
            batches_by_id[batch.id] = batch

    # Build response items with aggregated data
    response_items = []
    for item in supplier_items:
        variants = variants_by_item.get(item.id, [])

        # Extract attributes
        attributes = item.attributes or {}
        origin_country = attributes.get("origin_country")
        colors = attributes.get("colors", [])
        if isinstance(colors, str):
            colors = [colors]

        # Aggregate variant data
        lengths = [v.length_cm for v in variants if v.length_cm is not None]
        prices = [v.price_min for v in variants if v.price_min is not None]
        stocks = [v.stock_qty for v in variants if v.stock_qty is not None]

        length_min = min(lengths) if lengths else None
        length_max = max(lengths) if lengths else None
        price_min = min(prices) if prices else None
        price_max = max(prices) if prices else None
        stock_total = sum(stocks) if stocks else 0

        # Get source file name
        source_file = None
        if item.last_import_batch_id and item.last_import_batch_id in batches_by_id:
            source_file = batches_by_id[item.last_import_batch_id].source_filename

        # Check if item is a possible duplicate
        flower_type = attributes.get("flower_type")
        variety = attributes.get("variety")
        is_possible_duplicate = bool(
            flower_type and variety and (flower_type, variety) in duplicate_combos
        )

        # Build variant responses
        variant_responses = [
            OfferVariantResponse(
                id=v.id,
                length_cm=v.length_cm,
                pack_type=v.pack_type,
                pack_qty=v.pack_qty,
                price=v.price_min,
                price_max=v.price_max,
                stock=v.stock_qty,
                validation=v.validation,
            )
            for v in variants
        ]

        response_items.append(
            SupplierItemResponse(
                id=item.id,
                raw_name=item.raw_name,
                origin_country=origin_country,
                colors=colors,
                length_min=length_min,
                length_max=length_max,
                price_min=price_min,
                price_max=price_max,
                stock_total=stock_total,
                status=item.status,
                source_file=source_file,
                variants_count=len(variants),
                variants=variant_responses,
                attributes=item.attributes,
                possible_duplicate=is_possible_duplicate,
            )
        )

    logger.info(
        "supplier_items_fetched",
        supplier_id=str(supplier_id),
        total=total,
        page=page,
        per_page=per_page,
    )

    return SupplierItemsListResponse(
        items=response_items,
        total=total,
        page=page,
        per_page=per_page,
    )


# Import endpoints
@router.post("/suppliers/{supplier_id}/imports/csv", response_model=ImportBatchResponse)
async def upload_csv_import(
    supplier_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> ImportBatch:
    """
    Upload and import a CSV price list for a supplier.

    Args:
        supplier_id: Supplier UUID
        file: CSV file upload
        db: Database session

    Returns:
        Created import batch
    """
    # Verify supplier exists
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Validate file type
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    # Read file content
    content = await file.read()

    # Import CSV
    import_service = ImportService(db)
    try:
        import_batch = await import_service.import_csv(
            supplier_id=supplier_id,
            filename=file.filename,
            content=content,
        )
        logger.info(
            "csv_import_completed",
            batch_id=str(import_batch.id),
            supplier_id=str(supplier_id),
            filename=file.filename,
        )
        return import_batch
    except Exception as e:
        logger.error(
            "csv_import_failed",
            supplier_id=str(supplier_id),
            filename=file.filename,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/imports/{import_batch_id}", response_model=ImportSummaryResponse)
async def get_import_summary(
    import_batch_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ImportSummaryResponse:
    """
    Get import batch summary with counts.

    Args:
        import_batch_id: Import batch UUID
        db: Database session

    Returns:
        Import summary
    """
    import_service = ImportService(db)
    summary = await import_service.get_import_summary(import_batch_id)

    if not summary:
        raise HTTPException(status_code=404, detail="Import batch not found")

    return summary


# AI Enrichment endpoint
@router.post("/imports/{import_batch_id}/ai-enrich", response_model=AIEnrichmentResponse)
async def run_ai_enrichment(
    import_batch_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AIEnrichmentResponse:
    """
    Manually trigger AI enrichment for an import batch.

    This endpoint allows re-running AI enrichment on items that may have been
    missed during initial import or when AI was not available.

    Args:
        import_batch_id: Import batch UUID
        db: Database session

    Returns:
        AI enrichment result
    """
    # Get the import batch to find supplier_id
    result = await db.execute(
        select(ImportBatch).where(ImportBatch.id == import_batch_id)
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")

    logger.info(
        "ai_enrichment_manual_trigger",
        batch_id=str(import_batch_id),
        supplier_id=str(batch.supplier_id),
    )

    try:
        ai_result = await run_ai_enrichment_for_batch(
            db=db,
            supplier_id=batch.supplier_id,
            import_batch_id=import_batch_id,
        )

        logger.info(
            "ai_enrichment_manual_complete",
            batch_id=str(import_batch_id),
            status=ai_result.get("status"),
        )

        return AIEnrichmentResponse(
            status=ai_result.get("status", "unknown"),
            ai_run_id=ai_result.get("ai_run_id"),
            auto_applied=ai_result.get("auto_applied", 0),
            applied_with_mark=ai_result.get("applied_with_mark", 0),
            needs_review=ai_result.get("needs_review", 0),
            suggestions_created=ai_result.get("suggestions_created", 0),
            reason=ai_result.get("reason"),
            error=ai_result.get("error"),
        )

    except Exception as e:
        logger.error(
            "ai_enrichment_manual_failed",
            batch_id=str(import_batch_id),
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"AI enrichment failed: {str(e)}")


# AI Suggestions Review endpoints
@router.get("/ai/suggestions", response_model=AISuggestionsListResponse)
async def list_ai_suggestions(
    status: Optional[str] = Query(None, description="Filter by status (needs_review, pending, auto_applied, rejected)"),
    supplier_id: Optional[UUID] = Query(None, description="Filter by supplier"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> AISuggestionsListResponse:
    """
    List AI suggestions for review.

    Args:
        status: Filter by applied_status
        supplier_id: Filter by supplier
        page: Page number (1-based)
        per_page: Items per page
        db: Database session

    Returns:
        Paginated list of AI suggestions
    """
    # Build query with joins
    query = (
        select(AISuggestion, SupplierItem.raw_name, Supplier.name)
        .join(AIRun, AISuggestion.ai_run_id == AIRun.id)
        .outerjoin(SupplierItem, AISuggestion.target_id == SupplierItem.id)
        .outerjoin(Supplier, AIRun.supplier_id == Supplier.id)
    )

    # Apply filters
    if status:
        query = query.where(AISuggestion.applied_status == status)
    if supplier_id:
        query = query.where(AIRun.supplier_id == supplier_id)

    # Count total
    count_query = select(func.count()).select_from(
        query.with_only_columns(AISuggestion.id).subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering (newest first, then by confidence desc)
    offset = (page - 1) * per_page
    query = query.order_by(
        AISuggestion.created_at.desc(),
        AISuggestion.confidence.desc(),
    ).offset(offset).limit(per_page)

    result = await db.execute(query)
    rows = result.all()

    # Build response
    items = []
    for suggestion, item_raw_name, supplier_name in rows:
        items.append(
            AISuggestionResponse(
                id=suggestion.id,
                ai_run_id=suggestion.ai_run_id,
                suggestion_type=suggestion.suggestion_type,
                target_entity=suggestion.target_entity,
                target_id=suggestion.target_id,
                field_name=suggestion.field_name,
                suggested_value=suggestion.suggested_value,
                confidence=suggestion.confidence,
                applied_status=suggestion.applied_status,
                applied_at=suggestion.applied_at,
                applied_by=suggestion.applied_by,
                created_at=suggestion.created_at,
                item_raw_name=item_raw_name,
                supplier_name=supplier_name,
            )
        )

    logger.info(
        "ai_suggestions_listed",
        status_filter=status,
        supplier_id=str(supplier_id) if supplier_id else None,
        total=total,
        page=page,
    )

    return AISuggestionsListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.patch("/ai/suggestions/{suggestion_id}/accept", response_model=AISuggestionActionResponse)
async def accept_ai_suggestion(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AISuggestionActionResponse:
    """
    Accept and apply an AI suggestion.

    Args:
        suggestion_id: Suggestion UUID
        db: Database session

    Returns:
        Action result
    """
    # Find the suggestion
    result = await db.execute(
        select(AISuggestion).where(AISuggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    # Check if already processed
    if suggestion.applied_status in [AISuggestionStatus.MANUAL_APPLIED.value, AISuggestionStatus.REJECTED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Suggestion already processed with status: {suggestion.applied_status}",
        )

    # Apply the suggestion to the target entity
    if suggestion.target_entity == "supplier_item" and suggestion.target_id and suggestion.field_name:
        item_result = await db.execute(
            select(SupplierItem).where(SupplierItem.id == suggestion.target_id)
        )
        item = item_result.scalar_one_or_none()
        if item:
            attributes = item.attributes or {}
            sources = attributes.get("_sources", {})

            # Apply value
            value = suggestion.suggested_value.get("value")
            attributes[suggestion.field_name] = value
            sources[suggestion.field_name] = "ai"

            # Update confidences
            confidences = attributes.get("_confidences", {})
            confidences[suggestion.field_name] = float(suggestion.confidence)
            attributes["_confidences"] = confidences

            attributes["_sources"] = sources
            item.attributes = attributes
            flag_modified(item, "attributes")

    # Update suggestion status
    suggestion.applied_status = AISuggestionStatus.MANUAL_APPLIED.value
    suggestion.applied_at = datetime.utcnow()
    suggestion.applied_by = "admin"

    await db.commit()

    logger.info(
        "ai_suggestion_accepted",
        suggestion_id=str(suggestion_id),
        field_name=suggestion.field_name,
        value=suggestion.suggested_value,
    )

    return AISuggestionActionResponse(
        id=suggestion.id,
        applied_status=suggestion.applied_status,
        applied_at=suggestion.applied_at,
        message=f"Suggestion accepted and applied to {suggestion.field_name}",
    )


@router.patch("/ai/suggestions/{suggestion_id}/reject", response_model=AISuggestionActionResponse)
async def reject_ai_suggestion(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AISuggestionActionResponse:
    """
    Reject an AI suggestion.

    Args:
        suggestion_id: Suggestion UUID
        db: Database session

    Returns:
        Action result
    """
    # Find the suggestion
    result = await db.execute(
        select(AISuggestion).where(AISuggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    # Check if already processed
    if suggestion.applied_status in [AISuggestionStatus.MANUAL_APPLIED.value, AISuggestionStatus.REJECTED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Suggestion already processed with status: {suggestion.applied_status}",
        )

    # Update suggestion status
    suggestion.applied_status = AISuggestionStatus.REJECTED.value
    suggestion.applied_at = datetime.utcnow()
    suggestion.applied_by = "admin"

    await db.commit()

    logger.info(
        "ai_suggestion_rejected",
        suggestion_id=str(suggestion_id),
        field_name=suggestion.field_name,
    )

    return AISuggestionActionResponse(
        id=suggestion.id,
        applied_status=suggestion.applied_status,
        applied_at=suggestion.applied_at,
        message=f"Suggestion rejected for {suggestion.field_name}",
    )


# Supplier Item Update endpoint (for editable table)
@router.patch("/supplier-items/{item_id}", response_model=SupplierItemResponse)
async def update_supplier_item(
    item_id: UUID,
    data: SupplierItemUpdate,
    db: AsyncSession = Depends(get_db),
) -> SupplierItemResponse:
    """
    Update a supplier item's editable fields.

    Args:
        item_id: Supplier item UUID
        data: Fields to update
        db: Database session

    Returns:
        Updated supplier item
    """
    # Find the item
    result = await db.execute(
        select(SupplierItem).where(SupplierItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Supplier item not found")

    # Update fields
    if data.raw_name is not None:
        item.raw_name = data.raw_name

    # Handle attributes updates with source tracking
    attributes = item.attributes or {}
    sources = attributes.get("_sources", {})
    locked = attributes.get("_locked", [])

    if data.origin_country is not None:
        # Check if field is not locked
        if "origin_country" not in locked:
            attributes["origin_country"] = data.origin_country
            sources["origin_country"] = "manual"

    if data.colors is not None:
        if "colors" not in locked:
            attributes["colors"] = data.colors
            sources["colors"] = "manual"

    if data.variety is not None:
        if "variety" not in locked:
            attributes["variety"] = data.variety
            sources["variety"] = "manual"

    # Update sources metadata
    attributes["_sources"] = sources
    item.attributes = attributes
    flag_modified(item, "attributes")  # Mark JSON field as modified

    await db.commit()
    await db.refresh(item)

    # Load variants for response
    variants_query = select(OfferCandidate).where(
        OfferCandidate.supplier_item_id == item_id
    )
    variants_result = await db.execute(variants_query)
    variants = variants_result.scalars().all()

    # Extract attributes
    origin_country = attributes.get("origin_country")
    colors = attributes.get("colors", [])
    if isinstance(colors, str):
        colors = [colors]

    # Aggregate variant data
    lengths = [v.length_cm for v in variants if v.length_cm is not None]
    prices = [v.price_min for v in variants if v.price_min is not None]
    stocks = [v.stock_qty for v in variants if v.stock_qty is not None]

    variant_responses = [
        OfferVariantResponse(
            id=v.id,
            length_cm=v.length_cm,
            pack_type=v.pack_type,
            pack_qty=v.pack_qty,
            price=v.price_min,
            price_max=v.price_max,
            stock=v.stock_qty,
            validation=v.validation,
        )
        for v in variants
    ]

    logger.info(
        "supplier_item_updated",
        item_id=str(item_id),
        updated_fields=data.model_dump(exclude_unset=True),
    )

    return SupplierItemResponse(
        id=item.id,
        raw_name=item.raw_name,
        origin_country=origin_country,
        colors=colors,
        length_min=min(lengths) if lengths else None,
        length_max=max(lengths) if lengths else None,
        price_min=min(prices) if prices else None,
        price_max=max(prices) if prices else None,
        stock_total=sum(stocks) if stocks else 0,
        status=item.status,
        source_file=None,
        variants_count=len(variants),
        variants=variant_responses,
        attributes=item.attributes,
    )


# Offer Candidate Update endpoint (for editable table)
@router.patch("/offer-candidates/{candidate_id}", response_model=OfferVariantResponse)
async def update_offer_candidate(
    candidate_id: UUID,
    data: OfferCandidateUpdate,
    db: AsyncSession = Depends(get_db),
) -> OfferVariantResponse:
    """
    Update an offer candidate (variant) fields.

    Args:
        candidate_id: Offer candidate UUID
        data: Fields to update
        db: Database session

    Returns:
        Updated offer candidate
    """
    # Find the candidate
    result = await db.execute(
        select(OfferCandidate).where(OfferCandidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Offer candidate not found")

    # Update fields
    if data.length_cm is not None:
        candidate.length_cm = data.length_cm
    if data.pack_type is not None:
        candidate.pack_type = data.pack_type
    if data.pack_qty is not None:
        candidate.pack_qty = data.pack_qty
    if data.price_min is not None:
        candidate.price_min = data.price_min
    if data.stock_qty is not None:
        candidate.stock_qty = data.stock_qty

    await db.commit()
    await db.refresh(candidate)

    logger.info(
        "offer_candidate_updated",
        candidate_id=str(candidate_id),
        updated_fields=data.model_dump(exclude_unset=True),
    )

    return OfferVariantResponse(
        id=candidate.id,
        length_cm=candidate.length_cm,
        pack_type=candidate.pack_type,
        pack_qty=candidate.pack_qty,
        price=candidate.price_min,
        price_max=candidate.price_max,
        stock=candidate.stock_qty,
        validation=candidate.validation,
    )


# ============================================================================
# Supplier Item Actions (delete, hide, restore)
# ============================================================================

class ItemActionResponse(BaseModel):
    """Response for item action endpoints."""
    id: UUID
    status: str
    message: str


class BulkActionRequest(BaseModel):
    """Request for bulk actions."""
    item_ids: List[UUID]


class BulkActionResponse(BaseModel):
    """Response for bulk actions."""
    affected_count: int
    status: str
    message: str


@router.delete("/supplier-items/{item_id}", response_model=ItemActionResponse)
async def delete_supplier_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ItemActionResponse:
    """
    Soft delete a supplier item (sets status to 'deleted').

    The item remains in DB but won't appear in listings by default.
    Can be restored using the restore endpoint.
    """
    from datetime import datetime

    result = await db.execute(
        select(SupplierItem).where(SupplierItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Supplier item not found")

    item.status = "deleted"
    item.deleted_at = datetime.utcnow()

    await db.commit()

    logger.info(
        "supplier_item_deleted",
        item_id=str(item_id),
        supplier_id=str(item.supplier_id),
    )

    return ItemActionResponse(
        id=item_id,
        status="deleted",
        message="Item deleted successfully",
    )


@router.post("/supplier-items/{item_id}/hide", response_model=ItemActionResponse)
async def hide_supplier_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ItemActionResponse:
    """
    Hide a supplier item (sets status to 'hidden').

    Hidden items won't appear in public catalog but remain manageable.
    """
    result = await db.execute(
        select(SupplierItem).where(SupplierItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Supplier item not found")

    item.status = "hidden"

    await db.commit()

    logger.info(
        "supplier_item_hidden",
        item_id=str(item_id),
        supplier_id=str(item.supplier_id),
    )

    return ItemActionResponse(
        id=item_id,
        status="hidden",
        message="Item hidden successfully",
    )


@router.post("/supplier-items/{item_id}/restore", response_model=ItemActionResponse)
async def restore_supplier_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ItemActionResponse:
    """
    Restore a hidden or deleted supplier item (sets status to 'active').
    """
    result = await db.execute(
        select(SupplierItem).where(SupplierItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Supplier item not found")

    item.status = "active"
    item.deleted_at = None

    await db.commit()

    logger.info(
        "supplier_item_restored",
        item_id=str(item_id),
        supplier_id=str(item.supplier_id),
    )

    return ItemActionResponse(
        id=item_id,
        status="active",
        message="Item restored successfully",
    )


@router.post("/supplier-items/bulk-delete", response_model=BulkActionResponse)
async def bulk_delete_supplier_items(
    request: BulkActionRequest,
    db: AsyncSession = Depends(get_db),
) -> BulkActionResponse:
    """
    Bulk soft delete supplier items.
    """
    from datetime import datetime
    from sqlalchemy import update

    result = await db.execute(
        update(SupplierItem)
        .where(SupplierItem.id.in_(request.item_ids))
        .values(status="deleted", deleted_at=datetime.utcnow())
    )

    await db.commit()

    affected = result.rowcount

    logger.info(
        "supplier_items_bulk_deleted",
        item_count=affected,
        item_ids=[str(id) for id in request.item_ids],
    )

    return BulkActionResponse(
        affected_count=affected,
        status="deleted",
        message=f"Deleted {affected} items",
    )


@router.post("/supplier-items/bulk-hide", response_model=BulkActionResponse)
async def bulk_hide_supplier_items(
    request: BulkActionRequest,
    db: AsyncSession = Depends(get_db),
) -> BulkActionResponse:
    """
    Bulk hide supplier items.
    """
    from sqlalchemy import update

    result = await db.execute(
        update(SupplierItem)
        .where(SupplierItem.id.in_(request.item_ids))
        .values(status="hidden")
    )

    await db.commit()

    affected = result.rowcount

    logger.info(
        "supplier_items_bulk_hidden",
        item_count=affected,
        item_ids=[str(id) for id in request.item_ids],
    )

    return BulkActionResponse(
        affected_count=affected,
        status="hidden",
        message=f"Hidden {affected} items",
    )


@router.post("/supplier-items/bulk-restore", response_model=BulkActionResponse)
async def bulk_restore_supplier_items(
    request: BulkActionRequest,
    db: AsyncSession = Depends(get_db),
) -> BulkActionResponse:
    """
    Bulk restore supplier items (set to active).
    """
    from sqlalchemy import update

    result = await db.execute(
        update(SupplierItem)
        .where(SupplierItem.id.in_(request.item_ids))
        .values(status="active", deleted_at=None)
    )

    await db.commit()

    affected = result.rowcount

    logger.info(
        "supplier_items_bulk_restored",
        item_count=affected,
        item_ids=[str(id) for id in request.item_ids],
    )

    return BulkActionResponse(
        affected_count=affected,
        status="active",
        message=f"Restored {affected} items",
    )


# Bundle split endpoint
class SplitBundleRequest(BaseModel):
    """Request to split a bundle item into separate items."""

    varieties: list[str] = Field(..., min_length=1, description="List of variety names to create")
    delete_original: bool = Field(default=True, description="Delete original bundle item after split")


class SplitBundleResponse(BaseModel):
    """Response after splitting a bundle."""

    original_item_id: UUID
    created_count: int
    created_item_ids: list[UUID]
    original_deleted: bool
    message: str


@router.post("/supplier-items/{item_id}/split-bundle", response_model=SplitBundleResponse)
async def split_bundle_item(
    item_id: UUID,
    request: SplitBundleRequest,
    db: AsyncSession = Depends(get_db),
) -> SplitBundleResponse:
    """
    Split a bundle item (multiple varieties in one row) into separate items.

    This endpoint:
    1. Validates the original item is a bundle
    2. Creates new supplier items for each variety
    3. Copies offer candidates with updated names
    4. Optionally deletes or marks original as processed

    Args:
        item_id: Original bundle item UUID
        request: Varieties to create and options
        db: Database session

    Returns:
        Summary of split operation
    """
    from packages.core.parsing import generate_stable_key, normalize_name
    from apps.api.models import OfferCandidate

    # Find the original item
    result = await db.execute(
        select(SupplierItem).where(SupplierItem.id == item_id)
    )
    original_item = result.scalar_one_or_none()
    if not original_item:
        raise HTTPException(status_code=404, detail="Supplier item not found")

    # Validate it's a bundle
    attrs = original_item.attributes or {}
    if not attrs.get("is_bundle_list"):
        raise HTTPException(
            status_code=400,
            detail="Item is not a bundle list. Cannot split.",
        )

    # Get original offer candidates
    result = await db.execute(
        select(OfferCandidate).where(OfferCandidate.supplier_item_id == item_id)
    )
    original_candidates = result.scalars().all()

    created_item_ids = []
    flower_type = attrs.get("flower_type", "")

    for variety in request.varieties:
        variety = variety.strip()
        if not variety:
            continue

        # Build new name: "FlowerType Variety"
        new_name = f"{flower_type} {variety}" if flower_type else variety

        # Generate stable key
        stable_key = generate_stable_key(
            supplier_id=original_item.supplier_id,
            raw_name=new_name,
            raw_group=None,
        )

        # Check if item already exists
        result = await db.execute(
            select(SupplierItem).where(
                SupplierItem.supplier_id == original_item.supplier_id,
                SupplierItem.stable_key == stable_key,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            logger.warning(
                "split_bundle_item_exists",
                original_id=str(item_id),
                variety=variety,
                existing_id=str(existing.id),
            )
            continue

        # Create new attributes
        new_attrs = {
            "flower_type": flower_type,
            "variety": variety,
            "clean_name": new_name,
            "origin_country": attrs.get("origin_country"),
            "colors": attrs.get("colors", []),
            "_sources": {
                "flower_type": "parser",
                "variety": "manual",
                "clean_name": "manual",
            },
            "_split_from": str(item_id),  # Track origin
        }
        new_attrs = {k: v for k, v in new_attrs.items() if v is not None}

        # Create new supplier item
        new_item = SupplierItem(
            supplier_id=original_item.supplier_id,
            stable_key=stable_key,
            last_import_batch_id=original_item.last_import_batch_id,
            raw_name=new_name,
            raw_group=original_item.raw_group,
            name_norm=normalize_name(new_name),
            attributes=new_attrs,
            status="active",
        )
        db.add(new_item)
        await db.flush()

        created_item_ids.append(new_item.id)

        # Copy offer candidates
        for oc in original_candidates:
            new_candidate = OfferCandidate(
                supplier_item_id=new_item.id,
                import_batch_id=oc.import_batch_id,
                validation=oc.validation,
                length_cm=oc.length_cm,
                pack_type=oc.pack_type,
                pack_qty=oc.pack_qty,
                price_type=oc.price_type,
                price_min=oc.price_min,
                price_max=oc.price_max,
                currency=oc.currency,
                tier_min_qty=oc.tier_min_qty,
                tier_max_qty=oc.tier_max_qty,
                availability=oc.availability,
                stock_qty=oc.stock_qty,
            )
            db.add(new_candidate)

    # Handle original item
    original_deleted = False
    if request.delete_original and created_item_ids:
        original_item.status = "deleted"
        original_item.deleted_at = datetime.utcnow()
        original_deleted = True
    elif created_item_ids:
        # Mark as processed but keep
        attrs["_split_completed"] = True
        attrs["_split_into"] = [str(id) for id in created_item_ids]
        attrs["is_bundle_list"] = False  # No longer a bundle
        attrs["needs_review"] = False
        original_item.attributes = attrs
        flag_modified(original_item, "attributes")

    await db.commit()

    logger.info(
        "bundle_split_completed",
        original_id=str(item_id),
        created_count=len(created_item_ids),
        varieties=request.varieties,
        original_deleted=original_deleted,
    )

    return SplitBundleResponse(
        original_item_id=item_id,
        created_count=len(created_item_ids),
        created_item_ids=created_item_ids,
        original_deleted=original_deleted,
        message=f"Created {len(created_item_ids)} items from bundle",
    )


# Order metrics endpoint
class OrderMetricsResponse(BaseModel):
    """Schema for order metrics response."""

    total_orders: int
    pending: int
    confirmed: int
    rejected: int
    cancelled: int
    total_revenue: Decimal


@router.get("/orders/metrics", response_model=OrderMetricsResponse)
async def get_order_metrics(
    db: AsyncSession = Depends(get_db),
) -> OrderMetricsResponse:
    """
    Get global order statistics (admin endpoint).

    Args:
        db: Database session

    Returns:
        Order metrics across all suppliers
    """
    order_service = OrderService(db)
    metrics = await order_service.get_order_metrics()

    return OrderMetricsResponse(**metrics)


# Reparse endpoint
class ReparseResponse(BaseModel):
    """Schema for reparse response."""

    total: int
    updated: int
    unchanged: int
    errors: int
    sample_changes: list = Field(default_factory=list)


@router.post("/supplier-items/reparse", response_model=ReparseResponse)
async def reparse_supplier_items(
    supplier_id: Optional[UUID] = Query(None, description="Limit to specific supplier"),
    dry_run: bool = Query(False, description="Don't save changes, just preview"),
    db: AsyncSession = Depends(get_db),
) -> ReparseResponse:
    """
    Re-parse all supplier items with the updated parser.

    This endpoint re-runs the name normalization parser on existing
    supplier_items to update flower_type, variety, clean_name, etc.
    after parser improvements.

    Args:
        supplier_id: Optional supplier UUID to limit reparse
        dry_run: If True, returns what would change without saving
        db: Database session

    Returns:
        Statistics about updated items
    """
    from packages.core.parsing.name_normalizer import normalize_name

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
        "sample_changes": [],
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

                # Track sample changes (limit to 20)
                if len(stats["sample_changes"]) < 20:
                    stats["sample_changes"].append({
                        "id": str(item.id),
                        "raw_name": item.raw_name[:60],
                        "old_clean": old_clean,
                        "new_clean": new_clean,
                        "old_type": existing.get("flower_type"),
                        "new_type": new_attrs.get("flower_type"),
                    })

                if not dry_run:
                    item.attributes = merged
                    flag_modified(item, "attributes")

                stats["updated"] += 1
            else:
                stats["unchanged"] += 1

        except Exception as e:
            stats["errors"] += 1
            logger.error("reparse_error", item_id=str(item.id), error=str(e))

    if not dry_run:
        await db.commit()
        logger.info(
            "reparse_completed",
            total=stats["total"],
            updated=stats["updated"],
            supplier_id=str(supplier_id) if supplier_id else "all",
        )

    return ReparseResponse(**stats)
