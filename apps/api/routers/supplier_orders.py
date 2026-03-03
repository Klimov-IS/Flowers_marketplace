"""Supplier order management endpoints."""
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database import get_db
from apps.api.logging_config import get_logger
from apps.api.models import Order, Supplier
from apps.api.services.order_service import OrderService

router = APIRouter(prefix="/suppliers/{supplier_id}/orders", tags=["supplier-orders"])
logger = get_logger(__name__)


# Pydantic schemas
class OrderConfirm(BaseModel):
    """Schema for confirming an order."""

    order_id: UUID


class OrderReject(BaseModel):
    """Schema for rejecting an order."""

    order_id: UUID
    reason: str


class OrderAssemble(BaseModel):
    """Schema for assembling an order."""

    order_id: UUID


class OrderShip(BaseModel):
    """Schema for shipping an order."""

    order_id: UUID


class OrderActionResponse(BaseModel):
    """Schema for order action response."""

    order_id: UUID
    status: str
    confirmed_at: str | None = None
    rejected_at: str | None = None
    rejection_reason: str | None = None
    assembled_at: str | None = None
    shipped_at: str | None = None

    class Config:
        from_attributes = True


class OrderMetricsResponse(BaseModel):
    """Schema for order metrics response."""

    total_orders: int
    pending: int
    confirmed: int
    assembled: int = 0
    shipped: int = 0
    rejected: int
    cancelled: int
    total_revenue: Decimal


# Endpoints
@router.get("", response_model=None)
async def list_supplier_orders(
    supplier_id: UUID,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List orders for supplier."""
    # Validate supplier exists
    result = await db.execute(
        select(Supplier).where(Supplier.id == supplier_id)
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier not found: {supplier_id}")

    # Build query
    query = select(Order).where(Order.supplier_id == supplier_id).order_by(Order.created_at.desc())

    if status:
        query = query.where(Order.status == status)

    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    orders = result.scalars().all()

    # Load relationships
    for order in orders:
        await db.refresh(order, ["items", "buyer"])

    # Convert to dict for response (include items for expandable details)
    response = []
    for order in orders:
        order_items = []
        for item in order.items:
            order_items.append({
                "id": str(item.id),
                "offer_id": str(item.offer_id),
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "total_price": str(item.total_price),
                "notes": item.notes,
            })

        response.append({
            "id": order.id,
            "buyer_id": order.buyer_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "currency": order.currency,
            "delivery_address": order.delivery_address,
            "delivery_date": str(order.delivery_date) if order.delivery_date else None,
            "notes": order.notes,
            "created_at": str(order.created_at),
            "confirmed_at": str(order.confirmed_at) if order.confirmed_at else None,
            "rejected_at": str(order.rejected_at) if order.rejected_at else None,
            "rejection_reason": order.rejection_reason,
            "assembled_at": str(order.assembled_at) if order.assembled_at else None,
            "shipped_at": str(order.shipped_at) if order.shipped_at else None,
            "delivery_type": order.delivery_type,
            "buyer": {
                "id": order.buyer.id,
                "name": order.buyer.name,
                "phone": order.buyer.phone,
            },
            "items": order_items,
            "items_count": len(order.items),
        })

    return response


@router.post("/confirm", response_model=OrderActionResponse)
async def confirm_order(
    supplier_id: UUID,
    action_data: OrderConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Confirm an order (supplier action)."""
    order_service = OrderService(db)

    try:
        order = await order_service.confirm_order(
            order_id=action_data.order_id,
            supplier_id=supplier_id,
        )
        await db.commit()
        await db.refresh(order)

        logger.info(
            "order_confirmed",
            order_id=str(order.id),
            supplier_id=str(supplier_id),
        )
        return order

    except ValueError as e:
        logger.warning("order_confirm_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reject", response_model=OrderActionResponse)
async def reject_order(
    supplier_id: UUID,
    action_data: OrderReject,
    db: AsyncSession = Depends(get_db),
):
    """Reject an order (supplier action)."""
    order_service = OrderService(db)

    try:
        order = await order_service.reject_order(
            order_id=action_data.order_id,
            supplier_id=supplier_id,
            reason=action_data.reason,
        )
        await db.commit()
        await db.refresh(order)

        logger.info(
            "order_rejected",
            order_id=str(order.id),
            supplier_id=str(supplier_id),
            reason=action_data.reason,
        )
        return order

    except ValueError as e:
        logger.warning("order_reject_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assemble", response_model=OrderActionResponse)
async def assemble_order(
    supplier_id: UUID,
    action_data: OrderAssemble,
    db: AsyncSession = Depends(get_db),
):
    """Mark order as assembled/picked (supplier action)."""
    order_service = OrderService(db)

    try:
        order = await order_service.assemble_order(
            order_id=action_data.order_id,
            supplier_id=supplier_id,
        )
        await db.commit()
        await db.refresh(order)

        logger.info(
            "order_assembled",
            order_id=str(order.id),
            supplier_id=str(supplier_id),
        )
        return order

    except ValueError as e:
        logger.warning("order_assemble_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ship", response_model=OrderActionResponse)
async def ship_order(
    supplier_id: UUID,
    action_data: OrderShip,
    db: AsyncSession = Depends(get_db),
):
    """Mark order as shipped (supplier action)."""
    order_service = OrderService(db)

    try:
        order = await order_service.ship_order(
            order_id=action_data.order_id,
            supplier_id=supplier_id,
        )
        await db.commit()
        await db.refresh(order)

        logger.info(
            "order_shipped",
            order_id=str(order.id),
            supplier_id=str(supplier_id),
        )
        return order

    except ValueError as e:
        logger.warning("order_ship_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/metrics", response_model=OrderMetricsResponse)
async def get_supplier_order_metrics(
    supplier_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> OrderMetricsResponse:
    """Get order metrics for supplier."""
    # Validate supplier exists
    result = await db.execute(
        select(Supplier).where(Supplier.id == supplier_id)
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier not found: {supplier_id}")

    order_service = OrderService(db)
    metrics = await order_service.get_order_metrics(supplier_id=supplier_id)

    return OrderMetricsResponse(**metrics)
