"""
base.py

SQLAlchemy declarative base and common model helpers for DocQuery.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    """Return the current time in UTC with timezone awareness."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass
