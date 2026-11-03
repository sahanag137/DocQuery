"""
user_service.py

Service layer for user profiles, avatar uploads, password changes,
preferences, and account deletion.
"""

from pathlib import Path
import shutil
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash, validate_password_strength, verify_password
from app.models.document import Document
from app.models.user import User
from app.models.user_settings import UserSettings
from app.schemas.user import UserUpdateRequest
from app.utils.file_handler import delete_file_if_exists, generate_unique_filename, validate_file_extension


def get_user_by_id(db: Session, user_id: int) -> User:
    """Fetch user by primary key ID or raise 404."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user


def update_user_profile(db: Session, user: User, update_data: UserUpdateRequest) -> User:
    """
    Update user name, email, and preferences (theme, language).
    """
    # 1. Update email if requested and check uniqueness
    if update_data.email and update_data.email.lower().strip() != user.email:
        new_email = update_data.email.lower().strip()
        existing = db.execute(
            select(User).where(User.email == new_email, User.id != user.id)
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email address is already in use by another account.",
            )
        user.email = new_email

    # 2. Update full name if requested
    if update_data.full_name is not None:
        user.full_name = update_data.full_name.strip()

    # 3. Update settings if requested
    if update_data.theme is not None or update_data.language is not None:
        if not user.settings:
            user.settings = UserSettings(user_id=user.id, theme="light", language="en")
            db.add(user.settings)
        if update_data.theme is not None:
            user.settings.theme = update_data.theme.strip()
        if update_data.language is not None:
            user.settings.language = update_data.language.strip()

    db.commit()
    db.refresh(user)
    return user


def update_user_password(
    db: Session, user: User, current_password: str, new_password: str
) -> None:
    """Change the password for an authenticated user."""
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    is_valid, msg = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    user.hashed_password = get_password_hash(new_password)
    db.commit()


async def save_user_avatar(db: Session, user: User, file: UploadFile) -> str:
    """
    Validate, save a profile picture, and link it to the user.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided for avatar upload.",
        )

    # 1. Validate extension
    validate_file_extension(file.filename, settings.ALLOWED_AVATAR_EXTENSIONS)

    # 2. Check file size during streaming
    settings.AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    _, stored_filename = generate_unique_filename(file.filename)
    dest_path = settings.AVATARS_DIR / stored_filename

    total_bytes = 0
    try:
        with dest_path.open("wb") as buffer:
            while chunk := await file.read(64 * 1024):
                total_bytes += len(chunk)
                if total_bytes > settings.max_avatar_size_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Avatar file exceeds maximum size limit of {settings.MAX_AVATAR_SIZE_MB}MB.",
                    )
                buffer.write(chunk)
    except Exception:
        delete_file_if_exists(dest_path)
        raise
    finally:
        await file.close()

    # 3. Clean up old avatar if exists
    if user.avatar_path:
        old_avatar = Path(user.avatar_path)
        delete_file_if_exists(old_avatar)

    # 4. Save path to database
    user.avatar_path = str(dest_path)
    db.commit()
    db.refresh(user)

    return str(dest_path)


def get_user_avatar_path(user: User) -> Optional[Path]:
    """Retrieve Path to the user's avatar image, or None if not set / missing."""
    if not user.avatar_path:
        return None
    path = Path(user.avatar_path)
    if path.is_file():
        return path
    return None


def delete_user_account(db: Session, user: User) -> None:
    """
    Completely delete a user account and associated physical files.
    """
    # 1. Delete avatar file
    if user.avatar_path:
        delete_file_if_exists(user.avatar_path)

    # 2. Delete all physical documents owned by user
    user_docs = db.execute(select(Document).where(Document.user_id == user.id)).scalars().all()
    for doc in user_docs:
        if doc.file_path:
            delete_file_if_exists(doc.file_path)

    # 3. Delete user from database (cascades settings, conversations, messages, doc records)
    db.delete(user)
    db.commit()
