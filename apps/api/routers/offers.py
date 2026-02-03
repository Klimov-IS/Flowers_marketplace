"""Offers endpoints (retail/public)."""
import structlog
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.api.database import get_db
from apps.api.models import NormalizedSKU, Offer, Supplier

logger = structlog.get_logger()
router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================


class SupplierInfo(BaseModel):
    """Supplier info for offer response."""

    id: UUID
    name: str

    class Config:
        from_attributes = True


class SKUInfo(BaseModel):
    """SKU info for offer response."""

    id: UUID
    product_type: str
    variety: str | None
    title: str

    class Config:
        from_attributes = True


class OfferDetail(BaseModel):
    """Offer details for retail response."""

    id: UUID
    supplier: SupplierInfo
    sku: SKUInfo
    length_cm: int | None
    pack_type: str | None
    pack_qty: int | None
    price_type: str
    price_min: Decimal
    price_max: Decimal | None
    currency: str
    tier_min_qty: int | None
    tier_max_qty: int | None
    availability: str
    stock_qty: int | None
    published_at: datetime

    class Config:
        from_attributes = True


class OffersListResponse(BaseModel):
    """Response from list offers endpoint."""

    offers: list[OfferDetail]
    total: int
    limit: int
    offset: int


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/offers", response_model=OffersListResponse)
async def list_offers(
    q: str | None = Query(None, description="Full text search"),
    product_type: str | None = Query(None, description="Filter by product type"),
    length_cm: int | None = Query(None, description="Filter by exact length"),
    length_min: int | None = Query(None, description="Filter by min length"),
    length_max: int | None = Query(None, description="Filter by max length"),
    price_min: Decimal | None = Query(None, description="Filter by min price"),
    price_max: Decimal | None = Query(None, description="Filter by max price"),
    supplier_id: UUID | None = Query(None, description="Filter by supplier"),
    is_active: bool = Query(True, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
) -> OffersListResponse:
    """
    List published offers with filters.

    Filters:
    - q: Full text search (title, variety, product_type)
    - product_type: Exact match
    - length_cm: Exact length
    - length_min/length_max: Length range
    - price_min/price_max: Price range
    - supplier_id: Specific supplier
    - is_active: Active status (default true)

    Returns offers with joined supplier and SKU data.
    Ordered by published_at DESC, price_min ASC.
    """
    log = logger.bind(
        q=q,
        product_type=product_type,
        supplier_id=str(supplier_id) if supplier_id else None,
    )
    log.info("offers.list.start")

    # Build base query with joins
    query = (
        select(Offer)
        .options(
            joinedload(Offer.supplier),
            joinedload(Offer.normalized_sku),
        )
        .where(Offer.is_active == is_active)
    )

    # Apply filters
    if supplier_id:
        query = query.where(Offer.supplier_id == supplier_id)

    if length_cm is not None:
        query = query.where(Offer.length_cm == length_cm)

    if length_min is not None:
        query = query.where(Offer.length_cm >= length_min)

    if length_max is not None:
        query = query.where(Offer.length_cm <= length_max)

    if price_min is not None:
        query = query.where(Offer.price_min >= price_min)

    if price_max is not None:
        query = query.where(Offer.price_min <= price_max)

    # Join with normalized_skus for text search and product_type filter
    if q or product_type:
        query = query.join(NormalizedSKU, NormalizedSKU.id == Offer.normalized_sku_id)

        if product_type:
            query = query.where(NormalizedSKU.product_type == product_type)

        if q:
            # Full text search on title, variety, product_type
            q_lower = q.lower()
            query = query.where(
                or_(
                    func.lower(NormalizedSKU.title).contains(q_lower),
                    func.lower(NormalizedSKU.variety).contains(q_lower),
                    func.lower(NormalizedSKU.product_type).contains(q_lower),
                )
            )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Order and paginate
    query = query.order_by(
        Offer.published_at.desc(),
        Offer.price_min.asc(),
    )
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await db.execute(query)
    offers = result.scalars().all()

    # Build response
    offer_details = []
    for offer in offers:
        offer_details.append(
            OfferDetail(
                id=offer.id,
                supplier=SupplierInfo(
                    id=offer.supplier.id,
                    name=offer.supplier.name,
                ),
                sku=SKUInfo(
                    id=offer.normalized_sku.id,
                    product_type=offer.normalized_sku.product_type,
                    variety=offer.normalized_sku.variety,
                    title=offer.normalized_sku.title,
                ),
                length_cm=offer.length_cm,
                pack_type=offer.pack_type,
                pack_qty=offer.pack_qty,
                price_type=offer.price_type,
                price_min=offer.price_min,
                price_max=offer.price_max,
                currency=offer.currency,
                tier_min_qty=offer.tier_min_qty,
                tier_max_qty=offer.tier_max_qty,
                availability=offer.availability,
                stock_qty=offer.stock_qty,
                published_at=offer.published_at,
            )
        )

    log.info("offers.list.success", total=total, returned=len(offer_details))
    return OffersListResponse(
        offers=offer_details,
        total=total,
        limit=limit,
        offset=offset,
    )
