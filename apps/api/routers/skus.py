"""Normalized SKU endpoints."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database import get_db
from apps.api.logging_config import get_logger
from apps.api.models import NormalizedSKU
from apps.api.services.sku_service import SKUService

router = APIRouter()
logger = get_logger(__name__)


# Pydantic schemas
class NormalizedSKUResponse(BaseModel):
    """Normalized SKU response schema."""

    id: UUID
    product_type: str
    variety: str | None
    color: str | None
    title: str
    meta: dict

    class Config:
        from_attributes = True


class NormalizedSKUCreate(BaseModel):
    """Normalized SKU creation schema."""

    product_type: str
    title: str
    variety: Optional[str] = None
    color: Optional[str] = None
    meta: dict = {}


# Endpoints
@router.post("", response_model=NormalizedSKUResponse, status_code=201)
async def create_sku(
    sku_data: NormalizedSKUCreate,
    db: AsyncSession = Depends(get_db),
) -> NormalizedSKU:
    """
    Create a new normalized SKU.

    Args:
        sku_data: SKU creation data

    Returns:
        Created normalized SKU
    """
    service = SKUService(db)
    try:
        sku = await service.create_sku(
            product_type=sku_data.product_type,
            title=sku_data.title,
            variety=sku_data.variety,
            color=sku_data.color,
            meta=sku_data.meta,
        )
        return sku
    except Exception as e:
        logger.error("sku_create_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Creation failed: {str(e)}")


@router.get("", response_model=List[NormalizedSKUResponse])
async def list_skus(
    q: Optional[str] = None,
    product_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> List[NormalizedSKU]:
    """
    List normalized SKUs with optional search and filters.

    Args:
        q: Search query (matches title, variety, product_type)
        product_type: Filter by product type
        limit: Max results (default 100)
        offset: Pagination offset

    Returns:
        List of normalized SKUs
    """
    service = SKUService(db)
    skus = await service.list_skus(
        q=q,
        product_type=product_type,
        limit=limit,
        offset=offset,
    )
    return skus


@router.get("/{sku_id}", response_model=NormalizedSKUResponse)
async def get_sku(
    sku_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> NormalizedSKU:
    """
    Get SKU by ID.

    Args:
        sku_id: SKU UUID

    Returns:
        Normalized SKU
    """
    service = SKUService(db)
    sku = await service.get_sku(sku_id)

    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")

    return sku
