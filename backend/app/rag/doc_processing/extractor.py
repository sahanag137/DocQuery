"""
extractor.py

Text extraction module for DocQuery.
Extracts text from PDF, TXT, and Markdown files while preserving page numbers,
structure, and document metadata. Includes fallbacks for encoding and corrupted files.
Ensures file handles are properly closed to prevent Windows file locking.
"""

from pathlib import Path
from typing import Dict, List, Union
import logging

logger = logging.getLogger(__name__)


def _extract_pdf_pages(file_path: Path) -> List[Dict]:
    """Extract pages from a PDF file using PyMuPDF (fitz) with pypdf fallback."""
    pages = []

    # 1. Primary method: PyMuPDF (fitz)
    try:
        import fitz
        doc = fitz.open(str(file_path))
        try:
            for page_number, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                if text:
                    pages.append({
                        "page": page_number,
                        "text": text
                    })
        finally:
            doc.close()

        if pages:
            return pages
    except Exception as exc:
        logger.warning(
            "PyMuPDF extraction failed for '%s' (%s), attempting pypdf fallback...",
            file_path.name, exc
        )

    # 2. Fallback method: pypdf with explicit context manager
    try:
        import pypdf
        with open(str(file_path), "rb") as f:
            reader = pypdf.PdfReader(f)
            for page_number, page in enumerate(reader.pages, start=1):
                try:
                    text = (page.extract_text() or "").strip()
                    if text:
                        pages.append({
                            "page": page_number,
                            "text": text
                        })
                except Exception as page_exc:
                    logger.warning("pypdf failed on page %d of '%s': %s", page_number, file_path.name, page_exc)
        if pages:
            return pages
    except Exception as exc:
        logger.error("pypdf extraction also failed for '%s': %s", file_path.name, exc)

    return pages


def _extract_text_file(file_path: Path) -> List[Dict]:
    """Extract text from TXT or Markdown files with encoding fallbacks."""
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    content = ""

    for enc in encodings:
        try:
            content = file_path.read_text(encoding=enc).strip()
            if content:
                break
        except UnicodeDecodeError:
            continue
        except Exception:
            break

    if not content:
        return []

    # For structured text / markdown with page separators (\x0c)
    if "\x0c" in content:
        raw_pages = content.split("\x0c")
        pages = []
        for p_num, raw_p in enumerate(raw_pages, start=1):
            cleaned = raw_p.strip()
            if cleaned:
                pages.append({"page": p_num, "text": cleaned})
        if pages:
            return pages

    return [{"page": 1, "text": content}]


def extract_pages(file_path: Union[str, Path]) -> List[Dict]:
    """
    Extract text and page-level information from a document file.
    Supports PDF, TXT, and Markdown (.md, .markdown).
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()

    if ext == ".pdf":
        return _extract_pdf_pages(path)
    elif ext in {".txt", ".md", ".markdown"}:
        return _extract_text_file(path)
    else:
        raise ValueError(f"Unsupported document format: '{ext}'. Supported formats: PDF, TXT, Markdown.")
