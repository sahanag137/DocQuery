"""
API Router package for DocQuery.
"""

from app.api.auth import router as auth_router, get_current_user
from app.api.users import router as users_router
from app.api.documents import router as documents_router
from app.api.chats import router as chats_router
from app.api.export import router as export_router

__all__ = [
    "auth_router",
    "users_router",
    "documents_router",
    "chats_router",
    "export_router",
    "get_current_user",
]
