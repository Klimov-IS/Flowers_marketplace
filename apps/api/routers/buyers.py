"""Buyer endpoints (admin)."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database import get_db
from apps.api.logging_config import get_logger
from apps.api.models import Buyer, City

router = APIRouter(prefix="/admin/buyers", tags=["admin-buyers"])
logger = get_logger(__name__)


# Pydantic schemas
class BuyerCreate(BaseModel):
    """Schema for creating a buyer."""

    name: str
    phone: str
    email: EmailStr | None = None
    address: str | None = None
    city_id: UUID


class BuyerUpdate(BaseModel):
    """Schema for updating a buyer."""

    name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    status: str | None = None  # active, blocked, pending_verification


class BuyerResponse(BaseModel):
    """Schema for buyer response."""

    id: UUID
    name: str
    phone: str
    email: str | None
    address: str | None
    city_id: UUID
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# Endpoints
@router.post("", response_model=BuyerResponse, status_code=201)
async def create_buyer(
    buyer_data: BuyerCreate,
    db: AsyncSession = Depends(get_db),
) -> Buyer:
    """
    Create a new buyer (admin endpoint).

    Args:
        buyer_data: Buyer creation data
        db: Database session

    Returns:
        Created buyer
    """
    # Validate city exists
    result = await db.execute(
        select(City).where(City.id == buyer_data.city_id)
    )
    city = result.scalar_one_or_none()
    if not city:
        raise HTTPException(status_code=404, detail=f"City not found: {buyer_data.city_id}")

    # Check if phone already exists
    result = await db.execute(
        select(Buyer).where(Buyer.phone == buyer_data.phone)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Buyer with phone {buyer_data.phone} already exists"
        )

    buyer = Buyer(
        name=buyer_data.name,
        phone=buyer_data.phone,
        email=buyer_data.email,
        address=buyer_data.address,
        city_id=buyer_data.city_id,
        status="active",  # Default to active
    )
    db.add(buyer)
    await db.commit()
    await db.refresh(buyer)

    logger.info("buyer_created", buyer_id=str(buyer.id), phone=buyer.phone)
    return buyer


@router.get("", response_model=List[BuyerResponse])
async def list_buyers(
    status: str | None = None,
    city_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> List[Buyer]:
    """
    List buyers with optional filters (admin endpoint).

    Args:
        status: Optional status filter
        city_id: Optional city filter
        limit: Max results (default 100)
        offset: Offset for pagination
        db: Database session

    Returns:
        List of buyers
    """
    query = select(Buyer).order_by(Buyer.created_at.desc())

    if status:
        query = query.where(Buyer.status == status)

    if city_id:
        query = query.where(Buyer.city_id == city_id)

    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    buyers = result.scalars().all()
    return list(buyers)


@router.get("/{buyer_id}", response_model=BuyerResponse)
async def get_buyer(
    buyer_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Buyer:
    """
    Get buyer by ID (admin endpoint).

    Args:
        buyer_id: Buyer UUID
        db: Database session

    Returns:
        Buyer details
    """
    result = await db.execute(
        select(Buyer).where(Buyer.id == buyer_id)
    )
    buyer = result.scalar_one_or_none()

    if not buyer:
        raise HTTPException(status_code=404, detail=f"Buyer not found: {buyer_id}")

    return buyer


@router.patch("/{buyer_id}", response_model=BuyerResponse)
async def update_buyer(
    buyer_id: UUID,
    buyer_data: BuyerUpdate,
    db: AsyncSession = Depends(get_db),
) -> Buyer:
    """
    Update buyer (admin endpoint).

    Args:
        buyer_id: Buyer UUID
        buyer_data: Update data
        db: Database session

    Returns:
        Updated buyer
    """
    result = await db.execute(
        select(Buyer).where(Buyer.id == buyer_id)
    )
    buyer = result.scalar_one_or_none()

    if not buyer:
        raise HTTPException(status_code=404, detail=f"Buyer not found: {buyer_id}")

    # Update fields if provided
    if buyer_data.name is not None:
        buyer.name = buyer_data.name
    if buyer_data.phone is not None:
        buyer.phone = buyer_data.phone
    if buyer_data.email is not None:
        buyer.email = buyer_data.email
    if buyer_data.address is not None:
        buyer.address = buyer_data.address
    if buyer_data.status is not None:
        if buyer_data.status not in ["active", "blocked", "pending_verification"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {buyer_data.status}. Must be: active, blocked, pending_verification"
            )
        buyer.status = buyer_data.status

    await db.commit()
    await db.refresh(buyer)

    logger.info("buyer_updated", buyer_id=str(buyer.id))
    return buyer
