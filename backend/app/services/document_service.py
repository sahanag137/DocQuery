"""
document_service.py

Service layer for document uploads, metadata management, inline viewing,
secure downloads, and conversation-document associations.
"""

from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.conversation import Conversation
from app.models.conversation_document import ConversationDocument
from app.models.document import Document
from app.schemas.document import DocumentResponse
from app.utils.file_handler import (
    delete_file_if_exists,
    generate_unique_filename,
    sanitize_filename,
    validate_file_extension,
)


def _to_document_response(doc: Document) -> DocumentResponse:
    """Helper to convert Document ORM model to DocumentResponse schema."""
    doc_identifier = str(doc.id)
    return DocumentResponse(
        id=doc.id,
        document_id=doc.document_id or str(doc.id),
        user_id=doc.user_id,
        original_filename=doc.original_filename,
        stored_filename=doc.stored_filename,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        processing_status=doc.processing_status,
        uploaded_at=doc.uploaded_at,
        view_url=f"/documents/{doc_identifier}/view",
        download_url=f"/documents/{doc_identifier}/download",
    )


async def save_uploaded_document(
    db: Session,
    user_id: int,
    file: UploadFile,
) -> Document:
    """
    Validate, save a document to disk, and persist metadata in the database.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename.",
        )

    # 1. Validate file extension
    ext, mime_type = validate_file_extension(
        file.filename, settings.ALLOWED_DOCUMENT_EXTENSIONS
    )

    clean_name = sanitize_filename(file.filename)
    unique_id, stored_filename = generate_unique_filename(clean_name)

    settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    destination_path = settings.DOCUMENTS_DIR / stored_filename

    # 2. Stream and write to disk, enforcing size limits
    total_bytes = 0
    try:
        with destination_path.open("wb") as destination_file:
            while chunk := await file.read(64 * 1024):
                total_bytes += len(chunk)
                if total_bytes > settings.max_file_size_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            f"File size exceeds maximum allowed limit of "
                            f"{settings.MAX_FILE_SIZE_MB}MB."
                        ),
                    )
                destination_file.write(chunk)
    except Exception:
        delete_file_if_exists(destination_path)
        raise
    finally:
        await file.close()

    # 3. Create database record
    try:
        document = Document(
            user_id=user_id,
            original_filename=clean_name,
            stored_filename=stored_filename,
            file_path=str(destination_path),
            mime_type=mime_type,
            file_size=total_bytes,
            processing_status="uploaded",
            document_id=unique_id,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document
    except Exception as error:
        delete_file_if_exists(destination_path)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record document metadata: {error}",
        ) from error


def get_document_by_id_or_uuid(
    db: Session,
    document_id: str | int,
    user_id: Optional[int] = None,
) -> Document:
    """
    Lookup a document by either integer primary key or UUID document_id string.
    Optionally enforces user ownership.
    """
    stmt = select(Document)
    doc_id_str = str(document_id).strip()

    if doc_id_str.isdigit():
        stmt = stmt.where((Document.id == int(doc_id_str)) | (Document.document_id == doc_id_str))
    else:
        stmt = stmt.where(Document.document_id == doc_id_str)

    document = db.execute(stmt).scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    # Ownership check
    if user_id is not None and document.user_id is not None and document.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this document.",
        )

    return document


def get_user_documents(
    db: Session,
    user_id: int,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Document]:
    """Retrieve all documents owned by the user with pagination."""
    stmt = (
        select(Document)
        .where((Document.user_id == user_id) | (Document.user_id.is_(None)))
        .order_by(Document.uploaded_at.desc())
    )

    if status_filter:
        stmt = stmt.where(Document.processing_status == status_filter.strip().lower())

    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def delete_document(db: Session, document: Document) -> None:
    """Remove a document physical file from disk and delete the database row."""
    if document.file_path:
        delete_file_if_exists(document.file_path)

    db.delete(document)
    db.commit()


def associate_document_with_chat(
    db: Session,
    user_id: int,
    conversation_id: int,
    document_id_or_uuid: str | int,
) -> ConversationDocument:
    """
    Associate a document with a conversation, ensuring ownership of both.
    """
    # 1. Verify conversation ownership
    conversation = db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )

    # 2. Verify document ownership
    document = get_document_by_id_or_uuid(db, document_id_or_uuid, user_id=user_id)

    # 3. Check if already associated
    existing = db.execute(
        select(ConversationDocument).where(
            ConversationDocument.conversation_id == conversation.id,
            ConversationDocument.document_id == document.id,
        )
    ).scalar_one_or_none()

    if existing:
        return existing

    assoc = ConversationDocument(
        conversation_id=conversation.id,
        document_id=document.id,
    )
    db.add(assoc)
    db.commit()
    db.refresh(assoc)
    return assoc


def get_chat_documents(
    db: Session,
    user_id: int,
    conversation_id: int,
) -> List[Document]:
    """Retrieve all documents associated with a specific conversation."""
    conversation = db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )

    stmt = (
        select(Document)
        .join(ConversationDocument, ConversationDocument.document_id == Document.id)
        .where(ConversationDocument.conversation_id == conversation.id)
        .order_by(Document.uploaded_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def remove_document_from_chat(
    db: Session,
    user_id: int,
    conversation_id: int,
    document_id_or_uuid: str | int,
) -> None:
    """Remove the association between a document and a conversation."""
    conversation = db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )

    document = get_document_by_id_or_uuid(db, document_id_or_uuid, user_id=user_id)

    assoc = db.execute(
        select(ConversationDocument).where(
            ConversationDocument.conversation_id == conversation.id,
            ConversationDocument.document_id == document.id,
        )
    ).scalar_one_or_none()

    if not assoc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document is not associated with this conversation.",
        )

    db.delete(assoc)
    db.commit()
