"""
crud.py

Backwards-compatibility shim preserving the original CRUD interface.
New code should use the service layer (app/services/) instead.
"""

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.document import Document
from app.models.question import Question


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
        original_filename=filename,
        stored_filename=filename,
        file_path="",
        mime_type=file_type,
        file_size=0,
        processing_status=status,
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document


def get_document(db: Session, document_id: str) -> Document | None:
    """Fetch a single document by its public document_id."""
    stmt = select(Document).where(Document.document_id == document_id)
    return db.execute(stmt).scalar_one_or_none()


def get_documents(db: Session, skip: int = 0, limit: int = 100) -> list[Document]:
    """Fetch a paginated list of documents, most recently uploaded first."""
    stmt = (
        select(Document)
        .order_by(Document.uploaded_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def delete_document(db: Session, document_id: str) -> bool:
    """Delete a document by document_id. Returns True if deleted, False if not found."""
    db_document = get_document(db, document_id)
    if db_document is None:
        return False
    db.delete(db_document)
    db.commit()
    return True


def update_document_status(db: Session, document_id: str, status: str) -> Document | None:
    """Update the status of a document."""
    db_document = get_document(db, document_id)
    if db_document is None:
        return None
    db_document.processing_status = status
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
