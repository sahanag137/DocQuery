"""
test_chat_history_advanced.py

Advanced Chat History tests covering:
- Category creation and filtering
- Rename conversation via PATCH
- Move conversation to a different category
- Delete conversation (cascade messages, preserve documents)
- Resume conversation — load full detail with messages and documents
- Search by message content and by title
- Cross-user isolation for all advanced operations
- Empty-title rename validation
"""

import io
import pytest
from fastapi.testclient import TestClient


CATEGORIES = ["General", "Study", "Development", "Research"]


# ---------------------------------------------------------------------------
# 1. Category field — create with explicit category, default category
# ---------------------------------------------------------------------------

def test_create_conversation_with_category(user_one: dict, client: TestClient):
    """Creating a conversation with an explicit category persists it."""
    resp = client.post(
        "/chats",
        json={"title": "My Study Notes", "category": "Study"},
        headers=user_one["headers"],
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "My Study Notes"
    assert data["category"] == "Study"


def test_create_conversation_default_category(user_one: dict, client: TestClient):
    """Creating a conversation without specifying a category defaults to 'General'."""
    resp = client.post("/chats", json={"title": "Quick Chat"}, headers=user_one["headers"])
    assert resp.status_code == 201
    assert resp.json()["category"] == "General"


def test_create_conversation_invalid_category_falls_back(user_one: dict, client: TestClient):
    """An unrecognised category value is normalised to 'General'."""
    resp = client.post(
        "/chats",
        json={"title": "Bad Category", "category": "Nonsense"},
        headers=user_one["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["category"] == "General"


# ---------------------------------------------------------------------------
# 2. Categories endpoint
# ---------------------------------------------------------------------------

def test_list_categories_endpoint(user_one: dict, client: TestClient):
    """GET /chats/categories returns the four predefined categories."""
    resp = client.get("/chats/categories", headers=user_one["headers"])
    assert resp.status_code == 200
    cats = resp.json()
    assert set(cats) == {"General", "Study", "Development", "Research"}


# ---------------------------------------------------------------------------
# 3. Category filter — GET /chats?category=...
# ---------------------------------------------------------------------------

def test_filter_conversations_by_category(user_one: dict, client: TestClient):
    """Only conversations matching the requested category are returned."""
    client.post("/chats", json={"title": "Chat A", "category": "Study"}, headers=user_one["headers"])
    client.post("/chats", json={"title": "Chat B", "category": "Development"}, headers=user_one["headers"])
    client.post("/chats", json={"title": "Chat C", "category": "Study"}, headers=user_one["headers"])

    study_resp = client.get("/chats?category=Study", headers=user_one["headers"])
    assert study_resp.status_code == 200
    titles = [c["title"] for c in study_resp.json()]
    assert "Chat A" in titles
    assert "Chat C" in titles
    assert "Chat B" not in titles

    dev_resp = client.get("/chats?category=Development", headers=user_one["headers"])
    assert dev_resp.status_code == 200
    dev_titles = [c["title"] for c in dev_resp.json()]
    assert "Chat B" in dev_titles
    assert "Chat A" not in dev_titles


def test_filter_all_conversations_no_category_param(user_one: dict, client: TestClient):
    """Omitting the category filter returns all conversations regardless of category."""
    client.post("/chats", json={"title": "G Chat", "category": "General"}, headers=user_one["headers"])
    client.post("/chats", json={"title": "R Chat", "category": "Research"}, headers=user_one["headers"])

    all_resp = client.get("/chats", headers=user_one["headers"])
    titles = [c["title"] for c in all_resp.json()]
    assert "G Chat" in titles
    assert "R Chat" in titles


# ---------------------------------------------------------------------------
# 4. Rename conversation
# ---------------------------------------------------------------------------

def test_rename_conversation(user_one: dict, client: TestClient):
    """PATCH /chats/{id} with a new title updates the conversation title."""
    chat = client.post("/chats", json={"title": "Old Title"}, headers=user_one["headers"]).json()
    chat_id = chat["id"]

    patch_resp = client.patch(
        f"/chats/{chat_id}",
        json={"title": "Updated Title"},
        headers=user_one["headers"],
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Updated Title"

    # Verify the get endpoint also shows the new title
    get_resp = client.get(f"/chats/{chat_id}", headers=user_one["headers"])
    assert get_resp.json()["title"] == "Updated Title"


def test_rename_conversation_empty_title_rejected(user_one: dict, client: TestClient):
    """Attempting to rename to an empty title should return 422."""
    chat = client.post("/chats", json={"title": "Valid Title"}, headers=user_one["headers"]).json()
    patch_resp = client.patch(
        f"/chats/{chat['id']}",
        json={"title": "   "},
        headers=user_one["headers"],
    )
    assert patch_resp.status_code == 422


# ---------------------------------------------------------------------------
# 5. Move conversation to a different category
# ---------------------------------------------------------------------------

def test_move_conversation_to_different_category(user_one: dict, client: TestClient):
    """PATCH /chats/{id} with a new category updates only the category."""
    chat = client.post(
        "/chats", json={"title": "Moving Chat", "category": "General"}, headers=user_one["headers"]
    ).json()
    chat_id = chat["id"]

    patch_resp = client.patch(
        f"/chats/{chat_id}",
        json={"category": "Research"},
        headers=user_one["headers"],
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["category"] == "Research"
    # Title should be unchanged
    assert patch_resp.json()["title"] == "Moving Chat"


def test_move_conversation_invalid_category_falls_back(user_one: dict, client: TestClient):
    """Moving to an invalid category silently normalises to 'General'."""
    chat = client.post(
        "/chats", json={"title": "Chat X", "category": "Study"}, headers=user_one["headers"]
    ).json()
    patch_resp = client.patch(
        f"/chats/{chat['id']}",
        json={"category": "InvalidCat"},
        headers=user_one["headers"],
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["category"] == "General"


# ---------------------------------------------------------------------------
# 6. Delete conversation
# ---------------------------------------------------------------------------

def test_delete_conversation_removes_messages(user_one: dict, client: TestClient):
    """Deleting a conversation also removes all its messages (cascade)."""
    chat = client.post("/chats", json={"title": "To Delete"}, headers=user_one["headers"]).json()
    chat_id = chat["id"]

    # Add some messages
    client.post(
        f"/chats/{chat_id}/messages",
        json={"role": "user", "content": "Hello?"},
        headers=user_one["headers"],
    )
    client.post(
        f"/chats/{chat_id}/messages",
        json={"role": "assistant", "content": "Hi there!"},
        headers=user_one["headers"],
    )

    # Delete
    del_resp = client.delete(f"/chats/{chat_id}", headers=user_one["headers"])
    assert del_resp.status_code == 200

    # Conversation should be gone
    get_resp = client.get(f"/chats/{chat_id}", headers=user_one["headers"])
    assert get_resp.status_code == 404


def test_delete_conversation_does_not_delete_document(user_one: dict, client: TestClient):
    """Deleting a conversation must not delete the associated uploaded document."""
    # Upload a document
    pdf = {"file": ("keep_me.pdf", io.BytesIO(b"%PDF-1.4 keep"), "application/pdf")}
    doc = client.post("/documents/upload", files=pdf, headers=user_one["headers"]).json()
    doc_id = str(doc["id"])

    # Create chat and associate
    chat = client.post("/chats", json={"title": "Linked Chat"}, headers=user_one["headers"]).json()
    chat_id = chat["id"]
    client.post(
        f"/chats/{chat_id}/documents",
        json={"document_id": doc_id},
        headers=user_one["headers"],
    )

    # Delete conversation
    client.delete(f"/chats/{chat_id}", headers=user_one["headers"])

    # Document must still exist
    doc_resp = client.get(f"/documents/{doc_id}", headers=user_one["headers"])
    assert doc_resp.status_code == 200


# ---------------------------------------------------------------------------
# 7. Resume conversation — full detail with messages & documents
# ---------------------------------------------------------------------------

def test_resume_conversation_loads_full_history(user_one: dict, client: TestClient):
    """GET /chats/{id} returns all saved messages in chronological order."""
    # Create with a 'New Chat' title so auto-naming can fire on first message
    chat = client.post("/chats", headers=user_one["headers"]).json()
    chat_id = chat["id"]

    client.post(
        f"/chats/{chat_id}/messages",
        json={"role": "user", "content": "What is RAG?"},
        headers=user_one["headers"],
    )
    client.post(
        f"/chats/{chat_id}/messages",
        json={
            "role": "assistant",
            "content": "RAG stands for Retrieval-Augmented Generation.",
            "source_metadata": [{"source": "docs.pdf", "page": 1}],
        },
        headers=user_one["headers"],
    )
    client.post(
        f"/chats/{chat_id}/messages",
        json={"role": "user", "content": "Tell me more."},
        headers=user_one["headers"],
    )

    detail = client.get(f"/chats/{chat_id}", headers=user_one["headers"]).json()

    assert detail["id"] == chat_id
    # Auto-title: conversation started as 'New Chat' so the first user message renames it
    assert "What is RAG" in detail["title"]
    messages = detail["messages"]
    assert len(messages) == 3
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "What is RAG?"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["source_metadata"] is not None
    assert messages[2]["role"] == "user"


def test_resume_conversation_includes_attached_documents(user_one: dict, client: TestClient):
    """GET /chats/{id} includes documents attached to the conversation."""
    pdf = {"file": ("attached.pdf", io.BytesIO(b"%PDF-1.4 attached"), "application/pdf")}
    doc = client.post("/documents/upload", files=pdf, headers=user_one["headers"]).json()
    doc_id = str(doc["id"])

    chat = client.post("/chats", json={"title": "Doc Chat"}, headers=user_one["headers"]).json()
    chat_id = chat["id"]

    client.post(
        f"/chats/{chat_id}/documents",
        json={"document_id": doc_id},
        headers=user_one["headers"],
    )

    detail = client.get(f"/chats/{chat_id}", headers=user_one["headers"]).json()
    assert len(detail["documents"]) == 1
    assert detail["documents"][0]["original_filename"] == "attached.pdf"


# ---------------------------------------------------------------------------
# 8. Search conversations
# ---------------------------------------------------------------------------

def test_search_by_title(user_one: dict, client: TestClient):
    """Search term matching a title returns only that conversation."""
    client.post("/chats", json={"title": "Quantum Physics Notes"}, headers=user_one["headers"])
    client.post("/chats", json={"title": "Biology Lecture"}, headers=user_one["headers"])

    resp = client.get("/chats?search=Quantum", headers=user_one["headers"])
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["title"] == "Quantum Physics Notes"


def test_search_by_message_content(user_one: dict, client: TestClient):
    """Search term matching a message body returns the conversation containing it."""
    chat = client.post("/chats", json={"title": "GenChat"}, headers=user_one["headers"]).json()
    client.post(
        f"/chats/{chat['id']}/messages",
        json={"role": "user", "content": "Explain photosynthesis in detail"},
        headers=user_one["headers"],
    )
    other = client.post("/chats", json={"title": "Other"}, headers=user_one["headers"]).json()
    client.post(
        f"/chats/{other['id']}/messages",
        json={"role": "user", "content": "Tell me about Newton"},
        headers=user_one["headers"],
    )

    resp = client.get("/chats?search=photosynthesis", headers=user_one["headers"])
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert chat["id"] in ids
    assert other["id"] not in ids


def test_search_no_results_returns_empty_list(user_one: dict, client: TestClient):
    """A search term with no matches returns an empty list, not an error."""
    client.post("/chats", json={"title": "Something"}, headers=user_one["headers"])
    resp = client.get("/chats?search=xyzzy_no_match", headers=user_one["headers"])
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# 9. Combined search + category filter
# ---------------------------------------------------------------------------

def test_search_within_category(user_one: dict, client: TestClient):
    """When both search and category are provided, both filters apply."""
    c1 = client.post(
        "/chats", json={"title": "Neural Networks", "category": "Study"}, headers=user_one["headers"]
    ).json()
    c2 = client.post(
        "/chats", json={"title": "Neural Nets Dev", "category": "Development"}, headers=user_one["headers"]
    ).json()

    # Search "Neural" within "Study" category — should only return c1
    resp = client.get("/chats?search=Neural&category=Study", headers=user_one["headers"])
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert c1["id"] in ids
    assert c2["id"] not in ids


# ---------------------------------------------------------------------------
# 10. Cross-user isolation
# ---------------------------------------------------------------------------

def test_cross_user_cannot_rename(user_one: dict, user_two: dict, client: TestClient):
    """User Two cannot rename User One's conversation."""
    chat = client.post("/chats", json={"title": "Private"}, headers=user_one["headers"]).json()
    resp = client.patch(
        f"/chats/{chat['id']}",
        json={"title": "Hacked"},
        headers=user_two["headers"],
    )
    assert resp.status_code == 403


def test_cross_user_cannot_delete(user_one: dict, user_two: dict, client: TestClient):
    """User Two cannot delete User One's conversation."""
    chat = client.post("/chats", json={"title": "Private"}, headers=user_one["headers"]).json()
    resp = client.delete(f"/chats/{chat['id']}", headers=user_two["headers"])
    assert resp.status_code == 403


def test_cross_user_cannot_view_detail(user_one: dict, user_two: dict, client: TestClient):
    """User Two cannot view User One's conversation detail."""
    chat = client.post("/chats", json={"title": "Secret"}, headers=user_one["headers"]).json()
    resp = client.get(f"/chats/{chat['id']}", headers=user_two["headers"])
    assert resp.status_code == 403


def test_cross_user_conversations_not_in_list(user_one: dict, user_two: dict, client: TestClient):
    """User Two's conversation list never includes User One's conversations."""
    client.post("/chats", json={"title": "User1 Chat"}, headers=user_one["headers"])
    client.post("/chats", json={"title": "User2 Chat"}, headers=user_two["headers"])

    u2_list = client.get("/chats", headers=user_two["headers"]).json()
    u2_titles = [c["title"] for c in u2_list]
    assert "User2 Chat" in u2_titles
    assert "User1 Chat" not in u2_titles


# ---------------------------------------------------------------------------
# 11. Conversation detail contains category
# ---------------------------------------------------------------------------

def test_conversation_detail_includes_category(user_one: dict, client: TestClient):
    """GET /chats/{id} includes the category in its response."""
    chat = client.post(
        "/chats", json={"title": "DevWork", "category": "Development"}, headers=user_one["headers"]
    ).json()
    detail = client.get(f"/chats/{chat['id']}", headers=user_one["headers"]).json()
    assert detail["category"] == "Development"


# ---------------------------------------------------------------------------
# 12. Message count in list response
# ---------------------------------------------------------------------------

def test_message_count_increments_on_new_messages(user_one: dict, client: TestClient):
    """The message_count field in the list response reflects actual message count."""
    chat = client.post("/chats", json={"title": "Count Test"}, headers=user_one["headers"]).json()
    chat_id = chat["id"]

    # Initially zero
    list_resp = client.get("/chats", headers=user_one["headers"]).json()
    matched = next(c for c in list_resp if c["id"] == chat_id)
    assert matched["message_count"] == 0

    client.post(
        f"/chats/{chat_id}/messages",
        json={"role": "user", "content": "One"},
        headers=user_one["headers"],
    )
    client.post(
        f"/chats/{chat_id}/messages",
        json={"role": "assistant", "content": "Two"},
        headers=user_one["headers"],
    )

    list_resp2 = client.get("/chats", headers=user_one["headers"]).json()
    matched2 = next(c for c in list_resp2 if c["id"] == chat_id)
    assert matched2["message_count"] == 2
