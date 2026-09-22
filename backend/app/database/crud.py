"""
CRUD (Create, Read, Update, Delete) helper functions for DocQuery.

These functions are plain SQLAlchemy operations with no FastAPI-specific
logic (no Depends, no HTTPException) so they can be reused anywhere,
including in scripts, background tasks, or future RAG pipeline code.
"""

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.models import Document, Question


# ---------------------------------------------------------------------------
# Document CRUD
# ---------------------------------------------------------------------------
def create_document(
    db: Session,
    document_id: str,
    filename: str,
    file_type: str,
    status: str = "uploaded",
) -> Document:
    """Create and persist a new Document record."""
    db_document = Document(
        document_id=document_id,
        filename=filename,
        file_type=file_type,
        status=status,
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document


def get_document(db: Session, document_id: str) -> Document | None:
    """
    Fetch a single document by its public document_id.
    Returns None if no matching document is found.
    """
    stmt = select(Document).where(Document.document_id == document_id)
    return db.execute(stmt).scalar_one_or_none()


def get_documents(db: Session, skip: int = 0, limit: int = 100) -> list[Document]:
    """Fetch a paginated list of documents, most recently uploaded first."""
    stmt = (
        select(Document)
        .order_by(Document.upload_date.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def delete_document(db: Session, document_id: str) -> bool:
    """
    Delete a document by document_id.
    Returns True if a record was deleted, False if it did not exist.
    """
    db_document = get_document(db, document_id)
    if db_document is None:
        return False

    db.delete(db_document)
    db.commit()
    return True


def update_document_status(db: Session, document_id: str, status: str) -> Document | None:
    """
    Update the status of a document (e.g. 'processing', 'indexed', 'failed').
    Returns the updated Document, or None if it does not exist.
    """
    db_document = get_document(db, document_id)
    if db_document is None:
        return None

    db_document.status = status
    db.commit()
    db.refresh(db_document)
    return db_document


# ---------------------------------------------------------------------------
# Question CRUD
# ---------------------------------------------------------------------------
def create_question(db: Session, question: str, answer: str | None = None) -> Question:
    """Create and persist a new Question record."""
    db_question = Question(question=question, answer=answer)
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


def get_questions(db: Session, skip: int = 0, limit: int = 100) -> list[Question]:
    """Fetch a paginated list of questions, most recent first."""
    stmt = (
        select(Question)
        .order_by(Question.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())