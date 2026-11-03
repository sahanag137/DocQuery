"""
message.py

SQLAlchemy model for chat messages.
Stores both user questions and assistant answers along with source citations.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Message(Base):
    """Individual chat message within a conversation."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional JSON string storing citations, retrieval chunks, page numbers, etc.
    source_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True, nullable=False
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, conv_id={self.conversation_id}, role={self.role!r})>"
