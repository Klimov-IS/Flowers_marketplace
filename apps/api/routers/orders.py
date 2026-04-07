"""Order endpoints (retail - buyer side)."""
from datetime import date, datetime
from decimal import Decimal
from typing import List
from uuid import UUID

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.dependencies import CurrentUser, get_current_buyer
from apps.api.database import get_db
from apps.api.logging_config import get_logger
from apps.api.models import Offer, Order, OrderItem
from apps.api.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])
logger = get_logger(__name__)


# Pydantic schemas
class OrderItemCreate(BaseModel):
    """Schema for order item in create request."""

    offer_id: UUID
    quantity: int
    notes: str | None = None


class OrderCreate(BaseModel):
    """Schema for creating an order."""

    items: List[OrderItemCreate]
    delivery_type: str | None = None  # 'pickup' or 'delivery'
    delivery_address: str | None = None
    delivery_date: date | None = None
    notes: str | None = None

    @field_validator("delivery_date", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v


class OrderItemResponse(BaseModel):
    """Schema for order item response."""

    id: UUID
    offer_id: UUID
    normalized_sku_id: UUID
    product_name: str | None = None
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    notes: str | None

    class Config:
        from_attributes = True


class SupplierBrief(BaseModel):
    """Brief supplier info for order response."""

    id: UUID
    name: str

    class Config:
        from_attributes = True


class BuyerBrief(BaseModel):
    """Brief buyer info for order response."""

    id: UUID
    name: str
    phone: str

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Schema for order response."""

    id: UUID
    buyer_id: UUID
    supplier_id: UUID
    status: str
    total_amount: Decimal
    currency: str
    delivery_type: str | None = None
    delivery_address: str | None
    delivery_date: date | None
    notes: str | None
    created_at: datetime
    confirmed_at: datetime | None
    rejected_at: datetime | None
    rejection_reason: str | None
    assembled_at: datetime | None = None
    shipped_at: datetime | None = None
    items: List[OrderItemResponse]
    buyer: BuyerBrief
    supplier: SupplierBrief

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Schema for orders list response."""

    total: int
    limit: int
    offset: int
    orders: List[OrderResponse]


async def _enrich_order_items(db: AsyncSession, order: Order) -> None:
    """Load offer relationship for each item and set product_name."""
    for item in order.items:
        await db.refresh(item, ["offer"])
        item.product_name = item.offer.display_title if item.offer and item.offer.display_title else None


# Endpoints
@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    order_data: OrderCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_buyer)],
    db: AsyncSession = Depends(get_db),
) -> Order:
    """
    Create a new order (retail endpoint).

    Requires authenticated buyer. buyer_id taken from JWT token.

    Args:
        order_data: Order creation data
        current_user: Authenticated buyer from JWT
        db: Database session

    Returns:
        Created order with items

    Raises:
        HTTPException 400: Validation failed (inactive buyer/offers, multiple suppliers, etc.)
        HTTPException 404: Buyer or offers not found
    """
    order_service = OrderService(db)

    try:
        # Convert Pydantic models to dicts
        items_data = [item.model_dump() for item in order_data.items]

        order = await order_service.create_order(
            buyer_id=current_user.id,
            items=items_data,
            delivery_address=order_data.delivery_address,
            delivery_date=order_data.delivery_date,
            delivery_type=order_data.delivery_type,
            notes=order_data.notes,
        )

        await db.commit()
        await db.refresh(order, ["items", "buyer", "supplier"])
        await _enrich_order_items(db, order)

        logger.info(
            "order_created",
            order_id=str(order.id),
            buyer_id=str(order.buyer_id),
            supplier_id=str(order.supplier_id),
            total_amount=str(order.total_amount),
        )
        return order

    except ValueError as e:
        logger.warning("order_creation_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=OrderListResponse)
async def list_orders(
    current_user: Annotated[CurrentUser, Depends(get_current_buyer)],
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    """
    List orders for authenticated buyer.

    Returns only the current buyer's orders.

    Args:
        current_user: Authenticated buyer from JWT
        status: Optional filter by status
        limit: Max results (default 50)
        offset: Offset for pagination
        db: Database session

    Returns:
        Paginated list of orders
    """
    query = select(Order).order_by(Order.created_at.desc())

    # Always filter by authenticated buyer
    query = query.where(Order.buyer_id == current_user.id)

    if status:
        query = query.where(Order.status == status)

    # Count total
    from sqlalchemy import func, select as sa_select
    count_query = sa_select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Fetch paginated
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    orders = result.scalars().all()

    # Load relationships
    for order in orders:
        await db.refresh(order, ["items", "buyer", "supplier"])
        await _enrich_order_items(db, order)

    return OrderListResponse(
        total=total,
        limit=limit,
        offset=offset,
        orders=list(orders),
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_buyer)],
    db: AsyncSession = Depends(get_db),
) -> Order:
    """
    Get order details by ID (retail endpoint).

    Requires authenticated buyer; returns only own orders.

    Args:
        order_id: Order UUID
        current_user: Authenticated buyer from JWT
        db: Database session

    Returns:
        Order details with items

    Raises:
        HTTPException 404: Order not found
    """
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.buyer_id == current_user.id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")

    # Load relationships
    await db.refresh(order, ["items", "buyer", "supplier"])
    await _enrich_order_items(db, order)

    return order


# ── Cart validation ──


class ValidateCartRequest(BaseModel):
    """Schema for cart validation."""

    offer_ids: List[UUID]


class ValidateCartResponse(BaseModel):
    """Schema for cart validation response."""

    valid: List[UUID]
    invalid: List[UUID]


@router.post("/validate-cart", response_model=ValidateCartResponse)
async def validate_cart(
    data: ValidateCartRequest,
    db: AsyncSession = Depends(get_db),
):
    """Check which offer_ids are still active."""
    if not data.offer_ids:
        return ValidateCartResponse(valid=[], invalid=[])

    result = await db.execute(
        select(Offer.id).where(
            Offer.id.in_(data.offer_ids),
            Offer.is_active == True,
        )
    )
    active_ids = {row[0] for row in result.all()}

    valid = [oid for oid in data.offer_ids if oid in active_ids]
    invalid = [oid for oid in data.offer_ids if oid not in active_ids]

    return ValidateCartResponse(valid=valid, invalid=invalid)
