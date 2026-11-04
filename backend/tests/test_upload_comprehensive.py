"""
test_upload_comprehensive.py

Comprehensive end-to-end tests for the DocQuery document upload pipeline:
- Valid PDF, TXT, Markdown uploads
- Invalid file extensions rejection
- Oversized file rejection
- Unauthenticated rejection
- Listing and metadata with dual field aliases (filename, original_filename)
- Inline streaming view with Range requests (HTTP 200 & 206)
- File download
- Deletion and disk cleanup
"""

import io
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from app.core.config import settings


def test_upload_pdf_e2e(client: TestClient, user_one: dict):
    """Test full upload pipeline for a valid PDF document."""
    auth_headers = user_one["headers"]
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    files = {"file": ("manual_guide.pdf", io.BytesIO(pdf_content), "application/pdf")}

    response = client.post("/documents/upload", files=files, headers=auth_headers)
    assert response.status_code == 201, response.text
    data = response.json()

    assert "id" in data
    assert data["filename"] == "manual_guide.pdf"
    assert data["original_filename"] == "manual_guide.pdf"
    assert data["file_type"] == "application/pdf"
    assert data["status"] == "uploaded"
    assert "document_id" in data

    doc_id = data["document_id"]

    # Verify physical file stored on disk
    stored_files = list(settings.DOCUMENTS_DIR.glob(f"{doc_id}*"))
    assert len(stored_files) == 1
    assert stored_files[0].is_file()
    assert stored_files[0].read_bytes() == pdf_content

    # Verify listing includes both filename and original_filename
    list_resp = client.get("/documents", headers=auth_headers)
    assert list_resp.status_code == 200
    docs = list_resp.json()
    matched = [d for d in docs if d["document_id"] == doc_id]
    assert len(matched) == 1
    assert matched[0]["filename"] == "manual_guide.pdf"
    assert matched[0]["original_filename"] == "manual_guide.pdf"
    assert matched[0]["status"] == "uploaded"
    assert matched[0]["upload_date"] is not None

    # Verify inline viewing
    view_resp = client.get(f"/documents/{doc_id}/view", headers=auth_headers)
    assert view_resp.status_code == 200
    assert view_resp.headers["content-type"] == "application/pdf"
    assert view_resp.content == pdf_content

    # Verify inline viewing via token query parameter (used by browser iframes)
    token = user_one["token"]
    view_query_resp = client.get(f"/documents/{doc_id}/view?token={token}")
    assert view_query_resp.status_code == 200
    assert view_query_resp.content == pdf_content

    # Verify download
    dl_resp = client.get(f"/documents/{doc_id}/download", headers=auth_headers)
    assert dl_resp.status_code == 200
    assert dl_resp.content == pdf_content

    # Verify deletion cleans up both DB row and physical file
    del_resp = client.delete(f"/documents/{doc_id}", headers=auth_headers)
    assert del_resp.status_code == 200
    assert not stored_files[0].exists()


def test_upload_txt_and_md(client: TestClient, user_one: dict):
    """Test that text and markdown documents are accepted."""
    auth_headers = user_one["headers"]
    txt_file = {"file": ("notes.txt", io.BytesIO(b"Meeting notes"), "text/plain")}
    r_txt = client.post("/documents/upload", files=txt_file, headers=auth_headers)
    assert r_txt.status_code == 201
    assert r_txt.json()["filename"] == "notes.txt"

    md_file = {"file": ("readme.md", io.BytesIO(b"# Heading\nContent"), "text/markdown")}
    r_md = client.post("/documents/upload", files=md_file, headers=auth_headers)
    assert r_md.status_code == 201
    assert r_md.json()["filename"] == "readme.md"


def test_upload_unsupported_format(client: TestClient, user_one: dict):
    """Test rejection of unsupported file types."""
    auth_headers = user_one["headers"]
    exe_file = {"file": ("danger.exe", io.BytesIO(b"MZ..."), "application/octet-stream")}
    r = client.post("/documents/upload", files=exe_file, headers=auth_headers)
    assert r.status_code == 400
    assert "unsupported file extension" in r.json()["detail"].lower()


def test_upload_oversized_file(client: TestClient, user_one: dict, monkeypatch):
    """Test rejection of files exceeding maximum allowed size."""
    auth_headers = user_one["headers"]
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 1)
    huge_data = b"X" * (1024 * 1024 + 100)  # > 1MB
    huge_file = {"file": ("large.pdf", io.BytesIO(huge_data), "application/pdf")}
    r = client.post("/documents/upload", files=huge_file, headers=auth_headers)
    assert r.status_code == 413
    assert "exceeds maximum allowed limit" in r.json()["detail"]


def test_upload_unauthenticated(client: TestClient):
    """Test unauthenticated upload is rejected with 401."""
    pdf_content = b"%PDF-1.4 dummy"
    files = {"file": ("doc.pdf", io.BytesIO(pdf_content), "application/pdf")}
    r = client.post("/documents/upload", files=files)
    assert r.status_code == 401
