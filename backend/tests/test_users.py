"""
test_users.py

Comprehensive tests for Module 2 (User Profile & Settings):
- View profile (/users/me)
- Update profile details and preferences (theme, language)
- Avatar upload, retrieval, and validation
- Change password with verification
- Account deletion
"""

import io
from fastapi.testclient import TestClient


def test_get_user_profile(user_one: dict, client: TestClient):
    """Verify that user profile and settings can be retrieved."""
    resp = client.get("/users/me", headers=user_one["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "alice@example.com"
    assert data["full_name"] == "Alice Tester"
    assert data["settings"]["theme"] == "light"
    assert data["settings"]["language"] == "en"


def test_update_profile_and_settings(user_one: dict, client: TestClient):
    """Verify updating name, email, theme, and language."""
    update_payload = {
        "full_name": "Alice Wonderland",
        "email": "alice_new@example.com",
        "theme": "dark",
        "language": "fr",
    }
    resp = client.put("/users/me", json=update_payload, headers=user_one["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Alice Wonderland"
    assert data["email"] == "alice_new@example.com"
    assert data["settings"]["theme"] == "dark"
    assert data["settings"]["language"] == "fr"


def test_avatar_upload_and_retrieval(user_one: dict, client: TestClient):
    """Verify uploading an avatar image and retrieving it."""
    # 1. Create a dummy PNG file in memory
    dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    files = {"file": ("avatar.png", io.BytesIO(dummy_png), "image/png")}

    upload_resp = client.post(
        "/users/me/avatar", files=files, headers=user_one["headers"]
    )
    assert upload_resp.status_code == 200
    assert upload_resp.json()["avatar_url"] is not None

    # 2. Retrieve avatar
    get_resp = client.get("/users/me/avatar", headers=user_one["headers"])
    assert get_resp.status_code == 200
    assert get_resp.headers["content-type"].startswith("image/png")
    assert len(get_resp.content) > 0


def test_avatar_invalid_extension(user_one: dict, client: TestClient):
    """Verify that non-image file formats are rejected for avatars."""
    bad_file = {"file": ("script.py", io.BytesIO(b"print('hack')"), "text/x-python")}
    resp = client.post("/users/me/avatar", files=bad_file, headers=user_one["headers"])
    assert resp.status_code == 400
    assert "unsupported file extension" in resp.json()["detail"].lower()


def test_change_password(user_one: dict, client: TestClient):
    """Verify changing password requires correct current password."""
    # Wrong current password
    bad_req = {
        "current_password": "WrongPassword!",
        "new_password": "NewSecretPassword123",
    }
    resp = client.put("/users/me/password", json=bad_req, headers=user_one["headers"])
    assert resp.status_code == 400

    # Correct current password
    good_req = {
        "current_password": "Password123!",
        "new_password": "NewSecretPassword123",
    }
    resp = client.put("/users/me/password", json=good_req, headers=user_one["headers"])
    assert resp.status_code == 200

    # Verify login with new password
    login_resp = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "NewSecretPassword123"},
    )
    assert login_resp.status_code == 200


def test_delete_user_account(user_one: dict, client: TestClient):
    """Verify account deletion prevents subsequent logins and removes profile."""
    resp = client.delete("/users/me", headers=user_one["headers"])
    assert resp.status_code == 200

    # Attempting to fetch /users/me should now fail
    me_resp = client.get("/users/me", headers=user_one["headers"])
    assert me_resp.status_code == 401
