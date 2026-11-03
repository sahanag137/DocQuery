"""
document.py

SQLAlchemy model for uploaded documents.
Tracks file storage details, ownership, processing state, and metadata.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.conversation_document import ConversationDocument


class Document(Base):
    """Document metadata and storage record."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Core required fields
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status: uploaded, processing, processed, failed
    processing_status: Mapped[str] = mapped_column(
        String(32), default="uploaded", index=True, nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True, nullable=False
    )

    # Legacy compatibility identifier (UUID string)
    document_id: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, index=True, nullable=True, default=lambda: uuid.uuid4().hex
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="documents")
    conversation_associations: Mapped[List["ConversationDocument"]] = relationship(
        "ConversationDocument", back_populates="document", cascade="all, delete-orphan"
    )

    # Backwards compatibility properties for existing modules
    @property
    def filename(self) -> str:
        return self.original_filename

    @filename.setter
    def filename(self, val: str) -> None:
        self.original_filename = val

    @property
    def file_type(self) -> str:
        return self.mime_type

    @file_type.setter
    def file_type(self, val: str) -> None:
        self.mime_type = val

    @property
    def status(self) -> str:
        return self.processing_status

    @status.setter
    def status(self, val: str) -> None:
        self.processing_status = val

    @property
    def upload_date(self) -> datetime:
        return self.uploaded_at

    @upload_date.setter
    def upload_date(self, val: datetime) -> None:
        self.uploaded_at = val

    def __repr__(self) -> str:
        return (
            f"<Document(id={self.id}, user_id={self.user_id}, "
            f"name={self.original_filename!r}, status={self.processing_status!r})>"
        )
