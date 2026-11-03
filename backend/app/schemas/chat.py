"""
chat.py

Pydantic schemas for Conversations and Messages.
"""

from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.document import DocumentResponse


class MessageCreate(BaseModel):
    """Payload to add a new message to a conversation."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., min_length=1, description="Text body of the message")
    source_metadata: Optional[Any] = Field(
        default=None, description="Optional citation or retrieval metadata"
    )


class MessageResponse(BaseModel):
    """Schema for returning message records."""
    id: int
    conversation_id: int
    role: str
    content: str
    source_metadata: Optional[Any] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
    """Payload to start a new conversation."""
    title: Optional[str] = Field(default="New Chat", max_length=255)


class ConversationUpdate(BaseModel):
    """Payload to update/rename/archive a conversation."""
    title: Optional[str] = Field(None, max_length=255)
    is_archived: Optional[bool] = None


class ConversationResponse(BaseModel):
    """Summary schema for conversation items in sidebar/list."""
    id: int
    user_id: int
    title: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(BaseModel):
    """Full conversation schema including messages and attached documents."""
    id: int
    user_id: int
    title: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []
    documents: List[DocumentResponse] = []

    model_config = ConfigDict(from_attributes=True)
