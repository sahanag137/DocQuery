"""
DocQuery Pydantic Schemas.
"""

from app.schemas.auth import (
    SignUpRequest,
    LoginRequest,
    TokenResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    PasswordChangeRequest,
    LogoutResponse,
)
from app.schemas.user import (
    UserBase,
    UserUpdateRequest,
    UserResponse,
    UserSettingsBase,
    UserSettingsUpdate,
    UserSettingsResponse,
)
from app.schemas.document import (
    DocumentResponse,
    DocumentUploadResponse,
    DocumentAssociateRequest,
)
from app.schemas.chat import (
    MessageCreate,
    MessageResponse,
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationDetailResponse,
)

__all__ = [
    "SignUpRequest",
    "LoginRequest",
    "TokenResponse",
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "ResetPasswordRequest",
    "PasswordChangeRequest",
    "LogoutResponse",
    "UserBase",
    "UserUpdateRequest",
    "UserResponse",
    "UserSettingsBase",
    "UserSettingsUpdate",
    "UserSettingsResponse",
    "DocumentResponse",
    "DocumentUploadResponse",
    "DocumentAssociateRequest",
    "MessageCreate",
    "MessageResponse",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationResponse",
    "ConversationDetailResponse",
]
