"""
SQLAlchemy ORM models for DocQuery application metadata.

These models store ONLY metadata (filenames, statuses, timestamps, Q&A
history). Embeddings, vector indexes, and LLM-specific data are handled
elsewhere in the pipeline (vector store, not SQLite).
"""

from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


def _utcnow() -> datetime:
    """Default timestamp factory (UTC) for new records."""
    return datetime.now(timezone.utc)


class Document(Base):
    """
    Represents an uploaded document's metadata and processing status.

    Status is expected to move through states such as:
    'uploaded' -> 'processing' -> 'indexed' (or 'failed').
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Public-facing unique identifier for the document (e.g. UUID string).
    document_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )

    # Original filename; must not be empty.
    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # File extension / MIME type, e.g. "pdf", "txt", "docx".
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # When the document was uploaded.
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Current processing status: uploaded, processing, indexed, failed.
    status: Mapped[str] = mapped_column(
        String(32), default="uploaded", nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<Document(document_id={self.document_id!r}, "
            f"filename={self.filename!r}, status={self.status!r})>"
        )


class Question(Base):
    """
    Represents a question asked against the document corpus, along with
    the generated answer. This is a placeholder for future RAG integration
    and stores no embeddings, retrieval context, or LLM configuration.
    """

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    question: Mapped[str] = mapped_column(Text, nullable=False)

    # Nullable because a question may be recorded before an answer exists.
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, question={self.question[:30]!r})>"