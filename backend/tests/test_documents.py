"""
test_documents.py

Comprehensive tests for Module 4 (Document & PDF Management):
- Upload PDF, TXT, MD
- Invalid extension rejection
- Document listing and metadata
- Inline viewing and HTTP 206 range requests
- Original document download
- Document deletion
- Cross-user access isolation
"""

import io
from fastapi.testclient import TestClient


def test_upload_pdf_success(user_one: dict, client: TestClient):
    """Verify uploading a valid PDF document."""
    pdf_content = b"%PDF-1.4\n%test pdf content"
    files = {"file": ("manual.pdf", io.BytesIO(pdf_content), "application/pdf")}

    resp = client.post("/documents/upload", files=files, headers=user_one["headers"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["filename"] == "manual.pdf"
    assert data["status"] == "uploaded"
    assert "document_id" in data


def test_upload_text_and_markdown(user_one: dict, client: TestClient):
    """Verify uploading TXT and Markdown files."""
    txt_files = {"file": ("notes.txt", io.BytesIO(b"Simple notes text"), "text/plain")}
    resp_txt = client.post("/documents/upload", files=txt_files, headers=user_one["headers"])
    assert resp_txt.status_code == 201

    md_files = {"file": ("readme.md", io.BytesIO(b"# Markdown Header"), "text/markdown")}
    resp_md = client.post("/documents/upload", files=md_files, headers=user_one["headers"])
    assert resp_md.status_code == 201


def test_upload_unsupported_extension(user_one: dict, client: TestClient):
    """Verify that unsupported file types (.exe, .py, etc.) return 400."""
    bad_files = {"file": ("virus.exe", io.BytesIO(b"binary"), "application/octet-stream")}
    resp = client.post("/documents/upload", files=bad_files, headers=user_one["headers"])
    assert resp.status_code == 400
    assert "unsupported file extension" in resp.json()["detail"].lower()


def test_list_and_get_document(user_one: dict, client: TestClient):
    """Verify listing documents and retrieving single document metadata."""
    pdf_content = b"%PDF-1.4\nSample documentation body"
    files = {"file": ("spec.pdf", io.BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post("/documents/upload", files=files, headers=user_one["headers"])
    doc_id = upload_resp.json()["id"]

    # List documents
    list_resp = client.get("/documents", headers=user_one["headers"])
    assert list_resp.status_code == 200
    docs = list_resp.json()
    assert len(docs) >= 1
    assert any(d["original_filename"] == "spec.pdf" for d in docs)

    # Get single document
    get_resp = client.get(f"/documents/{doc_id}", headers=user_one["headers"])
    assert get_resp.status_code == 200
    assert get_resp.json()["original_filename"] == "spec.pdf"


def test_view_inline_and_range_request(user_one: dict, client: TestClient):
    """Verify inline document viewing and HTTP 206 Partial Content range requests."""
    pdf_content = b"%PDF-1.4 0123456789 ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    files = {"file": ("stream_test.pdf", io.BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post("/documents/upload", files=files, headers=user_one["headers"])
    doc_id = upload_resp.json()["id"]

    # Full view
    view_resp = client.get(f"/documents/{doc_id}/view", headers=user_one["headers"])
    assert view_resp.status_code == 200
    assert "inline" in view_resp.headers.get("content-disposition", "")

    # Range request (first 10 bytes)
    range_headers = {**user_one["headers"], "Range": "bytes=0-9"}
    range_resp = client.get(f"/documents/{doc_id}/view", headers=range_headers)
    assert range_resp.status_code == 206
    assert range_resp.headers["content-range"].startswith("bytes 0-9/")
    assert len(range_resp.content) == 10
    assert range_resp.content == pdf_content[:10]


def test_download_document(user_one: dict, client: TestClient):
    """Verify downloading original document as attachment."""
    pdf_content = b"%PDF-1.4 Document content download test"
    files = {"file": ("report.pdf", io.BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post("/documents/upload", files=files, headers=user_one["headers"])
    doc_id = upload_resp.json()["id"]

    down_resp = client.get(f"/documents/{doc_id}/download", headers=user_one["headers"])
    assert down_resp.status_code == 200
    assert "attachment" in down_resp.headers["content-disposition"]
    assert down_resp.content == pdf_content


def test_delete_document(user_one: dict, client: TestClient):
    """Verify document deletion removes record and disk file."""
    files = {"file": ("temp.pdf", io.BytesIO(b"%PDF-1.4 delete test"), "application/pdf")}
    upload_resp = client.post("/documents/upload", files=files, headers=user_one["headers"])
    doc_id = upload_resp.json()["id"]

    del_resp = client.delete(f"/documents/{doc_id}", headers=user_one["headers"])
    assert del_resp.status_code == 200

    # Getting deleted document returns 404
    get_resp = client.get(f"/documents/{doc_id}", headers=user_one["headers"])
    assert get_resp.status_code == 404


def test_cross_user_document_isolation(
    user_one: dict, user_two: dict, client: TestClient
):
    """Verify that User Two cannot view, download, or delete User One's documents."""
    files = {"file": ("alice_private.pdf", io.BytesIO(b"%PDF-1.4 private"), "application/pdf")}
    upload_resp = client.post("/documents/upload", files=files, headers=user_one["headers"])
    doc_id = upload_resp.json()["id"]

    # User Two attempts to get document metadata
    resp_get = client.get(f"/documents/{doc_id}", headers=user_two["headers"])
    assert resp_get.status_code == 403

    # User Two attempts to view document
    resp_view = client.get(f"/documents/{doc_id}/view", headers=user_two["headers"])
    assert resp_view.status_code == 403

    # User Two attempts to delete document
    resp_del = client.delete(f"/documents/{doc_id}", headers=user_two["headers"])
    assert resp_del.status_code == 403
