"""
database.py

Backwards-compatibility shim re-exporting Base, engine, SessionLocal, and get_db.
"""

from app.database.connection import engine, SessionLocal, get_db, init_db
from app.database.base import Base, utcnow

__all__ = ["engine", "SessionLocal", "get_db", "Base", "utcnow", "init_db"]
