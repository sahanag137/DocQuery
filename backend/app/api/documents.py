"""
documents.py

API layer for document management in the DocQuery system.

This module exposes endpoints to upload, list, retrieve, and delete
original documentation files. It only handles raw files on disk -
no text extraction, chunking, embeddings, FAISS indexing, RAG
retrieval, or database logic happens here. Those concerns belong to
other modules that will be added later.

Supported file types (for now): PDF, Markdown (.md), and plain text (.txt).
"""

import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status

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
# filename when saving to disk. This lets us recover the original
# filename later without needing a database.
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
    - The original filename can still be recovered later.

    Args:
        document_id: The unique ID generated for this document.
        original_filename: The filename provided by the uploader.

    Returns:
        The filename to use when saving the file to disk.
    """
    return f"{document_id}{ID_SEPARATOR}{original_filename}"


def _find_document_path(document_id: str) -> Optional[Path]:
    """
    Look up the stored file path for a given document ID.

    Args:
        document_id: The unique ID of the document to find.

    Returns:
        The matching Path if found, otherwise None.
    """
    _ensure_documents_dir()
    matches = list(DOCUMENTS_DIR.glob(f"{document_id}{ID_SEPARATOR}*"))
    return matches[0] if matches else None


def _parse_stored_file(file_path: Path) -> Dict[str, str]:
    """
    Extract document metadata from a stored file's path.

    Args:
        file_path: Path to a file stored inside DOCUMENTS_DIR.

    Returns:
        A dictionary with document_id, filename, and file_type.
    """
    document_id, _, original_filename = file_path.name.partition(ID_SEPARATOR)
    return {
        "document_id": document_id,
        "filename": original_filename,
        "file_type": file_path.suffix.lower().lstrip("."),
    }


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)) -> Dict[str, str]:
    """
    Upload a single document (PDF, Markdown, or plain text).

    The file is validated by extension, saved to the documents
    directory under a unique, generated name, and basic metadata is
    returned to the caller.

    Args:
        file: The uploaded file, provided as multipart/form-data.

    Returns:
        A dict with document_id, filename, file_type, and a
        confirmation message.

    Raises:
        HTTPException: 400 if the filename is missing or the file
            type is unsupported, or 500 if the file could not be saved.
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

    return {
        "document_id": document_id,
        "filename": file.filename,
        "file_type": file_extension.lstrip("."),
        "message": "File uploaded successfully.",
    }


@router.get("")
async def list_documents() -> List[Dict[str, str]]:
    """
    List all documents currently stored in the documents directory.

    Returns:
        A list of dicts, each containing document_id, filename, and
        file_type for one stored document. Returns an empty list if
        no documents have been uploaded yet.
    """
    _ensure_documents_dir()

    documents: List[Dict[str, str]] = []
    for file_path in sorted(DOCUMENTS_DIR.iterdir()):
     if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
        documents.append(_parse_stored_file(file_path))

    return documents


@router.get("/{document_id}")
async def get_document(document_id: str) -> Dict[str, str]:
    """
    Get information about a single document by its ID.

    Args:
        document_id: The unique ID of the document to look up.

    Returns:
        A dict with document_id, filename, and file_type.

    Raises:
        HTTPException: 404 if no document with that ID exists.
    """
    file_path = _find_document_path(document_id)
    if file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    return _parse_stored_file(file_path)


@router.delete("/{document_id}")
async def delete_document(document_id: str) -> Dict[str, str]:
    """
    Delete a document by its ID.

    Args:
        document_id: The unique ID of the document to delete.

    Returns:
        A dict confirming the deletion.

    Raises:
        HTTPException: 404 if no document with that ID exists, or
            500 if the file could not be deleted.
    """
    file_path = _find_document_path(document_id)
    if file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    try:
        file_path.unlink()
    except OSError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {error}",
        ) from error

    return {
        "document_id": document_id,
        "message": "Document deleted successfully.",
    }