"""Authentication router."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
    UpdateProfileRequest,
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
    await db.flush()  # Get supplier.id before creating buyer

    # Auto-create buyer profile so supplier can also place orders
    buyer = Buyer(
        id=supplier.id,
        name=request.name,
        email=email,
        phone=request.phone,
        password_hash=supplier.password_hash,
        city_id=city_id,
        status="active",
    )
    db.add(buyer)
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
        result = await db.execute(
            select(Buyer).options(selectinload(Buyer.city)).where(Buyer.id == current_user.id)
        )
        user = result.scalar_one_or_none()
        if user:
            return UserResponse(
                id=str(user.id),
                name=user.name,
                email=user.email,
                phone=user.phone,
                role="buyer",
                status=user.status,
                city_name=user.city.name if user.city else None,
            )
    elif current_user.role == "supplier":
        result = await db.execute(
            select(Supplier).options(selectinload(Supplier.city)).where(Supplier.id == current_user.id)
        )
        user = result.scalar_one_or_none()
        if user:
            contacts = user.contacts or {}
            return UserResponse(
                id=str(user.id),
                name=user.name,
                email=user.email,
                phone=contacts.get("phone"),
                role="supplier",
                status=user.status,
                city_name=user.city.name if user.city else None,
                legal_name=user.legal_name,
                warehouse_address=user.warehouse_address,
                description=user.description,
                min_order_amount=float(user.min_order_amount) if user.min_order_amount else None,
                avatar_url=user.avatar_url,
                contact_person=contacts.get("contact_person"),
                working_hours_from=contacts.get("working_hours_from"),
                working_hours_to=contacts.get("working_hours_to"),
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )


def _build_supplier_response(user) -> UserResponse:
    """Build UserResponse for a supplier."""
    contacts = user.contacts or {}
    return UserResponse(
        id=str(user.id),
        name=user.name,
        email=user.email,
        phone=contacts.get("phone"),
        role="supplier",
        status=user.status,
        city_name=user.city.name if user.city else None,
        legal_name=user.legal_name,
        warehouse_address=user.warehouse_address,
        description=user.description,
        min_order_amount=float(user.min_order_amount) if user.min_order_amount else None,
        avatar_url=user.avatar_url,
        contact_person=contacts.get("contact_person"),
        working_hours_from=contacts.get("working_hours_from"),
        working_hours_to=contacts.get("working_hours_to"),
    )


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile."""
    # Resolve city if provided
    city = None
    if request.city_name:
        result = await db.execute(select(City).where(City.name == request.city_name))
        city = result.scalar_one_or_none()
        if not city:
            # Create city on the fly
            city = City(name=request.city_name)
            db.add(city)
            await db.flush()

    if current_user.role == "buyer":
        result = await db.execute(
            select(Buyer).options(selectinload(Buyer.city)).where(Buyer.id == current_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if request.name is not None:
            user.name = request.name
        if request.email is not None:
            user.email = request.email.lower()
        if request.phone is not None:
            user.phone = request.phone
        if city:
            user.city_id = city.id

        await db.commit()
        await db.refresh(user)
        result = await db.execute(
            select(Buyer).options(selectinload(Buyer.city)).where(Buyer.id == user.id)
        )
        user = result.scalar_one()

        return UserResponse(
            id=str(user.id),
            name=user.name,
            email=user.email,
            phone=user.phone,
            role="buyer",
            status=user.status,
            city_name=user.city.name if user.city else None,
        )

    elif current_user.role == "supplier":
        result = await db.execute(
            select(Supplier).options(selectinload(Supplier.city)).where(Supplier.id == current_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if request.name is not None:
            user.name = request.name
        if request.email is not None:
            user.email = request.email.lower()

        # Update contacts JSONB
        contacts = user.contacts or {}
        if request.phone is not None:
            contacts["phone"] = request.phone
        if request.contact_person is not None:
            contacts["contact_person"] = request.contact_person
        if request.working_hours_from is not None:
            contacts["working_hours_from"] = request.working_hours_from
        if request.working_hours_to is not None:
            contacts["working_hours_to"] = request.working_hours_to
        user.contacts = contacts

        # Update dedicated columns
        if request.legal_name is not None:
            user.legal_name = request.legal_name
        if request.warehouse_address is not None:
            user.warehouse_address = request.warehouse_address
        if request.description is not None:
            user.description = request.description
        if request.min_order_amount is not None:
            from decimal import Decimal
            user.min_order_amount = Decimal(str(request.min_order_amount))
        if city:
            user.city_id = city.id

        # Mark JSONB as modified so SQLAlchemy detects change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(user, "contacts")

        await db.commit()
        await db.refresh(user)
        result = await db.execute(
            select(Supplier).options(selectinload(Supplier.city)).where(Supplier.id == user.id)
        )
        user = result.scalar_one()

        return _build_supplier_response(user)

    raise HTTPException(status_code=400, detail="Invalid role")


@router.post("/me/avatar")
async def upload_avatar(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload avatar image for supplier profile."""
    if current_user.role != "supplier":
        raise HTTPException(status_code=400, detail="Only suppliers can upload avatars")

    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: JPEG, PNG, WebP"
        )

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size: 5MB")

    import os
    import uuid as uuid_module

    upload_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "uploads", "avatars"
    )
    os.makedirs(upload_dir, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{uuid_module.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    avatar_url = f"/uploads/avatars/{filename}"

    result = await db.execute(
        select(Supplier).where(Supplier.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Supplier not found")

    user.avatar_url = avatar_url
    await db.commit()

    logger.info("avatar_uploaded", user_id=str(current_user.id), avatar_url=avatar_url)
    return {"avatar_url": avatar_url}


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
