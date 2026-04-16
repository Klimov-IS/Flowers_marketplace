"""Products endpoints (public catalog for buyers)."""
import structlog
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.api.database import get_db
from apps.api.models.product import Product
from apps.api.models.parties import Supplier

logger = structlog.get_logger()
router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================


class ProductSupplierInfo(BaseModel):
    id: UUID
    name: str
    warehouse_address: str | None = None

    class Config:
        from_attributes = True


class ProductDetail(BaseModel):
    id: UUID
    supplier: ProductSupplierInfo
    title: str
    flower_type: str | None = None
    variety: str | None = None
    length_cm: int | None = None
    color: str | None = None
    origin_country: str | None = None
    pack_type: str | None = None
    pack_qty: int | None = None
    photo_url: str | None = None
    price: Decimal
    currency: str
    stock_qty: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProductsListResponse(BaseModel):
    products: list[ProductDetail]
    total: int
    limit: int
    offset: int


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/products", response_model=ProductsListResponse)
async def list_products(
    q: str | None = Query(None, description="Full text search"),
    flower_type: str | None = Query(None, description="Filter by flower type"),
    variety: str | None = Query(None, description="Filter by variety"),
    length_min: int | None = Query(None, description="Filter by min length"),
    length_max: int | None = Query(None, description="Filter by max length"),
    price_min: Decimal | None = Query(None, description="Filter by min price"),
    price_max: Decimal | None = Query(None, description="Filter by max price"),
    supplier_id: UUID | None = Query(None, description="Filter by supplier"),
    color: str | None = Query(None, description="Filter by color"),
    in_stock: bool | None = Query(None, description="Filter by in stock (stock_qty > 0)"),
    sort_by: str | None = Query(None, description="Sort: price_asc, price_desc, newest"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
) -> ProductsListResponse:
    """List active products in the catalog."""
    log = logger.bind(q=q, flower_type=flower_type)
    log.info("products.list.start")

    query = (
        select(Product)
        .options(joinedload(Product.supplier))
        .where(Product.is_active == True, Product.status == "active")
    )

    if supplier_id:
        query = query.where(Product.supplier_id == supplier_id)

    if flower_type:
        query = query.where(func.lower(Product.flower_type) == flower_type.lower())

    if variety:
        query = query.where(func.lower(Product.variety).contains(variety.lower()))

    if length_min is not None:
        query = query.where(Product.length_cm >= length_min)

    if length_max is not None:
        query = query.where(Product.length_cm <= length_max)

    if price_min is not None:
        query = query.where(Product.price >= price_min)

    if price_max is not None:
        query = query.where(Product.price <= price_max)

    if color:
        query = query.where(func.lower(Product.color).contains(color.lower()))

    if in_stock is True:
        query = query.where(Product.stock_qty > 0)

    if q:
        q_lower = q.lower()
        query = query.where(
            or_(
                func.lower(Product.title).contains(q_lower),
                func.lower(Product.flower_type).contains(q_lower),
                func.lower(Product.variety).contains(q_lower),
            )
        )

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Sort
    if sort_by == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort_by == "newest":
        query = query.order_by(Product.created_at.desc())
    else:
        query = query.order_by(Product.created_at.desc(), Product.price.asc())

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    products = result.scalars().all()

    product_details = [
        ProductDetail(
            id=p.id,
            supplier=ProductSupplierInfo(
                id=p.supplier.id,
                name=p.supplier.name,
                warehouse_address=p.supplier.warehouse_address,
            ),
            title=p.title,
            flower_type=p.flower_type,
            variety=p.variety,
            length_cm=p.length_cm,
            color=p.color,
            origin_country=p.origin_country,
            pack_type=p.pack_type,
            pack_qty=p.pack_qty,
            photo_url=p.photo_url,
            price=p.price,
            currency=p.currency,
            stock_qty=p.stock_qty,
            created_at=p.created_at,
        )
        for p in products
    ]

    log.info("products.list.success", total=total, returned=len(product_details))
    return ProductsListResponse(
        products=product_details,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/products/flower-types")
async def list_flower_types(
    db: AsyncSession = Depends(get_db),
):
    """Get distinct flower types for catalog navigation."""
    result = await db.execute(
        select(Product.flower_type, func.count(Product.id))
        .where(Product.is_active == True, Product.status == "active", Product.flower_type.isnot(None))
        .group_by(Product.flower_type)
        .order_by(func.count(Product.id).desc())
    )
    return [{"flower_type": row[0], "count": row[1]} for row in result.all()]


@router.get("/products/varieties")
async def list_varieties(
    flower_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get distinct varieties, optionally filtered by flower type."""
    query = (
        select(Product.variety, func.count(Product.id))
        .where(Product.is_active == True, Product.status == "active", Product.variety.isnot(None))
    )
    if flower_type:
        query = query.where(func.lower(Product.flower_type) == flower_type.lower())
    query = query.group_by(Product.variety).order_by(func.count(Product.id).desc())
    result = await db.execute(query)
    return [{"variety": row[0], "count": row[1]} for row in result.all()]
