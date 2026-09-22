"""
documents.py

API layer for document management in the DocQuery system.

This module exposes endpoints to upload, list, retrieve, and delete
original documentation files. It only handles raw files on disk and
their metadata in the database - no text extraction, chunking,
embeddings, FAISS indexing, RAG retrieval, or LLM logic happens here.
Those concerns belong to other modules that will be added later.

Document metadata (document_id, filename, file_type, upload_date,
status) is persisted in the SQLite database via the existing
database/crud/models layer. The physical files themselves still live
on disk under data/documents/.

Supported file types (for now): PDF, Markdown (.md), and plain text (.txt).
"""

import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import crud
from app.database.database import get_db
from app.database.models import Document

# Router for all document-related endpoints.
# Every route defined here will automatically be prefixed with "/documents".
router = APIRouter(prefix="/documents", tags=["documents"])

# This file lives at: <PROJECT_ROOT>/backend/app/api/documents.py
# parents[0] = api, parents[1] = app, parents[2] = backend, parents[3] = project root.
# Computing the root this way means storage works the same whether the
# server is started from the project root or from backend/.
PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]

# Directory where uploaded files are stored on disk.
DOCUMENTS_DIR: Path = PROJECT_ROOT / "data" / "documents"

# File extensions the system currently knows how to accept.
ALLOWED_EXTENSIONS: set[str] = {".pdf", ".md", ".txt"}

# Separator used between the generated document ID and the original
# filename when saving to disk. This lets us locate a document's
# physical file later using only its document_id.
ID_SEPARATOR: str = "__"


def _ensure_documents_dir() -> None:
    """
    Make sure the documents storage directory exists.

    Creates the directory (including any missing parent directories)
    if it does not already exist. Safe to call multiple times.
    """
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


def _build_stored_filename(document_id: str, original_filename: str) -> str:
    """
    Build the filename used to store a file on disk.

    Combines the generated document ID with the original filename so
    that:
    - Files with identical original names never collide.
    - The original filename can still be recovered from disk if needed.

    Args:
        document_id: The unique ID generated for this document.
        original_filename: The filename provided by the uploader.

    Returns:
        The filename to use when saving the file to disk.
    """
    return f"{document_id}{ID_SEPARATOR}{original_filename}"


def _find_document_path(document_id: str) -> Optional[Path]:
    """
    Look up the stored physical file path for a given document ID.

    This only looks at the filesystem (used for saving/deleting the
    actual file). Document metadata itself comes from the database.

    Args:
        document_id: The unique ID of the document to find.

    Returns:
        The matching Path if found, otherwise None.
    """
    _ensure_documents_dir()
    matches = list(DOCUMENTS_DIR.glob(f"{document_id}{ID_SEPARATOR}*"))
    return matches[0] if matches else None


def _document_to_dict(document: Document) -> Dict[str, str]:
    """
    Convert a Document database record into a JSON-serializable dict.

    Args:
        document: The Document ORM instance to convert.

    Returns:
        A dict with document_id, filename, file_type, upload_date,
        and status.
    """
    return {
        "document_id": document.document_id,
        "filename": document.filename,
        "file_type": document.file_type,
        "upload_date": document.upload_date.isoformat(),
        "status": document.status,
    }


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """
    Upload a single document (PDF, Markdown, or plain text).

    The file is validated by extension, saved to the documents
    directory under a unique, generated name, and a corresponding
    metadata record is created in the database with status
    "uploaded". If the database record cannot be created, the
    physical file that was just saved is removed so the filesystem
    and database stay consistent.

    Args:
        file: The uploaded file, provided as multipart/form-data.
        db: Database session, injected by FastAPI.

    Returns:
        A dict with document_id, filename, file_type, status, and a
        confirmation message.

    Raises:
        HTTPException: 400 if the filename is missing or the file
            type is unsupported, or 500 if the file could not be
            saved or the database record could not be created.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename.",
        )

    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type '{file_extension}'. "
                f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    _ensure_documents_dir()

    # Generate a unique ID so files with the same name never overwrite each other.
    document_id = uuid.uuid4().hex
    stored_filename = _build_stored_filename(document_id, file.filename)
    destination_path = DOCUMENTS_DIR / stored_filename
    file_type = file_extension.lstrip(".")

    # Step 1: Save the physical file to disk.
    try:
        with destination_path.open("wb") as destination_file:
            shutil.copyfileobj(file.file, destination_file)
    except OSError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {error}",
        ) from error
    finally:
        file.file.close()

    # Step 2: Create the corresponding database record.
    try:
        crud.create_document(
            db=db,
            document_id=document_id,
            filename=file.filename,
            file_type=file_type,
            status="uploaded",
        )
    except Exception as error:
        # Roll back the physical file so disk and database don't
        # disagree about which documents exist.
        destination_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save document metadata: {error}",
        ) from error

    return {
        "document_id": document_id,
        "filename": file.filename,
        "file_type": file_type,
        "status": "uploaded",
        "message": "File uploaded successfully.",
    }


@router.get("")
async def list_documents(db: Session = Depends(get_db)) -> List[Dict[str, str]]:
    """
    List all documents recorded in the database.

    Args:
        db: Database session, injected by FastAPI.

    Returns:
        A list of dicts, each containing document_id, filename,
        file_type, upload_date, and status for one stored document.
        Returns an empty list if no documents have been uploaded yet.
    """
    documents = crud.get_documents(db)
    return [_document_to_dict(document) for document in documents]


@router.get("/{document_id}")
async def get_document(document_id: str, db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Get information about a single document by its ID.

    Args:
        document_id: The unique ID of the document to look up.
        db: Database session, injected by FastAPI.

    Returns:
        A dict with document_id, filename, file_type, upload_date,
        and status.

    Raises:
        HTTPException: 404 if no document with that ID exists.
    """
    document = crud.get_document(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    return _document_to_dict(document)


@router.delete("/{document_id}")
async def delete_document(document_id: str, db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Delete a document by its ID.

    Looks up the document in the database, deletes the physical file
    from disk (if present), and then removes the database record.

    Args:
        document_id: The unique ID of the document to delete.
        db: Database session, injected by FastAPI.

    Returns:
        A dict confirming the deletion.

    Raises:
        HTTPException: 404 if no document with that ID exists in the
            database, or 500 if the physical file could not be deleted.
    """
    document = crud.get_document(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    # Step 1: Delete the physical file, if it exists on disk.
    file_path = _find_document_path(document_id)
    if file_path is not None:
        try:
            file_path.unlink()
        except OSError as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete document file: {error}",
            ) from error

    # Step 2: Delete the database record.
    crud.delete_document(db, document_id)

    return {
        "document_id": document_id,
        "message": "Document deleted successfully.",
    }