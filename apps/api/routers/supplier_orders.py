"""Supplier order management endpoints."""
from decimal import Decimal
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database import get_db
from apps.api.logging_config import get_logger
from apps.api.models import Order, Supplier
from apps.api.services.order_service import OrderService

router = APIRouter(prefix="/admin/suppliers/{supplier_id}/orders", tags=["supplier-orders"])
logger = get_logger(__name__)


# Pydantic schemas
class OrderConfirm(BaseModel):
    """Schema for confirming an order."""

    order_id: UUID


class OrderReject(BaseModel):
    """Schema for rejecting an order."""

    order_id: UUID
    reason: str


class OrderActionResponse(BaseModel):
    """Schema for order action response."""

    order_id: UUID
    status: str
    confirmed_at: str | None
    rejected_at: str | None
    rejection_reason: str | None

    class Config:
        from_attributes = True


class OrderMetricsResponse(BaseModel):
    """Schema for order metrics response."""

    total_orders: int
    pending: int
    confirmed: int
    rejected: int
    cancelled: int
    total_revenue: Decimal


# Endpoints
@router.get("", response_model=List[dict])
async def list_supplier_orders(
    supplier_id: UUID,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> List[Order]:
    """
    List orders for supplier (supplier admin endpoint).

    MVP: No authentication - supplier_id from path.

    Args:
        supplier_id: Supplier UUID
        status: Optional status filter
        limit: Max results (default 50)
        offset: Offset for pagination
        db: Database session

    Returns:
        List of orders for supplier
    """
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

    # Convert to dict for response
    response = []
    for order in orders:
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
            "buyer": {
                "id": order.buyer.id,
                "name": order.buyer.name,
                "phone": order.buyer.phone,
            },
            "items_count": len(order.items),
        })

    return response


@router.post("/confirm", response_model=OrderActionResponse)
async def confirm_order(
    supplier_id: UUID,
    action_data: OrderConfirm,
    db: AsyncSession = Depends(get_db),
) -> Order:
    """
    Confirm an order (supplier action).

    Args:
        supplier_id: Supplier UUID
        action_data: Confirmation data
        db: Database session

    Returns:
        Updated order

    Raises:
        HTTPException 400: Order cannot be confirmed (wrong status, wrong supplier)
        HTTPException 404: Order not found
    """
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
) -> Order:
    """
    Reject an order (supplier action).

    Args:
        supplier_id: Supplier UUID
        action_data: Rejection data with reason
        db: Database session

    Returns:
        Updated order

    Raises:
        HTTPException 400: Order cannot be rejected (wrong status, wrong supplier)
        HTTPException 404: Order not found
    """
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


@router.get("/metrics", response_model=OrderMetricsResponse)
async def get_supplier_order_metrics(
    supplier_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> OrderMetricsResponse:
    """
    Get order metrics for supplier (supplier admin endpoint).

    Args:
        supplier_id: Supplier UUID
        db: Database session

    Returns:
        Order statistics

    Raises:
        HTTPException 404: Supplier not found
    """
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
