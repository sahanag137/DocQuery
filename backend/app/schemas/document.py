"""
document.py

Pydantic schemas for Document operations.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """Document details response."""
    id: int
    document_id: Optional[str] = None
    user_id: Optional[int] = None
    original_filename: str
    stored_filename: str
    mime_type: str
    file_size: int
    processing_status: str
    uploaded_at: datetime
    view_url: Optional[str] = None
    download_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    """Response returned upon successful file upload."""
    id: int
    document_id: str
    filename: str
    file_type: str
    status: str
    message: str

    model_config = ConfigDict(from_attributes=True)


class DocumentAssociateRequest(BaseModel):
    """Request payload to associate an existing document with a conversation."""
    document_id: str = Field(..., description="The ID (integer id or UUID string) of the document to associate")
