"""
test_auth.py

Comprehensive tests for Module 1 (Authentication):
- User registration and password strength
- Duplicate email prevention
- User login and JWT access token issue
- Invalid credentials rejection
- Protected route enforcement
- Password reset token flow
- User logout
"""

import pytest
from fastapi.testclient import TestClient


def test_signup_successful(client: TestClient):
    """Verify that a new user can register successfully."""
    payload = {
        "full_name": "Charlie Chaplin",
        "email": "charlie@example.com",
        "password": "ValidPassword1",
    }
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "charlie@example.com"
    assert data["full_name"] == "Charlie Chaplin"
    assert "id" in data
    assert data["settings"]["theme"] == "light"


def test_signup_duplicate_email(client: TestClient):
    """Verify that registering with an existing email returns 400."""
    payload = {
        "full_name": "User One",
        "email": "duplicate@example.com",
        "password": "Password123",
    }
    client.post("/auth/signup", json=payload)

    # Attempt second registration with same email
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.parametrize(
    "weak_password,expected_error",
    [
        ("short1", "at least 8 characters"),
        ("nonumbershere", "at least one number"),
        ("1234567890", "at least one letter"),
    ],
)
def test_signup_password_strength_validation(
    client: TestClient, weak_password: str, expected_error: str
):
    """Verify that weak passwords are systematically rejected."""
    payload = {
        "full_name": "Weak Pass User",
        "email": f"weak_{weak_password}@example.com",
        "password": weak_password,
    }
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 400
    assert expected_error.lower() in response.json()["detail"].lower()


def test_login_successful_and_me(client: TestClient):
    """Verify login returns valid JWT token and /auth/me returns profile."""
    # 1. Register
    signup_data = {
        "full_name": "David Bowie",
        "email": "david@example.com",
        "password": "ZiggyStardust1",
    }
    client.post("/auth/signup", json=signup_data)

    # 2. Login
    login_data = {
        "email": "david@example.com",
        "password": "ZiggyStardust1",
    }
    resp = client.post("/auth/login", json=login_data)
    assert resp.status_code == 200
    token_data = resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    token = token_data["access_token"]

    # 3. Access /auth/me
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "david@example.com"
    assert me_resp.json()["full_name"] == "David Bowie"


def test_login_invalid_credentials(client: TestClient):
    """Verify that invalid passwords or unregistered emails return 401."""
    # Unknown user
    resp = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "Password123"},
    )
    assert resp.status_code == 401

    # Wrong password
    client.post(
        "/auth/signup",
        json={"full_name": "Real User", "email": "real@example.com", "password": "CorrectPass1"},
    )
    wrong_resp = client.post(
        "/auth/login",
        json={"email": "real@example.com", "password": "WrongPassword1"},
    )
    assert wrong_resp.status_code == 401


def test_protected_route_without_token(client: TestClient):
    """Verify that unauthorized requests to protected endpoints return 401."""
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_logout(user_one: dict, client: TestClient):
    """Verify that logout endpoint accepts authenticated request."""
    resp = client.post("/auth/logout", headers=user_one["headers"])
    assert resp.status_code == 200
    assert "logged out" in resp.json()["message"].lower()


def test_forgot_and_reset_password_flow(client: TestClient):
    """Test full forgot-password and reset-password workflow."""
    # 1. Register
    signup_data = {
        "full_name": "Reset Tester",
        "email": "reset@example.com",
        "password": "OldPassword123",
    }
    client.post("/auth/signup", json=signup_data)

    # 2. Request forgot password
    forgot_resp = client.post("/auth/forgot-password", json={"email": "reset@example.com"})
    assert forgot_resp.status_code == 200
    reset_token = forgot_resp.json().get("reset_token")
    assert reset_token is not None

    # 3. Reset password with valid token
    new_pass = "BrandNewPassword456"
    reset_resp = client.post(
        "/auth/reset-password",
        json={"token": reset_token, "new_password": new_pass},
    )
    assert reset_resp.status_code == 200

    # 4. Old password should now fail
    old_login = client.post(
        "/auth/login",
        json={"email": "reset@example.com", "password": "OldPassword123"},
    )
    assert old_login.status_code == 401

    # 5. New password should succeed
    new_login = client.post(
        "/auth/login",
        json={"email": "reset@example.com", "password": new_pass},
    )
    assert new_login.status_code == 200

    # 6. Reusing same token should fail
    reuse_resp = client.post(
        "/auth/reset-password",
        json={"token": reset_token, "new_password": "YetAnotherPassword789"},
    )
    assert reuse_resp.status_code == 400
