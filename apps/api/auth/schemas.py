"""Authentication schemas."""
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=6, description="User password")
    role: Literal["buyer", "supplier"] = Field(
        ..., description="Login as buyer or supplier"
    )


class RegisterBuyerRequest(BaseModel):
    """Buyer registration request."""

    name: str = Field(..., min_length=2, max_length=255, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    phone: str = Field(..., min_length=10, max_length=20, description="Phone number")
    password: str = Field(..., min_length=6, max_length=128, description="Password")
    address: str | None = Field(None, description="Delivery address")
    city_id: str = Field(..., description="City UUID")


class RegisterSupplierRequest(BaseModel):
    """Supplier registration request."""

    name: str = Field(..., min_length=2, max_length=255, description="Company name")
    email: EmailStr = Field(..., description="Email address")
    phone: str = Field(..., min_length=10, max_length=20, description="Phone number")
    password: str = Field(..., min_length=6, max_length=128, description="Password")
    city_id: str | None = Field(None, description="City UUID")


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiration in seconds")


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class UserResponse(BaseModel):
    """User info response."""

    id: str
    name: str
    email: str | None
    phone: str | None
    role: Literal["buyer", "supplier"]
    status: str
    city_name: str | None = None


class UpdateProfileRequest(BaseModel):
    """Update user profile request. All fields optional."""

    name: str | None = Field(None, min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, min_length=10, max_length=20)
    city_name: str | None = Field(None, description="City name (will find or create)")


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
