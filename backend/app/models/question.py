"""
question.py

Legacy Question model for backward compatibility with existing DocQuery code.
"""

from datetime import datetime
from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, utcnow


class Question(Base):
    """
    Represents a legacy question asked against the document corpus.
    Kept for backwards compatibility with earlier database models.
    """

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, question={self.question[:30]!r})>"
