"""
chats.py

API routes for conversation management, message storage, search,
and document-conversation associations.
"""

import json
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
)
from app.schemas.document import DocumentAssociateRequest, DocumentResponse
from app.services import chat_service, document_service
from app.services.document_service import _to_document_response

router = APIRouter(prefix="/chats", tags=["chats"])


def _message_to_response(msg: Message) -> MessageResponse:
    """Helper to convert Message model to MessageResponse schema."""
    parsed_meta = None
    if msg.source_metadata:
        try:
            parsed_meta = json.loads(msg.source_metadata)
        except Exception:
            parsed_meta = msg.source_metadata

    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role,
        content=msg.content,
        source_metadata=parsed_meta,
        created_at=msg.created_at,
    )


def _conversation_to_summary(conv: Conversation) -> ConversationResponse:
    """Helper to convert Conversation model to summary response."""
    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        is_archived=conv.is_archived,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=len(conv.messages) if conv.messages is not None else 0,
    )


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_chat(
    data: Optional[ConversationCreate] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationResponse:
    """
    Start a new conversation thread for the authenticated user.
    """
    conversation = chat_service.create_conversation(
        db, user_id=current_user.id, conversation_in=data
    )
    return _conversation_to_summary(conversation)


@router.get("", response_model=List[ConversationResponse])
def list_chats(
    search: Optional[str] = Query(None, description="Search query across titles and messages"),
    include_archived: bool = Query(False, description="Whether to include archived chats"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ConversationResponse]:
    """
    List conversations for the current user, ordered by most recently active.
    Supports full-text filtering by conversation title or message content.
    """
    conversations = chat_service.get_user_conversations(
        db,
        user_id=current_user.id,
        search=search,
        include_archived=include_archived,
        skip=skip,
        limit=limit,
    )
    return [_conversation_to_summary(c) for c in conversations]


@router.get("/{chat_id}", response_model=ConversationDetailResponse)
def get_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationDetailResponse:
    """
    Retrieve full conversation details, including complete message history
    and attached documents.
    """
    conv = chat_service.get_conversation_by_id(
        db, conversation_id=chat_id, user_id=current_user.id
    )

    messages_resp = [_message_to_response(m) for m in conv.messages]
    docs_resp = [
        _to_document_response(assoc.document)
        for assoc in conv.document_associations
        if assoc.document is not None
    ]

    return ConversationDetailResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        is_archived=conv.is_archived,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=messages_resp,
        documents=docs_resp,
    )


@router.patch("/{chat_id}", response_model=ConversationResponse)
def update_chat(
    chat_id: int,
    data: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationResponse:
    """
    Rename or archive/restore a conversation.
    """
    conv = chat_service.update_conversation(
        db, conversation_id=chat_id, user_id=current_user.id, update_data=data
    )
    return _conversation_to_summary(conv)


@router.delete("/{chat_id}")
def delete_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Delete a conversation and all its messages.
    """
    chat_service.delete_conversation(
        db, conversation_id=chat_id, user_id=current_user.id
    )
    return {"message": "Conversation deleted successfully."}


@router.post("/{chat_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def post_message(
    chat_id: int,
    message_in: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """
    Append a user question or assistant response to the conversation.
    """
    message = chat_service.add_message(
        db, conversation_id=chat_id, user_id=current_user.id, message_in=message_in
    )
    return _message_to_response(message)


@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
def get_messages(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[MessageResponse]:
    """
    Retrieve message history for a specific conversation in chronological order.
    """
    messages = chat_service.get_conversation_messages(
        db, conversation_id=chat_id, user_id=current_user.id
    )
    return [_message_to_response(m) for m in messages]


@router.post("/{chat_id}/documents", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
def associate_document(
    chat_id: int,
    data: DocumentAssociateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Attach an uploaded document to this conversation for context.
    """
    assoc = document_service.associate_document_with_chat(
        db,
        user_id=current_user.id,
        conversation_id=chat_id,
        document_id_or_uuid=data.document_id,
    )
    return {
        "message": "Document successfully associated with conversation.",
        "conversation_id": str(assoc.conversation_id),
        "document_id": str(assoc.document_id),
    }


@router.get("/{chat_id}/documents", response_model=List[DocumentResponse])
def list_chat_documents(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DocumentResponse]:
    """
    List all documents attached to this conversation.
    """
    docs = document_service.get_chat_documents(
        db, user_id=current_user.id, conversation_id=chat_id
    )
    return [_to_document_response(d) for d in docs]


@router.delete("/{chat_id}/documents/{document_id}")
def remove_chat_document(
    chat_id: int,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Remove the association between a document and this conversation.
    """
    document_service.remove_document_from_chat(
        db,
        user_id=current_user.id,
        conversation_id=chat_id,
        document_id_or_uuid=document_id,
    )
    return {"message": "Document association removed successfully."}
