"""
documents.py

API routes for document upload, listing, details, inline viewing,
secure download, and deletion.
"""

from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.config import settings
from app.database.connection import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.services import document_service
from app.services.document_service import _to_document_response
from app.utils.file_handler import range_request_response

router = APIRouter(prefix="/documents", tags=["documents"])


def _resolve_physical_file(doc: Document) -> Path:
    """Resolve physical document file on disk with backward-compatibility fallbacks."""
    if doc.file_path and Path(doc.file_path).is_file():
        return Path(doc.file_path)

    # Check storage/documents
    if doc.stored_filename:
        storage_path = settings.DOCUMENTS_DIR / doc.stored_filename
        if storage_path.is_file():
            return storage_path

    # Check legacy data/documents directory
    legacy_dir = settings.DOCUMENTS_DIR.parents[1] / "data" / "documents"
    if doc.document_id:
        matches = list(legacy_dir.glob(f"{doc.document_id}__*"))
        if matches and matches[0].is_file():
            return matches[0]

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="The physical document file could not be found on the server.",
    )


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentUploadResponse:
    """
    Upload a single document (PDF, TXT, or Markdown).
    Validates file format and size, stores securely, and records ownership.
    """
    document = await document_service.save_uploaded_document(
        db=db, user_id=current_user.id, file=file
    )
    return DocumentUploadResponse(
        id=document.id,
        document_id=document.document_id or str(document.id),
        filename=document.original_filename,
        file_type=document.mime_type,
        status=document.processing_status,
        message="File uploaded successfully.",
    )


@router.get("", response_model=List[DocumentResponse])
def list_documents(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DocumentResponse]:
    """
    List all documents uploaded by or accessible to the current user.
    """
    docs = document_service.get_user_documents(
        db, user_id=current_user.id, status_filter=status_filter, skip=skip, limit=limit
    )
    return [_to_document_response(d) for d in docs]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_details(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """
    Retrieve metadata for a specific document by its ID.
    """
    doc = document_service.get_document_by_id_or_uuid(
        db, document_id, user_id=current_user.id
    )
    return _to_document_response(doc)


@router.get("/{document_id}/view")
def view_document_inline(
    document_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Stream a document for inline viewing (supports HTTP 206 Partial Content range requests).
    Ideal for PDF viewers embedded in the frontend UI.
    """
    doc = document_service.get_document_by_id_or_uuid(
        db, document_id, user_id=current_user.id
    )
    file_path = _resolve_physical_file(doc)
    return range_request_response(
        file_path=file_path,
        request=request,
        content_type=doc.mime_type,
        inline_filename=doc.original_filename,
    )


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """
    Download the original uploaded document as a file attachment.
    """
    doc = document_service.get_document_by_id_or_uuid(
        db, document_id, user_id=current_user.id
    )
    file_path = _resolve_physical_file(doc)
    return FileResponse(
        path=str(file_path),
        media_type=doc.mime_type,
        filename=doc.original_filename,
        headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'},
    )


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Permanently delete a document and its file on disk.
    """
    doc = document_service.get_document_by_id_or_uuid(
        db, document_id, user_id=current_user.id
    )
    document_service.delete_document(db, doc)
    return {
        "document_id": str(document_id),
        "message": "Document deleted successfully.",
    }
