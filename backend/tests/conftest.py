"""
conftest.py

Pytest configuration, fixtures, and test database setup.
Uses an isolated in-memory or temporary SQLite database so test runs never
affect production data.
"""

from pathlib import Path
import tempfile
from typing import Dict, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.database.base import Base
from app.database.connection import get_db
from app.main import app


@pytest.fixture(scope="session")
def test_temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for test storage."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Override storage directories in settings for tests
        orig_doc_dir = settings.DOCUMENTS_DIR
        orig_avatar_dir = settings.AVATARS_DIR
        settings.DOCUMENTS_DIR = tmp_path / "documents"
        settings.AVATARS_DIR = tmp_path / "avatars"
        settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        settings.AVATARS_DIR.mkdir(parents=True, exist_ok=True)

        yield tmp_path

        settings.DOCUMENTS_DIR = orig_doc_dir
        settings.AVATARS_DIR = orig_avatar_dir


@pytest.fixture(scope="function")
def db_session(test_temp_dir: Path) -> Generator[Session, None, None]:
    """
    Create a clean, isolated SQLite test database for each test function.
    """
    test_db_path = test_temp_dir / f"test_{tempfile.mktemp().split('tmp')[-1]}.db"
    test_engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()
        if test_db_path.exists():
            test_db_path.unlink()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient with overridden get_db dependency.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def user_one(client: TestClient) -> Dict:
    """Register and authenticate user 1, returning token and auth header."""
    signup_data = {
        "full_name": "Alice Tester",
        "email": "alice@example.com",
        "password": "Password123!",
    }
    resp = client.post("/auth/signup", json=signup_data)
    assert resp.status_code == 201

    login_resp = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    user_info = login_resp.json()["user"]

    return {
        "user": user_info,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture(scope="function")
def user_two(client: TestClient) -> Dict:
    """Register and authenticate user 2 for cross-user permission tests."""
    signup_data = {
        "full_name": "Bob Tester",
        "email": "bob@example.com",
        "password": "Password456!",
    }
    resp = client.post("/auth/signup", json=signup_data)
    assert resp.status_code == 201

    login_resp = client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "Password456!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    user_info = login_resp.json()["user"]

    return {
        "user": user_info,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }
