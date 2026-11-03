"""
test_chats.py

Comprehensive tests for Module 3 (Chat History) & Conversation-Document associations:
- Create conversation
- Post user and assistant messages with citations
- Automatic chat title generation
- Retrieve message history
- Search conversations by title and message content
- Rename and archive/restore conversations
- Delete conversation
- Associate and disassociate documents
- PDF export of conversation transcripts
- Cross-user conversation access isolation
"""

import io
from fastapi.testclient import TestClient


def test_create_chat_and_messages(user_one: dict, client: TestClient):
    """Verify creating a conversation, posting messages, and retrieving history."""
    # 1. Create chat
    create_resp = client.post("/chats", json={"title": "New Chat"}, headers=user_one["headers"])
    assert create_resp.status_code == 201
    chat_id = create_resp.json()["id"]

    # 2. Post user question
    msg_user = {
        "role": "user",
        "content": "What are the key terms in the library system?",
    }
    resp_user_msg = client.post(
        f"/chats/{chat_id}/messages", json=msg_user, headers=user_one["headers"]
    )
    assert resp_user_msg.status_code == 201
    assert resp_user_msg.json()["role"] == "user"

    # Verify auto-naming updated the title from 'New Chat'
    get_chat_resp = client.get(f"/chats/{chat_id}", headers=user_one["headers"])
    assert get_chat_resp.status_code == 200
    assert "What are the key terms" in get_chat_resp.json()["title"]

    # 3. Post assistant answer with citation metadata
    msg_assistant = {
        "role": "assistant",
        "content": "The key terms include Book, Member, and Loan.",
        "source_metadata": [{"source": "manual.pdf", "page": 2, "score": 0.95}],
    }
    resp_asst_msg = client.post(
        f"/chats/{chat_id}/messages", json=msg_assistant, headers=user_one["headers"]
    )
    assert resp_asst_msg.status_code == 201
    assert resp_asst_msg.json()["role"] == "assistant"
    assert resp_asst_msg.json()["source_metadata"] is not None

    # 4. Retrieve messages list
    list_msgs = client.get(f"/chats/{chat_id}/messages", headers=user_one["headers"])
    assert list_msgs.status_code == 200
    messages = list_msgs.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_search_conversations(user_one: dict, client: TestClient):
    """Verify searching chats by title or message content."""
    # Create chat 1
    c1 = client.post("/chats", json={"title": "Biology Research"}, headers=user_one["headers"]).json()
    client.post(
        f"/chats/{c1['id']}/messages",
        json={"role": "user", "content": "Explain cellular mitosis"},
        headers=user_one["headers"],
    )

    # Create chat 2
    c2 = client.post("/chats", json={"title": "Physics Notes"}, headers=user_one["headers"]).json()
    client.post(
        f"/chats/{c2['id']}/messages",
        json={"role": "user", "content": "Explain quantum entanglement"},
        headers=user_one["headers"],
    )

    # Search for "mitosis"
    search_resp = client.get("/chats?search=mitosis", headers=user_one["headers"])
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert len(results) == 1
    assert results[0]["id"] == c1["id"]

    # Search for "Physics"
    search_physics = client.get("/chats?search=Physics", headers=user_one["headers"])
    assert search_physics.status_code == 200
    assert len(search_physics.json()) == 1
    assert search_physics.json()[0]["id"] == c2["id"]


def test_rename_and_archive_chat(user_one: dict, client: TestClient):
    """Verify renaming a conversation and archiving/restoring it."""
    c = client.post("/chats", json={"title": "Draft Topic"}, headers=user_one["headers"]).json()
    chat_id = c["id"]

    # Rename
    patch_resp = client.patch(
        f"/chats/{chat_id}", json={"title": "Final Topic"}, headers=user_one["headers"]
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Final Topic"

    # Archive
    arc_resp = client.patch(
        f"/chats/{chat_id}", json={"is_archived": True}, headers=user_one["headers"]
    )
    assert arc_resp.status_code == 200
    assert arc_resp.json()["is_archived"] is True

    # When listing with include_archived=False, it should not appear
    list_active = client.get("/chats?include_archived=false", headers=user_one["headers"]).json()
    assert not any(chat["id"] == chat_id for chat in list_active)

    # When listing with include_archived=True, it should appear
    list_all = client.get("/chats?include_archived=true", headers=user_one["headers"]).json()
    assert any(chat["id"] == chat_id for chat in list_all)


def test_delete_chat(user_one: dict, client: TestClient):
    """Verify conversation deletion."""
    c = client.post("/chats", json={"title": "To Delete"}, headers=user_one["headers"]).json()
    chat_id = c["id"]

    del_resp = client.delete(f"/chats/{chat_id}", headers=user_one["headers"])
    assert del_resp.status_code == 200

    get_resp = client.get(f"/chats/{chat_id}", headers=user_one["headers"])
    assert get_resp.status_code == 404


def test_associate_and_remove_chat_document(user_one: dict, client: TestClient):
    """Verify associating an uploaded document with a chat and removing the link."""
    # 1. Upload doc
    pdf_file = {"file": ("guidelines.pdf", io.BytesIO(b"%PDF-1.4 guidelines"), "application/pdf")}
    doc = client.post("/documents/upload", files=pdf_file, headers=user_one["headers"]).json()
    doc_id = str(doc["id"])

    # 2. Create chat
    chat = client.post("/chats", json={"title": "Policy Chat"}, headers=user_one["headers"]).json()
    chat_id = chat["id"]

    # 3. Associate document
    assoc_resp = client.post(
        f"/chats/{chat_id}/documents",
        json={"document_id": doc_id},
        headers=user_one["headers"],
    )
    assert assoc_resp.status_code == 201

    # 4. List chat documents
    list_docs = client.get(f"/chats/{chat_id}/documents", headers=user_one["headers"])
    assert list_docs.status_code == 200
    docs = list_docs.json()
    assert len(docs) == 1
    assert docs[0]["original_filename"] == "guidelines.pdf"

    # Also verify document is in the full chat details endpoint
    chat_detail = client.get(f"/chats/{chat_id}", headers=user_one["headers"]).json()
    assert len(chat_detail["documents"]) == 1

    # 5. Remove association
    rem_resp = client.delete(
        f"/chats/{chat_id}/documents/{doc_id}", headers=user_one["headers"]
    )
    assert rem_resp.status_code == 200

    # Verify list is now empty
    list_docs_after = client.get(f"/chats/{chat_id}/documents", headers=user_one["headers"])
    assert len(list_docs_after.json()) == 0


def test_export_chat_pdf(user_one: dict, client: TestClient):
    """Verify exporting a conversation transcript to PDF."""
    chat = client.post("/chats", json={"title": "Export Test Chat"}, headers=user_one["headers"]).json()
    chat_id = chat["id"]

    # Add messages
    client.post(
        f"/chats/{chat_id}/messages",
        json={"role": "user", "content": "Hello, how does DocQuery work?"},
        headers=user_one["headers"],
    )
    client.post(
        f"/chats/{chat_id}/messages",
        json={
            "role": "assistant",
            "content": "DocQuery retrieves documentation chunks and answers questions.",
        },
        headers=user_one["headers"],
    )

    # Request PDF export
    export_resp = client.get(f"/chats/{chat_id}/export", headers=user_one["headers"])
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"] == "application/pdf"
    assert len(export_resp.content) > 0
    # PDF starts with %PDF
    assert export_resp.content.startswith(b"%PDF")


def test_cross_user_chat_isolation(
    user_one: dict, user_two: dict, client: TestClient
):
    """Verify User Two cannot view, message, or delete User One's chat."""
    chat = client.post("/chats", json={"title": "Private Chat"}, headers=user_one["headers"]).json()
    chat_id = chat["id"]

    # User Two tries to get chat
    assert client.get(f"/chats/{chat_id}", headers=user_two["headers"]).status_code == 403

    # User Two tries to post a message
    assert client.post(
        f"/chats/{chat_id}/messages",
        json={"role": "user", "content": "Spy message"},
        headers=user_two["headers"],
    ).status_code == 403

    # User Two tries to delete chat
    assert client.delete(f"/chats/{chat_id}", headers=user_two["headers"]).status_code == 403
