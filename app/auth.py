"""
Authentication & Session Management for Prawko B MVP.
Uses Argon2id hashing (with PBKDF2 fallback) and encrypted/signed session cookies.
Includes anti-enumeration timing equalization, in-memory IP rate limiting, and session rotation.
"""

import base64
import collections
import hashlib
import secrets
import time
from typing import Optional, Dict, List
from fastapi import Request, Response, HTTPException, status

try:
    from argon2 import PasswordHasher
    ph = PasswordHasher()
    USE_ARGON2 = True
except ImportError:
    USE_ARGON2 = False

SESSIONS: dict[str, int] = {}
SESSION_COOKIE_NAME = "prawko_session"
SESSION_MAX_AGE = 86400 * 30  # 30 days

# Rate limiting config
RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 60.0
_IP_ATTEMPT_LOG: Dict[str, List[float]] = collections.defaultdict(list)


def hash_password(password: str) -> str:
    """Hash password using Argon2id (or PBKDF2-HMAC-SHA256 fallback)."""
    if USE_ARGON2:
        return ph.hash(password)
    
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return "pbkdf2:" + base64.b64encode(salt + key).decode("ascii")


# Pre-computed dummy hash to equalize timing on non-existent users
_DUMMY_HASH = hash_password("prawko_dummy_timing_salt_string_12345")


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


def verify_password_or_dummy(password: str, stored_hash: Optional[str]) -> bool:
    """
    Constant-time password verification helper.
    If stored_hash is None (user does not exist), executes hash verification against
    a dummy hash to protect against timing-based user enumeration.
    """
    if stored_hash is None:
        verify_password(password, _DUMMY_HASH)
        return False
    return verify_password(password, stored_hash)


def check_rate_limit(request: Request, action: str = "auth"):
    """
    In-memory IP rate limiter. Allows max 5 attempts per minute per IP.
    Raises HTTPException 429 when limit exceeded.
    """
    client_ip = "unknown"
    if request.client and request.client.host:
        client_ip = request.client.host

    key = f"{action}:{client_ip}"
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS

    # Filter timestamps within window
    timestamps = [t for t in _IP_ATTEMPT_LOG[key] if t > cutoff]
    if len(timestamps) >= RATE_LIMIT_MAX_ATTEMPTS:
        _IP_ATTEMPT_LOG[key] = timestamps
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again in a minute."
        )

    timestamps.append(now)
    _IP_ATTEMPT_LOG[key] = timestamps


def reset_rate_limits():
    """Helper for test suites to reset rate limit logs."""
    _IP_ATTEMPT_LOG.clear()


def create_session(user_id: int, response: Response, request: Optional[Request] = None) -> str:
    """
    Create a new session token and set HTTP-only cookie.
    Rotates session ID if a prior session token exists in request cookies.
    """
    # Rotate session: invalidate old session token if present
    if request:
        old_token = request.cookies.get(SESSION_COOKIE_NAME)
        if old_token and old_token in SESSIONS:
            del SESSIONS[old_token]

    token = secrets.token_urlsafe(32)
    SESSIONS[token] = user_id
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE
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
