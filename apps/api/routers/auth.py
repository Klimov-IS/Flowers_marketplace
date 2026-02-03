"""Authentication router."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.dependencies import CurrentUser, get_current_user
from apps.api.auth.jwt import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from apps.api.auth.password import hash_password, verify_password
from apps.api.auth.schemas import (
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterBuyerRequest,
    RegisterSupplierRequest,
    TokenResponse,
    UserResponse,
)
from apps.api.database import get_db
from apps.api.logging_config import get_logger
from apps.api.models import Buyer, City, Supplier

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return tokens.

    Supports both buyer and supplier login with email/password.
    """
    email = request.email.lower()

    if request.role == "buyer":
        result = await db.execute(select(Buyer).where(Buyer.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password not set. Please contact support.",
            )

        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not active",
            )

        user_id = user.id
        role = "buyer"

    elif request.role == "supplier":
        result = await db.execute(select(Supplier).where(Supplier.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password not set. Please contact support.",
            )

        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not active",
            )

        user_id = user.id
        role = "supplier"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role",
        )

    logger.info("user_logged_in", user_id=str(user_id), role=role)

    access_token = create_access_token(user_id, role)
    refresh_token = create_refresh_token(user_id, role)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/register/buyer", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_buyer(
    request: RegisterBuyerRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new buyer account."""
    email = request.email.lower()

    # Check if email already exists
    result = await db.execute(select(Buyer).where(Buyer.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Verify city exists
    try:
        city_id = UUID(request.city_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid city_id format",
        )

    result = await db.execute(select(City).where(City.id == city_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="City not found",
        )

    # Create buyer
    buyer = Buyer(
        name=request.name,
        email=email,
        phone=request.phone,
        password_hash=hash_password(request.password),
        address=request.address,
        city_id=city_id,
        status="active",
    )
    db.add(buyer)
    await db.commit()
    await db.refresh(buyer)

    logger.info("buyer_registered", buyer_id=str(buyer.id), email=email)

    access_token = create_access_token(buyer.id, "buyer")
    refresh_token = create_refresh_token(buyer.id, "buyer")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/register/supplier", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_supplier(
    request: RegisterSupplierRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new supplier account."""
    email = request.email.lower()

    # Check if email already exists
    result = await db.execute(select(Supplier).where(Supplier.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if company name already exists
    result = await db.execute(select(Supplier).where(Supplier.name == request.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company name already registered",
        )

    # Verify city if provided
    city_id = None
    if request.city_id:
        try:
            city_id = UUID(request.city_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid city_id format",
            )

        result = await db.execute(select(City).where(City.id == city_id))
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="City not found",
            )

    # Create supplier (pending status, needs admin approval for production)
    supplier = Supplier(
        name=request.name,
        email=email,
        password_hash=hash_password(request.password),
        city_id=city_id,
        contacts={"phone": request.phone, "email": email},
        status="active",  # For MVP, auto-activate. In production: "pending"
    )
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)

    logger.info("supplier_registered", supplier_id=str(supplier.id), email=email)

    access_token = create_access_token(supplier.id, "supplier")
    refresh_token = create_refresh_token(supplier.id, "supplier")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Get new access token using refresh token."""
    payload = verify_token(request.refresh_token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Verify user still exists and is active
    try:
        uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID",
        )

    if role == "buyer":
        result = await db.execute(select(Buyer).where(Buyer.id == uuid))
        user = result.scalar_one_or_none()
        if not user or user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or not active",
            )
    elif role == "supplier":
        result = await db.execute(select(Supplier).where(Supplier.id == uuid))
        user = result.scalar_one_or_none()
        if not user or user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or not active",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid role",
        )

    access_token = create_access_token(uuid, role)
    refresh_token = create_refresh_token(uuid, role)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user info."""
    if current_user.role == "buyer":
        result = await db.execute(select(Buyer).where(Buyer.id == current_user.id))
        user = result.scalar_one_or_none()
        if user:
            return UserResponse(
                id=str(user.id),
                name=user.name,
                email=user.email,
                phone=user.phone,
                role="buyer",
                status=user.status,
            )
    elif current_user.role == "supplier":
        result = await db.execute(select(Supplier).where(Supplier.id == current_user.id))
        user = result.scalar_one_or_none()
        if user:
            return UserResponse(
                id=str(user.id),
                name=user.name,
                email=user.email,
                phone=user.contacts.get("phone") if user.contacts else None,
                role="supplier",
                status=user.status,
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """
    Logout current user.

    Note: JWT tokens are stateless, so we can't truly invalidate them.
    Client should delete tokens from storage.
    For production, implement token blacklist in Redis.
    """
    logger.info("user_logged_out", user_id=str(current_user.id), role=current_user.role)
    return MessageResponse(message="Successfully logged out")
