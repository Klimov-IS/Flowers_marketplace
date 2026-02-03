"""FastAPI authentication dependencies."""
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.jwt import verify_token
from apps.api.database import get_db
from apps.api.models import Buyer, Supplier

# HTTP Bearer scheme
security = HTTPBearer(auto_error=False)


class CurrentUser:
    """Current authenticated user."""

    def __init__(self, id: UUID, role: str, name: str):
        self.id = id
        self.role = role
        self.name = name


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """
    Get the current authenticated user from JWT token.

    Raises:
        HTTPException: If token is invalid or user not found
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user based on role
    try:
        uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    if role == "buyer":
        result = await db.execute(select(Buyer).where(Buyer.id == uuid))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Buyer not found",
            )
        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Buyer account is not active",
            )
        return CurrentUser(id=user.id, role="buyer", name=user.name)

    elif role == "supplier":
        result = await db.execute(select(Supplier).where(Supplier.id == uuid))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Supplier not found",
            )
        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Supplier account is not active",
            )
        return CurrentUser(id=user.id, role="supplier", name=user.name)

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid role in token",
        )


async def get_current_buyer(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Get current user and verify it's a buyer."""
    if current_user.role != "buyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Buyer access required",
        )
    return current_user


async def get_current_supplier(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Get current user and verify it's a supplier."""
    if current_user.role != "supplier":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supplier access required",
        )
    return current_user


# Optional authentication (returns None if not authenticated)
async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: AsyncSession = Depends(get_db),
) -> CurrentUser | None:
    """
    Get current user if authenticated, None otherwise.
    Does not raise exceptions for missing/invalid tokens.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = verify_token(token)

    if payload is None or payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id or not role:
        return None

    try:
        uuid = UUID(user_id)
    except ValueError:
        return None

    if role == "buyer":
        result = await db.execute(select(Buyer).where(Buyer.id == uuid))
        user = result.scalar_one_or_none()
        if user and user.status == "active":
            return CurrentUser(id=user.id, role="buyer", name=user.name)

    elif role == "supplier":
        result = await db.execute(select(Supplier).where(Supplier.id == uuid))
        user = result.scalar_one_or_none()
        if user and user.status == "active":
            return CurrentUser(id=user.id, role="supplier", name=user.name)

    return None
