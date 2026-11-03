"""
main.py

Entry point for the DocQuery FastAPI backend application.
Configures CORS, database schema initialization on startup, and registers
all API routers for Authentication, User Profiles, Documents, Chat History,
and PDF Export.

Run locally with:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chats import router as chats_router
from app.api.documents import router as documents_router
from app.api.export import router as export_router
from app.api.users import router as users_router
from app.core.config import settings
from app.database.connection import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Initializes database tables and runs non-destructive SQLite migrations.
    """
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="RAG-Based Documentation Question Answering System - Modules 1 to 4 Backend",
    version=settings.VERSION,
    lifespan=lifespan,
)

# Configure Cross-Origin Resource Sharing (CORS) for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(documents_router)
app.include_router(chats_router)
app.include_router(export_router)


@app.get("/")
def read_root() -> Dict[str, str]:
    """
    Root endpoint.
    Confirms that the API is up and reachable.
    """
    return {
        "message": "DocQuery API is running",
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.get("/health")
def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    Used by monitoring tools or deployment platforms to verify service health.
    """
    return {
        "status": "healthy",
        "service": "DocQuery Backend",
    }
