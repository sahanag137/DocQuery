"""
DocQuery Service Layer package.
"""

from app.services.auth_service import (
    register_user,
    authenticate_user,
    create_user_tokens,
    request_password_reset,
    reset_password_with_token,
)
from app.services.user_service import (
    get_user_by_id,
    update_user_profile,
    update_user_password,
    save_user_avatar,
    get_user_avatar_path,
    delete_user_account,
)
from app.services.document_service import (
    save_uploaded_document,
    get_user_documents,
    get_document_by_id_or_uuid,
    delete_document,
    associate_document_with_chat,
    get_chat_documents,
    remove_document_from_chat,
)
from app.services.chat_service import (
    create_conversation,
    get_user_conversations,
    get_conversation_by_id,
    update_conversation,
    delete_conversation,
    add_message,
    get_conversation_messages,
)
from app.services.pdf_export_service import export_conversation_to_pdf

__all__ = [
    "register_user",
    "authenticate_user",
    "create_user_tokens",
    "request_password_reset",
    "reset_password_with_token",
    "get_user_by_id",
    "update_user_profile",
    "update_user_password",
    "save_user_avatar",
    "get_user_avatar_path",
    "delete_user_account",
    "save_uploaded_document",
    "get_user_documents",
    "get_document_by_id_or_uuid",
    "delete_document",
    "associate_document_with_chat",
    "get_chat_documents",
    "remove_document_from_chat",
    "create_conversation",
    "get_user_conversations",
    "get_conversation_by_id",
    "update_conversation",
    "delete_conversation",
    "add_message",
    "get_conversation_messages",
    "export_conversation_to_pdf",
]
