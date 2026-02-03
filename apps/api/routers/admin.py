"""Admin endpoints for suppliers and imports."""
from decimal import Decimal
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database import get_db
from apps.api.logging_config import get_logger
from apps.api.models import ImportBatch, Supplier
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
    imported_at: str

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
