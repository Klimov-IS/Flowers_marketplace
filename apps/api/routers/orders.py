"""Order endpoints (retail - buyer side)."""
from datetime import date
from decimal import Decimal
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database import get_db
from apps.api.logging_config import get_logger
from apps.api.models import Order, OrderItem
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

    buyer_id: UUID  # MVP: No auth, pass buyer_id explicitly
    items: List[OrderItemCreate]
    delivery_address: str | None = None
    delivery_date: date | None = None
    notes: str | None = None


class OrderItemResponse(BaseModel):
    """Schema for order item response."""

    id: UUID
    offer_id: UUID
    normalized_sku_id: UUID
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
    delivery_address: str | None
    delivery_date: date | None
    notes: str | None
    created_at: str
    confirmed_at: str | None
    rejected_at: str | None
    rejection_reason: str | None
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


# Endpoints
@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
) -> Order:
    """
    Create a new order (retail endpoint).

    MVP: No authentication - buyer_id passed in request body.

    Args:
        order_data: Order creation data
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
            buyer_id=order_data.buyer_id,
            items=items_data,
            delivery_address=order_data.delivery_address,
            delivery_date=str(order_data.delivery_date) if order_data.delivery_date else None,
            notes=order_data.notes,
        )

        await db.commit()
        await db.refresh(order, ["items", "buyer", "supplier"])

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
    buyer_id: UUID | None = None,
    supplier_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    """
    List orders with filters (retail endpoint).

    MVP: No authentication - filter by buyer_id for buyer's orders.

    Args:
        buyer_id: Optional filter by buyer
        supplier_id: Optional filter by supplier
        status: Optional filter by status
        limit: Max results (default 50)
        offset: Offset for pagination
        db: Database session

    Returns:
        Paginated list of orders
    """
    query = select(Order).order_by(Order.created_at.desc())

    if buyer_id:
        query = query.where(Order.buyer_id == buyer_id)

    if supplier_id:
        query = query.where(Order.supplier_id == supplier_id)

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

    return OrderListResponse(
        total=total,
        limit=limit,
        offset=offset,
        orders=list(orders),
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Order:
    """
    Get order details by ID (retail endpoint).

    Args:
        order_id: Order UUID
        db: Database session

    Returns:
        Order details with items

    Raises:
        HTTPException 404: Order not found
    """
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")

    # Load relationships
    await db.refresh(order, ["items", "buyer", "supplier"])

    return order
