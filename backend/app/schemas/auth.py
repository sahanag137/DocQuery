"""
auth.py

Pydantic schemas for authentication and password recovery.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserResponse


class SignUpRequest(BaseModel):
    """Registration request payload."""
    full_name: str = Field(..., min_length=1, max_length=255, description="User full name")
    email: EmailStr = Field(..., description="Unique user email address")
    password: str = Field(..., description="Password (at least 8 chars, 1 letter, 1 number)")


class LoginRequest(BaseModel):
    """Login request payload."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """JWT Token response payload."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    """Forgot password request payload."""
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Forgot password response message."""
    message: str
    reset_token: Optional[str] = None  # Included in development for easy testing


class ResetPasswordRequest(BaseModel):
    """Reset password request payload with token."""
    token: str = Field(..., description="Password reset token received")
    new_password: str = Field(..., description="New secure password")


class PasswordChangeRequest(BaseModel):
    """Change password request for authenticated user."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New secure password")


class LogoutResponse(BaseModel):
    """Logout confirmation response."""
    message: str = "Successfully logged out."
