"""
export.py

API routes for exporting conversation transcripts to PDF.
"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.models.user import User
from app.services.pdf_export_service import export_conversation_to_pdf

router = APIRouter(prefix="/chats", tags=["export"])


@router.get("/{chat_id}/export", response_class=Response)
@router.get("/{chat_id}/export/pdf", response_class=Response)
def export_chat_pdf(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Export the entire transcript of a conversation as a formatted PDF document.
    """
    pdf_bytes = export_conversation_to_pdf(
        db, conversation_id=chat_id, user_id=current_user.id
    )

    headers = {
        "Content-Disposition": f'attachment; filename="chat_{chat_id}_transcript.pdf"',
        "Content-Type": "application/pdf",
    }
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers=headers,
    )
