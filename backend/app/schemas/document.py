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
    filename: Optional[str] = None
    stored_filename: Optional[str] = ""
    mime_type: str
    file_type: Optional[str] = None
    file_size: int
    processing_status: str
    status: Optional[str] = None
    uploaded_at: datetime
    upload_date: Optional[datetime] = None
    view_url: Optional[str] = None
    download_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    """Response returned upon successful file upload."""
    id: int
    document_id: str
    filename: str
    original_filename: Optional[str] = None
    file_type: str
    mime_type: Optional[str] = None
    status: str
    processing_status: Optional[str] = None
    message: str

    model_config = ConfigDict(from_attributes=True)


class DocumentAssociateRequest(BaseModel):
    """Request payload to associate an existing document with a conversation."""
    document_id: str = Field(..., description="The ID (integer id or UUID string) of the document to associate")
