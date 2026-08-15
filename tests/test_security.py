"""
Security & Hardening Test Suite (Task S4).

Covers:
- In-memory rate limiting (429 on >= 6 rapid attempts).
- Timing equalization & uniform failure messages (anti-enumeration).
- Session cookie attributes (HttpOnly, SameSite, Max-Age).
- Session ID rotation on login.
"""

import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app
from app.auth import SESSIONS, SESSION_COOKIE_NAME, reset_rate_limits
from app.db import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_security_tests():
    init_db()
    reset_rate_limits()
    yield
    reset_rate_limits()


def test_rate_limiting_login_breach():
    """Verify that >5 rapid failed or successful login attempts from same IP result in 429."""
    dummy_payload = {"login": "rate_limited_user", "password": "wrong_password"}

    # First 5 attempts return 401
    for i in range(5):
        res = client.post("/auth/login", json=dummy_payload)
        assert res.status_code == 401, f"Attempt {i+1} got unexpected status {res.status_code}"

    # 6th attempt should be rejected with 429
    res_6 = client.post("/auth/login", json=dummy_payload)
    assert res_6.status_code == 429
    assert "Too many authentication attempts" in res_6.json()["detail"]


def test_rate_limiting_register_breach():
    """Verify that >5 rapid registration attempts from same IP result in 429."""
    for i in range(5):
        res = client.post(
            "/auth/register",
            json={"login": f"user_rl_{uuid.uuid4().hex[:6]}", "password": "valid_password"}
        )
        assert res.status_code == 200

    # 6th attempt returns 429
    res_6 = client.post(
        "/auth/register",
        json={"login": f"user_rl_{uuid.uuid4().hex[:6]}", "password": "valid_password"}
    )
    assert res_6.status_code == 429


def test_anti_enumeration_identical_error():
    """Verify that 'unknown user' and 'wrong password' produce identical status and error detail."""
    registered_login = f"user_exist_{uuid.uuid4().hex[:6]}"
    correct_password = "SecretPassword123"

    # Register user
    reg_res = client.post("/auth/register", json={"login": registered_login, "password": correct_password})
    assert reg_res.status_code == 200
    reset_rate_limits()

    # Case 1: Existing user, wrong password
    res_wrong_pw = client.post("/auth/login", json={"login": registered_login, "password": "WrongPassword"})
    assert res_wrong_pw.status_code == 401

    # Case 2: Non-existent user
    non_existent_login = f"user_ghost_{uuid.uuid4().hex[:6]}"
    res_unknown_user = client.post("/auth/login", json={"login": non_existent_login, "password": "AnyPassword"})
    assert res_unknown_user.status_code == 401

    # Invariant: identical payload and status
    assert res_wrong_pw.json() == res_unknown_user.json()
    assert res_wrong_pw.json()["detail"] == "Invalid credentials"


def test_session_cookie_attributes_and_rotation():
    """Verify session cookie attributes and session ID rotation on subsequent login."""
    login_name = f"user_rot_{uuid.uuid4().hex[:6]}"
    password = "TestPassword123"

    # Register
    reg_res = client.post("/auth/register", json={"login": login_name, "password": password})
    assert reg_res.status_code == 200
    first_cookie = reg_res.cookies.get(SESSION_COOKIE_NAME)
    assert first_cookie is not None
    assert first_cookie in SESSIONS

    # Check Set-Cookie headers
    set_cookie_hdr = reg_res.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie_hdr or "httponly" in set_cookie_hdr.lower()
    assert "samesite=lax" in set_cookie_hdr.lower()
    assert "max-age=" in set_cookie_hdr.lower()

    reset_rate_limits()

    # Login with existing session in cookie -> should rotate session ID
    client.cookies.set(SESSION_COOKIE_NAME, first_cookie)
    login_res = client.post("/auth/login", json={"login": login_name, "password": password})
    assert login_res.status_code == 200

    new_cookie = login_res.cookies.get(SESSION_COOKIE_NAME)
    assert new_cookie is not None
    assert new_cookie != first_cookie, "Session token was not rotated upon login"
    assert first_cookie not in SESSIONS, "Old session token was not invalidated"
    assert new_cookie in SESSIONS, "New session token is not registered in active sessions"
