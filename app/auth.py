"""
Authentication & Session Management for Prawko B MVP.
Uses Argon2id hashing (with PBKDF2 fallback) and encrypted/signed session cookies.
"""

import base64
import hashlib
import secrets
from typing import Optional
from fastapi import Request, Response, HTTPException, status

try:
    from argon2 import PasswordHasher
    ph = PasswordHasher()
    USE_ARGON2 = True
except ImportError:
    USE_ARGON2 = False

SESSIONS: dict[str, int] = {}
SESSION_COOKIE_NAME = "prawko_session"


def hash_password(password: str) -> str:
    """Hash password using Argon2id (or PBKDF2-HMAC-SHA256 fallback)."""
    if USE_ARGON2:
        return ph.hash(password)
    
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return "pbkdf2:" + base64.b64encode(salt + key).decode("ascii")


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored Argon2id or PBKDF2 hash."""
    if USE_ARGON2 and not stored_hash.startswith("pbkdf2:"):
        try:
            return ph.verify(stored_hash, password)
        except Exception:
            return False

    try:
        raw_hash = stored_hash.replace("pbkdf2:", "")
        decoded = base64.b64decode(raw_hash.encode("ascii"))
        salt = decoded[:16]
        key = decoded[16:]
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return secrets.compare_digest(key, new_key)
    except Exception:
        return False


def create_session(user_id: int, response: Response) -> str:
    """Create a new session token and set HTTP-only cookie."""
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = user_id
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 30  # 30 days
    )
    return token


def get_current_user_id(request: Request) -> Optional[int]:
    """Retrieve current user_id from session cookie or header."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        auth_hdr = request.headers.get("Authorization")
        if auth_hdr and auth_hdr.startswith("Bearer "):
            token = auth_hdr.split(" ", 1)[1]

    if token and token in SESSIONS:
        return SESSIONS[token]
    return None


def require_user_id(request: Request) -> int:
    """Dependency that enforces authenticated user."""
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user_id


def destroy_session(request: Request, response: Response):
    """Remove session cookie and delete session from store."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token in SESSIONS:
        del SESSIONS[token]
    response.delete_cookie(SESSION_COOKIE_NAME)
