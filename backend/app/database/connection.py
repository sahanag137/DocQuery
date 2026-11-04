"""
connection.py

Database connection, engine configuration, session management,
and automatic SQLite schema migration.
"""

from collections.abc import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.database.base import Base

# Import all models to ensure they are registered with Base.metadata
import app.models  # noqa: F401


# Configure SQLite connection arguments
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)


# Enforce foreign key constraints in SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and guarantees
    it is closed afterwards.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_existing_tables() -> None:
    """
    Safely alter existing SQLite tables if they exist with older schema
    to avoid dropping or losing existing document records.
    """
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    with engine.connect() as conn:
        # Check if 'documents' table exists
        check_table = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        ).scalar_one_or_none()

        if check_table:
            # Check existing columns
            cols = [
                row[1] for row in conn.execute(text("PRAGMA table_info(documents)")).fetchall()
            ]

            # Add missing columns safely
            if "user_id" not in cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"))
            if "original_filename" not in cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN original_filename VARCHAR(255) DEFAULT ''"))
            if "stored_filename" not in cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN stored_filename VARCHAR(255) DEFAULT ''"))
            if "file_path" not in cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN file_path VARCHAR(512) DEFAULT ''"))
            if "mime_type" not in cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN mime_type VARCHAR(64) DEFAULT 'application/octet-stream'"))
            if "file_size" not in cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN file_size INTEGER DEFAULT 0"))
            if "processing_status" not in cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN processing_status VARCHAR(32) DEFAULT 'uploaded'"))
            if "uploaded_at" not in cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN uploaded_at DATETIME"))
            if "document_id" not in cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN document_id VARCHAR(64)"))

            # Synchronize existing legacy columns if present
            if "filename" in cols:
                conn.execute(text("UPDATE documents SET original_filename = filename WHERE (original_filename IS NULL OR original_filename = '') AND filename IS NOT NULL"))
                conn.execute(text("UPDATE documents SET filename = original_filename WHERE (filename IS NULL OR filename = '') AND original_filename IS NOT NULL"))
            if "file_type" in cols:
                conn.execute(text("UPDATE documents SET mime_type = file_type WHERE (mime_type IS NULL OR mime_type = '' OR mime_type = 'application/octet-stream') AND file_type IS NOT NULL"))
                conn.execute(text("UPDATE documents SET file_type = mime_type WHERE (file_type IS NULL OR file_type = '') AND mime_type IS NOT NULL"))
            if "status" in cols:
                conn.execute(text("UPDATE documents SET processing_status = status WHERE (processing_status IS NULL OR processing_status = '') AND status IS NOT NULL"))
                conn.execute(text("UPDATE documents SET status = processing_status WHERE (status IS NULL OR status = '') AND processing_status IS NOT NULL"))
            if "upload_date" in cols:
                conn.execute(text("UPDATE documents SET uploaded_at = upload_date WHERE uploaded_at IS NULL AND upload_date IS NOT NULL"))
                conn.execute(text("UPDATE documents SET upload_date = uploaded_at WHERE upload_date IS NULL AND uploaded_at IS NOT NULL"))

            conn.commit()


def init_db() -> None:
    """
    Initialize database schema, apply non-destructive SQLite migrations,
    and create all required tables.
    """
    _migrate_existing_tables()
    Base.metadata.create_all(bind=engine)
