"""
conversation.py

SQLAlchemy model for conversations / chat sessions.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.message import Message
    from app.models.conversation_document import ConversationDocument


class Conversation(Base):
    """Chat session / conversation thread."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), default="New Chat", nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, index=True, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    document_associations: Mapped[List["ConversationDocument"]] = relationship(
        "ConversationDocument", back_populates="conversation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, user_id={self.user_id}, title={self.title!r})>"
