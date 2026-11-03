"""
user.py

Pydantic schemas for User profiles and User settings.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserSettingsBase(BaseModel):
    """Base schema for user settings."""
    theme: str = Field(default="light", description="UI theme preference ('light' or 'dark')")
    language: str = Field(default="en", description="UI language preference ('en', 'es', etc.)")


class UserSettingsUpdate(BaseModel):
    """Schema for updating user settings."""
    theme: Optional[str] = None
    language: Optional[str] = None


class UserSettingsResponse(UserSettingsBase):
    """Schema for returning user settings."""
    id: int
    user_id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    """Base schema for user profile data."""
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr


class UserUpdateRequest(BaseModel):
    """Schema for updating profile information."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    theme: Optional[str] = None
    language: Optional[str] = None


class UserResponse(UserBase):
    """Schema for returning user profile details."""
    id: int
    avatar_path: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    settings: Optional[UserSettingsResponse] = None

    model_config = ConfigDict(from_attributes=True)
