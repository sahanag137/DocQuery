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
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    file_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False, default="application/pdf")
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status: uploaded, processing, processed, failed
    processing_status: Mapped[str] = mapped_column(
        String(32), default="uploaded", index=True, nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True, nullable=False
    )

    # Legacy compatibility columns present in existing SQLite databases
    filename: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    file_type: Mapped[str] = mapped_column(String(32), nullable=False, default="pdf")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
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

    def __init__(self, **kwargs):
        """Auto-populate legacy and modern fields simultaneously."""
        # Filename synchronization
        orig = kwargs.get("original_filename") or kwargs.get("filename") or ""
        kwargs["original_filename"] = orig
        kwargs["filename"] = orig

        # Mime type / file type synchronization
        mime = kwargs.get("mime_type") or kwargs.get("file_type") or "application/pdf"
        kwargs["mime_type"] = mime
        kwargs["file_type"] = mime[:32]

        # Status synchronization
        stat = kwargs.get("processing_status") or kwargs.get("status") or "uploaded"
        kwargs["processing_status"] = stat
        kwargs["status"] = stat

        # Timestamp synchronization
        now_val = kwargs.get("uploaded_at") or kwargs.get("upload_date") or utcnow()
        kwargs["uploaded_at"] = now_val
        kwargs["upload_date"] = now_val

        # Ensure document_id
        if "document_id" not in kwargs or not kwargs["document_id"]:
            kwargs["document_id"] = uuid.uuid4().hex

        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<Document(id={self.id}, user_id={self.user_id}, "
            f"name={self.original_filename!r}, status={self.processing_status!r})>"
        )
