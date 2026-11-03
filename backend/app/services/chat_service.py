"""
chat_service.py

Service layer for managing conversations, message history, searching chats,
and handling conversation lifecycle (archiving, renaming, deleting).
"""

import json
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import distinct, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.conversation import Conversation
from app.models.conversation_document import ConversationDocument
from app.models.document import Document
from app.models.message import Message
from app.schemas.chat import ConversationCreate, ConversationUpdate, MessageCreate


def create_conversation(
    db: Session,
    user_id: int,
    conversation_in: Optional[ConversationCreate] = None,
) -> Conversation:
    """Create a new conversation session for an authenticated user."""
    title = conversation_in.title.strip() if conversation_in and conversation_in.title else "New Chat"
    conversation = Conversation(
        user_id=user_id,
        title=title,
        is_archived=False,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_user_conversations(
    db: Session,
    user_id: int,
    search: Optional[str] = None,
    include_archived: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> List[Conversation]:
    """
    Retrieve conversations for a user.
    Supports text search across conversation titles and message content.
    """
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .options(selectinload(Conversation.messages))
    )

    if not include_archived:
        stmt = stmt.where(Conversation.is_archived.is_(False))

    if search and search.strip():
        term = f"%{search.strip()}%"
        # Search in title or within any associated message contents
        stmt = stmt.outerjoin(Message, Message.conversation_id == Conversation.id).where(
            or_(
                Conversation.title.ilike(term),
                Message.content.ilike(term),
            )
        ).distinct()

    stmt = stmt.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_conversation_by_id(
    db: Session,
    conversation_id: int,
    user_id: int,
) -> Conversation:
    """Fetch conversation ensuring ownership."""
    conversation = (
        db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(
                selectinload(Conversation.messages),
                selectinload(Conversation.document_associations).selectinload(
                    ConversationDocument.document
                ),
            )
        )
        .scalar_one_or_none()
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )

    if conversation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this conversation.",
        )

    return conversation


def update_conversation(
    db: Session,
    conversation_id: int,
    user_id: int,
    update_data: ConversationUpdate,
) -> Conversation:
    """Update title or archive status of a conversation."""
    conversation = get_conversation_by_id(db, conversation_id, user_id=user_id)

    if update_data.title is not None:
        new_title = update_data.title.strip()
        if new_title:
            conversation.title = new_title

    if update_data.is_archived is not None:
        conversation.is_archived = update_data.is_archived

    db.commit()
    db.refresh(conversation)
    return conversation


def delete_conversation(
    db: Session,
    conversation_id: int,
    user_id: int,
) -> None:
    """Delete a conversation and all its associated messages."""
    conversation = get_conversation_by_id(db, conversation_id, user_id=user_id)
    db.delete(conversation)
    db.commit()


def add_message(
    db: Session,
    conversation_id: int,
    user_id: int,
    message_in: MessageCreate,
) -> Message:
    """
    Save a message (user or assistant) to the conversation.
    Updates the conversation updated_at timestamp.
    If the conversation is named 'New Chat' and the message is from 'user',
    auto-names the conversation based on the initial question snippet.
    """
    conversation = get_conversation_by_id(db, conversation_id, user_id=user_id)

    # Serialize source_metadata if provided as dict or list
    serialized_meta = None
    if message_in.source_metadata is not None:
        if isinstance(message_in.source_metadata, (dict, list)):
            serialized_meta = json.dumps(message_in.source_metadata)
        else:
            serialized_meta = str(message_in.source_metadata)

    message = Message(
        conversation_id=conversation.id,
        role=message_in.role.strip().lower(),
        content=message_in.content.strip(),
        source_metadata=serialized_meta,
    )
    db.add(message)

    # Auto-generate a title if conversation is brand new and user asks a question
    if conversation.title == "New Chat" and message.role == "user":
        content_snippet = message.content.strip()
        if len(content_snippet) > 40:
            content_snippet = content_snippet[:37] + "..."
        conversation.title = content_snippet

    db.commit()
    db.refresh(message)
    return message


def get_conversation_messages(
    db: Session,
    conversation_id: int,
    user_id: int,
) -> List[Message]:
    """Retrieve all messages in chronological order for a conversation."""
    # Ensure ownership
    get_conversation_by_id(db, conversation_id, user_id=user_id)

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())
