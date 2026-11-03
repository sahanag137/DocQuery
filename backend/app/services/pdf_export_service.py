"""
pdf_export_service.py

Service to export conversation transcripts to formatted PDF files using fpdf2.
"""

from datetime import datetime, timezone
import json
from typing import List

from fpdf import FPDF
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.document import Document
from app.models.message import Message
from app.services.chat_service import get_conversation_by_id


class ChatPDF(FPDF):
    """Custom PDF template with headers and page numbering."""

    def __init__(self, title: str):
        super().__init__()
        self.doc_title = title

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, "DocQuery - Chat Export", new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, f"Conversation: {self.doc_title}", new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_text_color(0, 0, 0)
        self.line(10, 26, 200, 26)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def export_conversation_to_pdf(
    db: Session,
    conversation_id: int,
    user_id: int,
) -> bytes:
    """
    Generate a formatted PDF document containing the full transcript of a conversation.

    Args:
        db: Database session.
        conversation_id: Conversation primary key ID.
        user_id: Authenticated user ID.

    Returns:
        Raw bytes representing the generated PDF file.
    """
    conversation = get_conversation_by_id(db, conversation_id, user_id=user_id)

    pdf = ChatPDF(title=conversation.title)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Conversation Metadata
    pdf.set_font("Helvetica", "", 10)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf.cell(0, 6, f"Exported on: {now_str}", new_x="LMARGIN", new_y="NEXT")

    # Attached Documents
    associated_docs: List[Document] = [
        assoc.document for assoc in conversation.document_associations if assoc.document
    ]
    if associated_docs:
        doc_names = ", ".join([d.original_filename for d in associated_docs])
        pdf.cell(0, 6, f"Referenced Documents: {doc_names}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # Transcript messages
    if not conversation.messages:
        pdf.set_font("Helvetica", "I", 11)
        pdf.cell(0, 10, "No messages in this conversation.", new_x="LMARGIN", new_y="NEXT")
    else:
        for msg in conversation.messages:
            is_user = msg.role.lower() == "user"
            speaker_label = "You" if is_user else "DocQuery Assistant"

            # Speaker Box Header
            pdf.set_font("Helvetica", "B", 10)
            if is_user:
                pdf.set_text_color(25, 75, 150)  # Blue for user
            else:
                pdf.set_text_color(30, 120, 60)   # Green for assistant

            time_str = msg.created_at.strftime("%H:%M:%S")
            pdf.cell(0, 6, f"{speaker_label} ({time_str}):", new_x="LMARGIN", new_y="NEXT")

            # Message content
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)

            # Sanitize content for standard PDF encoding (latin-1 fallback)
            clean_content = msg.content.encode("latin-1", "replace").decode("latin-1")
            pdf.multi_cell(0, 5, clean_content)

            # Optional Citations / Sources
            if msg.source_metadata:
                try:
                    sources = json.loads(msg.source_metadata)
                    pdf.set_font("Helvetica", "I", 8)
                    pdf.set_text_color(120, 120, 120)
                    pdf.multi_cell(0, 4, f"Sources: {sources}")
                except Exception:
                    pass

            pdf.ln(4)

    return bytes(pdf.output())
