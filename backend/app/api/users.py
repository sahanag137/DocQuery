"""
users.py

API routes for user profile management, preferences, avatars,
password changes, and account deletion.
"""

from pathlib import Path
from typing import Dict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.auth import _build_user_response, get_current_user
from app.database.connection import get_db
from app.models.user import User
from app.schemas.auth import PasswordChangeRequest
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current user profile and settings.
    """
    return _build_user_response(current_user)


@router.put("/me", response_model=UserResponse)
def update_user_profile(
    update_data: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Update user name, email, or theme/language preferences.
    """
    updated_user = user_service.update_user_profile(db, current_user, update_data)
    return _build_user_response(updated_user)


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Upload and save a new profile picture.
    """
    await user_service.save_user_avatar(db, current_user, file)
    return _build_user_response(current_user)


@router.get("/me/avatar")
def get_avatar(
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """
    Retrieve current user's profile picture.
    """
    avatar_path = user_service.get_user_avatar_path(current_user)
    if not avatar_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have an avatar uploaded.",
        )

    # Determine image media type
    ext = avatar_path.suffix.lower().lstrip(".")
    media_type = f"image/{ext}" if ext != "jpg" else "image/jpeg"

    return FileResponse(
        path=str(avatar_path),
        media_type=media_type,
        filename=avatar_path.name,
    )


@router.put("/me/password")
def change_password(
    data: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Change password for the authenticated user.
    """
    user_service.update_user_password(
        db, current_user, data.current_password, data.new_password
    )
    return {"message": "Password updated successfully."}


@router.delete("/me")
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Permanently delete account and all associated data and files.
    """
    user_service.delete_user_account(db, current_user)
    return {"message": "Account successfully deleted."}
