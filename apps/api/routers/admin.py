"""Admin endpoints for suppliers and imports."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.database import get_db
from apps.api.logging_config import get_logger
from apps.api.models import ImportBatch, Supplier
from apps.api.models.items import OfferCandidate, SupplierItem
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
    db: AsyncSession = Depends(get_db),
) -> SupplierItemsListResponse:
    """
    Get paginated list of supplier items with aggregated variants.

    Args:
        supplier_id: Supplier UUID
        q: Optional search query
        page: Page number (1-based)
        per_page: Items per page
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

    # Build base query for supplier items
    base_query = select(SupplierItem).where(SupplierItem.supplier_id == supplier_id)

    # Apply search filter if provided
    if q:
        search_term = f"%{q.lower()}%"
        base_query = base_query.where(
            or_(
                SupplierItem.raw_name.ilike(search_term),
                SupplierItem.name_norm.ilike(search_term),
            )
        )

    # Count total items
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * per_page
    items_query = base_query.order_by(SupplierItem.raw_name).offset(offset).limit(per_page)

    items_result = await db.execute(items_query)
    supplier_items = items_result.scalars().all()

    # Get all item IDs for batch loading variants
    item_ids = [item.id for item in supplier_items]

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

    # Handle attributes updates
    attributes = item.attributes or {}
    if data.origin_country is not None:
        attributes["origin_country"] = data.origin_country
    if data.colors is not None:
        attributes["colors"] = data.colors
    item.attributes = attributes

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
