"""JWT token utilities."""
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from apps.api.config import settings

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(
    subject: str | UUID,
    role: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: User ID (buyer_id or supplier_id)
        role: User role ("buyer" or "supplier")
        expires_delta: Custom expiration time
        extra_claims: Additional claims to include

    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(subject),
        "role": role,
        "exp": expire,
        "type": "access",
    }

    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(
    subject: str | UUID,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT refresh token.

    Args:
        subject: User ID (buyer_id or supplier_id)
        role: User role ("buyer" or "supplier")
        expires_delta: Custom expiration time

    Returns:
        Encoded JWT refresh token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(subject),
        "role": role,
        "exp": expire,
        "type": "refresh",
    }

    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def verify_token(token: str) -> dict[str, Any] | None:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
