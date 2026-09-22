"""
Database configuration for DocQuery.

This module sets up the SQLAlchemy engine, session factory, and declarative
base used for storing application metadata (NOT embeddings or vector data).

The SQLite database file lives at: <project_root>/data/docquery.db
"""

from pathlib import Path
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


# ---------------------------------------------------------------------------
# Resolve project paths using pathlib (no hard-coded absolute paths)
# ---------------------------------------------------------------------------
# This file lives at: backend/app/database/database.py
# Project root is 4 levels up from this file.
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[3]

DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "docquery.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# check_same_thread=False is required because FastAPI can handle requests
# using multiple threads, while SQLite by default only allows the thread
# that created a connection to use it.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Declarative base (SQLAlchemy 2.x style)
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
def get_db() -> Generator:
    """
    FastAPI dependency that yields a database session and guarantees
    it is closed afterwards, even if an exception occurs.

    Usage:
        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()