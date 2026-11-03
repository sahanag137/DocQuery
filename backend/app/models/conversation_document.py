"""
conversation_document.py

Association model linking conversations with attached documents.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.document import Document


class ConversationDocument(Base):
    """Many-to-many relationship between Conversations and Documents."""

    __tablename__ = "conversation_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("conversation_id", "document_id", name="uq_conversation_document"),
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="document_associations")
    document: Mapped["Document"] = relationship("Document", back_populates="conversation_associations")

    def __repr__(self) -> str:
        return (
            f"<ConversationDocument(conversation_id={self.conversation_id}, "
            f"document_id={self.document_id})>"
        )
