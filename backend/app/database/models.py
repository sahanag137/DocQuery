"""
models.py

Backwards-compatibility shim re-exporting ORM models.
"""

from app.models.document import Document
from app.models.question import Question
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.conversation_document import ConversationDocument
from app.models.password_reset_token import PasswordResetToken

__all__ = [
    "Document",
    "Question",
    "User",
    "UserSettings",
    "Conversation",
    "Message",
    "ConversationDocument",
    "PasswordResetToken",
]
