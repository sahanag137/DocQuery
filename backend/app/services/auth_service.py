"""
auth_service.py

Service layer for user registration, authentication, token management,
and secure password recovery workflows.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_reset_token,
    get_password_hash,
    hash_token,
    validate_password_strength,
    verify_password,
)
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.models.user_settings import UserSettings
from app.schemas.auth import SignUpRequest, TokenResponse
from app.schemas.user import UserResponse, UserSettingsResponse


def register_user(db: Session, signup_data: SignUpRequest) -> User:
    """
    Register a new user account.

    Validates password strength, ensures email uniqueness, creates
    the User record and provisions default UserSettings.
    """
    # 1. Validate password strength
    is_valid, msg = validate_password_strength(signup_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    # 2. Check for duplicate email
    email_clean = signup_data.email.lower().strip()
    existing_user = db.execute(select(User).where(User.email == email_clean)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    # 3. Create user
    hashed_pwd = get_password_hash(signup_data.password)
    new_user = User(
        full_name=signup_data.full_name.strip(),
        email=email_clean,
        hashed_password=hashed_pwd,
        is_active=True,
    )
    db.add(new_user)
    db.flush()  # populate new_user.id

    # 4. Provision default settings
    default_settings = UserSettings(
        user_id=new_user.id,
        theme="light",
        language="en",
    )
    db.add(default_settings)
    db.commit()
    db.refresh(new_user)

    return new_user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Authenticate a user by email and password.

    Raises:
        HTTPException 401 if credentials are invalid or user inactive.
    """
    email_clean = email.lower().strip()
    user = db.execute(select(User).where(User.email == email_clean)).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact support.",
        )

    return user


def create_user_tokens(user: User) -> TokenResponse:
    """Generate an access token for an authenticated user."""
    access_token = create_access_token(subject=user.id)
    
    settings_resp = None
    if user.settings:
        settings_resp = UserSettingsResponse(
            id=user.settings.id,
            user_id=user.settings.user_id,
            theme=user.settings.theme,
            language=user.settings.language,
            updated_at=user.settings.updated_at,
        )

    user_resp = UserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        avatar_path=user.avatar_path,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        settings=settings_resp,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_resp,
    )


def request_password_reset(db: Session, email: str) -> Tuple[Optional[str], str]:
    """
    Initiate a password reset flow.
    Generates a secure token, hashes it for database storage,
    and returns (raw_token, message).
    """
    email_clean = email.lower().strip()
    user = db.execute(select(User).where(User.email == email_clean)).scalar_one_or_none()
    generic_msg = "If an account exists with this email, password reset instructions have been generated."

    if not user:
        return None, generic_msg

    raw_token, token_hash = generate_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)

    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        used_at=None,
    )
    db.add(reset_record)
    db.commit()

    return raw_token, generic_msg


def reset_password_with_token(db: Session, token: str, new_password: str) -> None:
    """
    Validate a reset token and set a new password.
    """
    is_valid, msg = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    hashed_input_token = hash_token(token)
    record = db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == hashed_input_token)
    ).scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token.",
        )

    if record.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset token has already been used.",
        )

    # Check expiration
    now = datetime.now(timezone.utc)
    # Ensure record.expires_at is timezone-aware
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset token has expired.",
        )

    # Update user password
    user = db.get(User, record.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated user not found.",
        )

    user.hashed_password = get_password_hash(new_password)
    record.used_at = now
    db.commit()
