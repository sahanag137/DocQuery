"""
user_settings.py

SQLAlchemy model for user preferences (theme, language, etc.).
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.user import User


class UserSettings(Base):
    """User preferences model."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    theme: Mapped[str] = mapped_column(String(32), default="light", nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="settings")

    def __repr__(self) -> str:
        return f"<UserSettings(user_id={self.user_id}, theme={self.theme!r}, language={self.language!r})>"
