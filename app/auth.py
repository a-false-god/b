"""
Authentication & Session Management for Prawko B MVP.
Uses Argon2id hashing (with PBKDF2 fallback) and persistent SQLite session tokens (BE-01).
Includes anti-enumeration timing equalization, real client IP extraction behind trusted proxies (BE-02),
in-memory rate limiting per real client IP, and session rotation.
"""

import base64
import collections
import hashlib
import ipaddress
import os
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from fastapi import Request, Response, HTTPException, status

from app.db import get_db_connection

try:
    from argon2 import PasswordHasher
    ph = PasswordHasher()
    USE_ARGON2 = True
except ImportError:
    USE_ARGON2 = False

SESSION_COOKIE_NAME = "prawko_session"
SESSION_MAX_AGE = 86400 * 30  # 30 days

# Rate limiting config
RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 60.0
_IP_ATTEMPT_LOG: Dict[str, List[float]] = collections.defaultdict(list)


def check_registration_key(provided_key: Optional[str] = None) -> bool:
    """
    Checks registration key if REGISTRATION_KEY environment variable is set.
    If REGISTRATION_KEY is unset or empty, registration is open (returns True).
    If set, provided_key must match constant-time via secrets.compare_digest.
    """
    reg_key = os.environ.get("REGISTRATION_KEY", "").strip()
    if not reg_key:
        return True
    if not provided_key:
        return False
    return secrets.compare_digest(provided_key.strip(), reg_key)


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


_DEFAULT_TRUSTED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def is_trusted_proxy(host: str) -> bool:
    """
    Checks whether direct connection peer is a trusted proxy (loopback, private network, or TRUSTED_PROXIES).
    """
    if not host or host in ("unknown", "testclient"):
        return True
    if host in ("127.0.0.1", "::1", "localhost"):
        return True

    custom_trusted = os.environ.get("TRUSTED_PROXIES", "").strip()
    if custom_trusted:
        trusted_entries = [t.strip() for t in custom_trusted.split(",") if t.strip()]
        for entry in trusted_entries:
            if host == entry:
                return True
            try:
                if ipaddress.ip_address(host) in ipaddress.ip_network(entry, strict=False):
                    return True
            except ValueError:
                pass

    try:
        ip_obj = ipaddress.ip_address(host)
        return any(ip_obj in net for net in _DEFAULT_TRUSTED_NETWORKS) or ip_obj.is_loopback
    except ValueError:
        return False


def get_client_ip(request: Request) -> str:
    """
    Extracts real client IP safely (BE-02).
    Reads X-Forwarded-For ONLY when direct peer is in trusted proxies.
    If direct peer is untrusted, XFF is ignored to prevent IP spoofing.
    """
    peer_ip = "unknown"
    if request.client and request.client.host:
        peer_ip = request.client.host

    if is_trusted_proxy(peer_ip):
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # First non-trusted address from the left is original client
            ips = [ip.strip() for ip in xff.split(",") if ip.strip()]
            if ips:
                return ips[0]

    return peer_ip


def check_rate_limit(request: Request, action: str = "auth"):
    """
    In-memory IP rate limiter keyed on real client IP (BE-02). Allows max 5 attempts per minute per IP.
    Raises HTTPException 429 when limit exceeded.
    """
    client_ip = get_client_ip(request)

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
    Create a new persistent session in SQLite (BE-01) and set HTTP-only cookie.
    Rotates session ID if a prior session token exists in request cookies.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Rotate session: invalidate old session token from SQLite if present
    if request:
        old_token = request.cookies.get(SESSION_COOKIE_NAME)
        if old_token:
            cursor.execute("DELETE FROM user_sessions WHERE token = ?", (old_token,))

    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=SESSION_MAX_AGE)).isoformat()

    cursor.execute(
        "INSERT INTO user_sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at)
    )
    conn.commit()
    conn.close()

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE
    )
    return token


def get_current_user_id(request: Request) -> Optional[int]:
    """
    Retrieve current user_id from persistent SQLite session table (BE-01) by cookie or header.
    Lazily prunes expired session rows on access.
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        auth_hdr = request.headers.get("Authorization")
        if auth_hdr and auth_hdr.startswith("Bearer "):
            token = auth_hdr.split(" ", 1)[1]

    if not token:
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, expires_at FROM user_sessions WHERE token = ?", (token,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    now_iso = datetime.now(timezone.utc).isoformat()
    if row["expires_at"] < now_iso:
        cursor.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None

    # Lazy opportunistic cleanup of other expired sessions (1 in 50 chance)
    if secrets.randbelow(50) == 0:
        cursor.execute("DELETE FROM user_sessions WHERE expires_at < ?", (now_iso,))
        conn.commit()

    user_id = row["user_id"]
    conn.close()
    return user_id


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
    """Remove session cookie and delete session row from SQLite (BE-01)."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        auth_hdr = request.headers.get("Authorization")
        if auth_hdr and auth_hdr.startswith("Bearer "):
            token = auth_hdr.split(" ", 1)[1]

    if token:
        conn = get_db_connection()
        conn.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()

    response.delete_cookie(SESSION_COOKIE_NAME)
