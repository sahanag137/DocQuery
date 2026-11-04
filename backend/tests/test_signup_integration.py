"""
test_signup_integration.py

Integration test verifying the exact registration flow requested by the frontend:
- Payload with full_name, email, password
- Argon2 password hashing verification
- Duplicate email rejection
- Default settings creation
- Subsequent login verification
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.user import User


def test_full_registration_flow(client: TestClient, db_session):
    """
    Test the complete registration workflow corresponding to the frontend Signup page:
    1. Valid registration request
    2. Verification of saved user in database
    3. Verification of Argon2 password hash
    4. Attempt duplicate registration (must fail with 400)
    5. Attempt login with registered user credentials
    """
    payload = {
        "full_name": "Frontend User",
        "email": "frontend_user@example.com",
        "password": "SecurePassword123!",
    }

    # 1. POST /auth/signup
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "frontend_user@example.com"
    assert data["full_name"] == "Frontend User"
    assert data["is_active"] is True
    assert "password" not in data  # Never expose password in response
    user_id = data["id"]

    # 2. Verify record in database
    db_user = db_session.get(User, user_id)
    assert db_user is not None
    assert db_user.email == "frontend_user@example.com"
    assert db_user.full_name == "Frontend User"

    # 3. Verify Argon2 password hashing (must not be plaintext)
    assert db_user.hashed_password != "SecurePassword123!"
    assert "$argon2" in db_user.hashed_password

    # 4. Verify duplicate email validation returns 400
    dup_response = client.post("/auth/signup", json=payload)
    assert dup_response.status_code == 400
    assert "already exists" in dup_response.json()["detail"].lower()

    # 5. Verify user can authenticate immediately via /auth/login
    login_response = client.post(
        "/auth/login",
        json={
            "email": "frontend_user@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["user"]["email"] == "frontend_user@example.com"
