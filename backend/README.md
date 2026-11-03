# DocQuery - Backend (Modules 1–4)

Production-ready FastAPI backend for **DocQuery**, an AI-powered Document Question Answering System.

---

## Architecture & Features

This implementation encompasses **Modules 1 through 4**:

- **Module 1 – Authentication**: User registration with password strength verification, Argon2/Bcrypt password hashing, JWT Bearer authentication, session logout, password reset via secure single-use tokens, and protected routes.
- **Module 2 – User Profile & Settings**: View/update profile (name, email), avatar upload and retrieval, change password, delete account with file cleanup, and theme/language preference management.
- **Module 3 – Chat History**: Full conversation lifecycle (create, list, search, rename, archive/restore, delete), message persistence (user & assistant roles, citations/source metadata), chronological ordering, and PDF transcript export.
- **Module 4 – Document & PDF Management**: Secure upload and validation (PDF, TXT, MD), size limits, path-traversal protection, inline viewing with HTTP 206 Partial Content range requests, attachment downloads, and association with conversations.

---

## Directory Structure

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entry point, CORS, and routers
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py              # /auth endpoints (signup, login, reset, me)
│   │   ├── users.py             # /users endpoints (profile, avatar, password)
│   │   ├── documents.py         # /documents endpoints (upload, view, download)
│   │   ├── chats.py             # /chats endpoints (history, messages, doc associations)
│   │   └── export.py            # /chats/{id}/export endpoints (PDF transcript generation)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic Settings and paths
│   │   └── security.py          # Argon2 hashing, password complexity, JWT tokens
│   ├── database/
│   │   ├── __init__.py
│   │   ├── base.py              # DeclarativeBase and UTC timestamp helpers
│   │   ├── connection.py        # SQLAlchemy engine, session maker, get_db, auto-migration
│   │   ├── database.py          # Compatibility layer
│   │   └── models.py            # Compatibility layer
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py              # User model
│   │   ├── user_settings.py     # UserSettings model (theme, language)
│   │   ├── document.py          # Document model
│   │   ├── conversation.py      # Conversation model
│   │   ├── message.py           # Message model
│   │   ├── conversation_document.py  # ConversationDocument link model
│   │   ├── password_reset_token.py   # PasswordResetToken model
│   │   └── question.py          # Backward-compatibility model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py              # Pydantic auth schemas
│   │   ├── user.py              # Pydantic user and settings schemas
│   │   ├── document.py          # Pydantic document schemas
│   │   └── chat.py              # Pydantic conversation and message schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py      # Registration, auth, and token logic
│   │   ├── user_service.py      # Profile, avatar, password, and settings logic
│   │   ├── document_service.py  # File upload, storage, and retrieval logic
│   │   ├── chat_service.py      # Chat and message management logic
│   │   └── pdf_export_service.py# PDF transcript generator via fpdf2
│   └── utils/
│       ├── __init__.py
│       └── file_handler.py      # Filename sanitization, extension checks, range streaming
├── storage/
│   ├── documents/               # Uploaded documents directory
│   └── profile_pictures/        # Uploaded user avatars directory
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures and mock database setup
│   ├── test_auth.py             # Auth test suite
│   ├── test_users.py            # Users test suite
│   ├── test_documents.py        # Documents test suite
│   └── test_chats.py            # Chats and export test suite
├── .env.example
├── requirements.txt
└── README.md
```

---

## Setup & Running

### 1. Activate Virtual Environment

```cmd
cd C:\Users\admin\Downloads\DocQuery
.venv\Scripts\activate
```

### 2. Install Dependencies

```cmd
cd backend
pip install -r requirements.txt
```

### 3. Run Database Initialization (Automatic on startup)

Database tables and SQLite non-destructive migrations run automatically on startup via `init_db()`.
To run manually:

```cmd
python -c "from app.database.connection import init_db; init_db()"
```

### 4. Start the Backend Server

```cmd
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API interactive Swagger documentation will be available at:
`http://127.0.0.1:8000/docs`

---

## Running the Automated Test Suite

Run pytest inside the backend directory:

```cmd
cd backend
pytest -v
```
