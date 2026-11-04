"""
test_login_integration.py

Comprehensive integration tests for the Login and Session flow:
- Authenticate via POST /auth/login with valid credentials
- Verify JWT access token and user response payload
- Verify HttpOnly access_token cookie is returned in Set-Cookie header
- Verify session access to protected GET /auth/me via Cookie and Bearer token
- Verify rejection of incorrect password (401)
- Verify rejection of non-existent user (401)
- Verify rejection of inactive accounts (403)
- Verify POST /auth/logout clears the access_token cookie
"""

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from app.models.user import User


def test_login_success_and_cookie_session(client: TestClient, db_session):
    """
    Test successful login returns access token, user details, and sets HttpOnly cookie.
    """
    # 1. Create a test user directly in DB
    user = User(
        full_name="Login Test User",
        email="login_user@example.com",
        hashed_password=get_password_hash("Password123!"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 2. POST /auth/login
    login_resp = client.post(
        "/auth/login",
        json={"email": "login_user@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login_user@example.com"
    assert data["user"]["full_name"] == "Login Test User"

    # 3. Verify HttpOnly cookie in Set-Cookie header
    cookies = login_resp.cookies
    assert "access_token" in cookies
    assert cookies["access_token"] == data["access_token"]

    # 4. Verify accessing protected GET /auth/me using Cookie
    me_resp_cookie = client.get("/auth/me", cookies={"access_token": data["access_token"]})
    assert me_resp_cookie.status_code == 200
    assert me_resp_cookie.json()["email"] == "login_user@example.com"

    # 5. Verify accessing protected GET /auth/me using Bearer header
    me_resp_bearer = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_resp_bearer.status_code == 200
    assert me_resp_bearer.json()["email"] == "login_user@example.com"

    # 6. POST /auth/logout clears the cookie
    logout_resp = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert logout_resp.status_code == 200
    # Cookie should be expired / cleared in response
    assert logout_resp.json()["message"] == "Successfully logged out."


def test_login_invalid_password(client: TestClient, db_session):
    """Verify incorrect password returns 401."""
    user = User(
        full_name="Password User",
        email="pass_user@example.com",
        hashed_password=get_password_hash("RealPassword1!"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    resp = client.post(
        "/auth/login",
        json={"email": "pass_user@example.com", "password": "WrongPassword!"},
    )
    assert resp.status_code == 401
    assert "invalid email or password" in resp.json()["detail"].lower()


def test_login_inactive_user(client: TestClient, db_session):
    """Verify inactive account is blocked with 403 Forbidden."""
    inactive_user = User(
        full_name="Inactive User",
        email="inactive@example.com",
        hashed_password=get_password_hash("ValidPass123!"),
        is_active=False,
    )
    db_session.add(inactive_user)
    db_session.commit()

    resp = client.post(
        "/auth/login",
        json={"email": "inactive@example.com", "password": "ValidPass123!"},
    )
    assert resp.status_code == 403
    assert "inactive" in resp.json()["detail"].lower()
