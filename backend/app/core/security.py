"""
security.py

Authentication and cryptographic utilities for DocQuery.
Provides Argon2 / Bcrypt password hashing, password strength validation,
JWT token creation / verification, and secure token generation for password resets.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets
from typing import Any, Dict, Optional, Tuple

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

# Initialize modern password hashers: Argon2 preferred, fallback to Bcrypt
_password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a hashed password."""
    if not plain_password or not hashed_password:
        return False
    try:
        return _password_hash.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate a secure Argon2 hash for the given plain-text password."""
    return _password_hash.hash(password)


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate that a password meets complexity standards:
    - At least 8 characters long
    - Contains at least one letter
    - Contains at least one digit
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    return True, ""


def create_access_token(
    subject: str | int,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject: The unique user identifier (e.g. user_id as string).
        expires_delta: Optional custom lifetime for the token.
        extra_claims: Optional extra dictionary of payload claims.

    Returns:
        Encoded JWT token string.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT access token.

    Args:
        token: The encoded JWT token string.

    Returns:
        The decoded payload dictionary, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except (jwt.PyJWTError, ValueError):
        return None


def generate_reset_token() -> Tuple[str, str]:
    """
    Generate a secure random token for password resets.

    Returns:
        A tuple of (raw_token, token_hash).
        The raw_token is provided to the user/email, while the token_hash
        is stored securely in the database.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)
    return raw_token, token_hash


def hash_token(raw_token: str) -> str:
    """Hash a token using SHA-256 for secure database lookup."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
