
"""
main.py

Entry point for the DocQuery FastAPI backend application.
Configures CORS, database initialization, and API routers.
"""

from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chats import router as chats_router
from app.api.documents import router as documents_router
from app.api.export import router as export_router
from app.api.query import router as query_router
from app.api.users import router as users_router

from app.core.config import settings
from app.database.connection import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables when the application starts."""
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="RAG-Based Documentation Question Answering System",
    version=settings.VERSION,
    lifespan=lifespan,
)


# Configure CORS.
# Preserve existing configured origins and allow local Vite frontend.
cors_origins = list(settings.CORS_ORIGINS)

for origin in [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]:
    if origin not in cors_origins:
        cors_origins.append(origin)


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routers.
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(documents_router)
app.include_router(chats_router)
app.include_router(export_router)
app.include_router(query_router)


@app.get("/")
def read_root() -> Dict[str, str]:
    return {
        "message": "DocQuery API is running",
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {
        "status": "healthy",
        "service": "DocQuery Backend",
    }
