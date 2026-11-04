"""
auth.py

API routes for user registration, authentication, token verification,
logout, and password recovery.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.database.connection import get_db
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LogoutResponse,
    ResetPasswordRequest,
    SignUpRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse, UserSettingsResponse
from app.services import auth_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def _build_user_response(user: User) -> UserResponse:
    """Helper to convert User model into UserResponse schema."""
    settings_resp = None
    if user.settings:
        settings_resp = UserSettingsResponse(
            id=user.settings.id,
            user_id=user.settings.user_id,
            theme=user.settings.theme,
            language=user.settings.language,
            updated_at=user.settings.updated_at,
        )

    avatar_url = f"/users/me/avatar" if user.avatar_path else None

    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        avatar_path=user.avatar_path,
        avatar_url=avatar_url,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        settings=settings_resp,
    )


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    bearer_token: Optional[str] = Depends(oauth2_scheme),
    token_query: Optional[str] = Query(None, alias="token"),
) -> User:
    """
    FastAPI dependency to extract and validate the JWT Bearer token.
    Supports Authorization: Bearer header, ?token= query parameter,
    and HttpOnly access_token cookies.
    """
    token = bearer_token or token_query or request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload["sub"]
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User belonging to this token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account.",
        )

    return user


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(
    signup_data: SignUpRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Register a new user account.

    Validates password strength, prevents duplicate emails, and creates
    the user along with default theme/language preferences.
    """
    user = auth_service.register_user(db, signup_data)
    return _build_user_response(user)


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate a user with email and password, return a JWT access token,
    and set a secure HttpOnly session cookie.
    """
    user = auth_service.authenticate_user(db, login_data.email, login_data.password)
    token_resp = auth_service.create_user_tokens(user)
    token_resp.user = _build_user_response(user)

    # Set HttpOnly cookie for secure session support
    response.set_cookie(
        key="access_token",
        value=token_resp.access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,  # Set True in HTTPS production
        path="/",
    )
    return token_resp


@router.post("/logout", response_model=LogoutResponse)
def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
) -> LogoutResponse:
    """
    Log out the current user session and clear authentication cookie.
    """
    response.delete_cookie(key="access_token", path="/")
    return LogoutResponse(message="Successfully logged out.")


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    """
    Generate a password recovery token for the given email address.
    """
    raw_token, message = auth_service.request_password_reset(db, data.email)
    return ForgotPasswordResponse(message=message, reset_token=raw_token)


@router.post("/reset-password", response_model=LogoutResponse)
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> LogoutResponse:
    """
    Reset a user's password using a valid, unexpired reset token.
    """
    auth_service.reset_password_with_token(db, data.token, data.new_password)
    return LogoutResponse(message="Password has been successfully reset. Please log in with your new password.")


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Retrieve profile details for the currently authenticated user.
    """
    return _build_user_response(current_user)
