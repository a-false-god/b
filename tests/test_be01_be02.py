"""
Test Suite for Audit Items BE-01 (Persistent SQLite Sessions) & BE-02 (Real Client IP Behind Proxy).
"""

import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app
from app.auth import (
    SESSION_COOKIE_NAME,
    get_client_ip,
    is_trusted_proxy,
    reset_rate_limits,
    RATE_LIMIT_MAX_ATTEMPTS,
)
from app.db import init_db, get_db_connection

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_tests():
    init_db()
    reset_rate_limits()
    yield
    reset_rate_limits()


# ============================================================================
# BE-01: Persistent SQLite Sessions Tests
# ============================================================================

def test_session_survives_restart_and_persists_in_sqlite():
    """Verify that a session token stored in user_sessions persists and authenticates across fresh clients."""
    username = f"persist_user_{uuid.uuid4().hex[:6]}"
    password = "SafePassword123!"

    # 1. Register user
    reg_res = client.post("/auth/register", json={"login": username, "password": password})
    assert reg_res.status_code == 200
    token = reg_res.cookies.get(SESSION_COOKIE_NAME)
    assert token is not None

    # Verify session row exists in SQLite table
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, expires_at FROM user_sessions WHERE token = ?", (token,))
    row = cursor.fetchone()
    conn.close()
    assert row is not None, "Session row was not found in SQLite user_sessions table"
    assert row["user_id"] == reg_res.json()["user_id"]

    # 2. Simulate complete application/client restart (create brand new TestClient instance)
    fresh_client = TestClient(app)
    fresh_client.cookies.set(SESSION_COOKIE_NAME, token)

    # 3. Fresh client should be authenticated against questions API
    q_res = fresh_client.get("/api/questions?limit=1")
    assert q_res.status_code == 200
    q_items = q_res.json()
    assert len(q_items) > 0
    sample_q = q_items[0]

    # 4. Fresh client should be able to submit answers
    ans_res = fresh_client.post(
        "/api/answers",
        json={
            "question_id": sample_q["id"],
            "chosen": sample_q.get("correct", "T") or "T",
            "time_ms": 3500,
            "session_id": "test_persist_sess"
        }
    )
    assert ans_res.status_code == 200
    assert "is_correct" in ans_res.json()


def test_expired_session_in_sqlite_is_rejected_and_pruned():
    """Verify that an expired session in SQLite returns 401 and is pruned from the database."""
    username = f"exp_user_{uuid.uuid4().hex[:6]}"
    password = "SafePassword123!"

    reg_res = client.post("/auth/register", json={"login": username, "password": password})
    assert reg_res.status_code == 200
    token = reg_res.cookies.get(SESSION_COOKIE_NAME)

    # Manually tamper with expiration timestamp in SQLite to simulate an expired session
    past_timestamp = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    conn = get_db_connection()
    conn.execute("UPDATE user_sessions SET expires_at = ? WHERE token = ?", (past_timestamp, token))
    conn.commit()
    conn.close()

    # Attempt request with expired session cookie
    fresh_client = TestClient(app)
    fresh_client.cookies.set(SESSION_COOKIE_NAME, token)
    res = fresh_client.post(
        "/api/answers",
        json={"question_id": 1, "chosen": "T", "time_ms": 3000, "session_id": "exp_sess"}
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Authentication required"

    # Verify pruned from DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE token = ?", (token,))
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 0, "Expired session was not pruned from user_sessions table"


def test_logout_deletes_session_row():
    """Verify that logging out removes the session row from SQLite."""
    username = f"logout_user_{uuid.uuid4().hex[:6]}"
    password = "SafePassword123!"

    login_res = client.post("/auth/register", json={"login": username, "password": password})
    assert login_res.status_code == 200
    token = login_res.cookies.get(SESSION_COOKIE_NAME)

    # Logout
    logout_client = TestClient(app)
    logout_client.cookies.set(SESSION_COOKIE_NAME, token)
    logout_res = logout_client.post("/auth/logout")
    assert logout_res.status_code == 200

    # Verify session row is gone
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE token = ?", (token,))
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 0, "Session row still exists after logout"


# ============================================================================
# BE-02: Real Client IP Behind Proxy & Rate Limiting Tests
# ============================================================================

def test_is_trusted_proxy_helpers():
    """Verify trusted proxy detection for loopback, private networks, and untrusted public IPs."""
    assert is_trusted_proxy("127.0.0.1") is True
    assert is_trusted_proxy("::1") is True
    assert is_trusted_proxy("localhost") is True
    assert is_trusted_proxy("10.0.4.15") is True
    assert is_trusted_proxy("172.18.0.2") is True
    assert is_trusted_proxy("192.168.1.100") is True
    assert is_trusted_proxy("testclient") is True

    # Untrusted public IPs
    assert is_trusted_proxy("203.0.113.195") is False
    assert is_trusted_proxy("8.8.8.8") is False
    assert is_trusted_proxy("1.1.1.1") is False


def test_trusted_proxy_reads_x_forwarded_for():
    """Behind a trusted proxy (e.g. Caddy on loopback/LAN), rate limiter keys on the forwarded client IP."""
    reset_rate_limits()
    real_ip_a = "198.51.100.11"
    real_ip_b = "198.51.100.22"

    # Rapid requests from IP A through trusted proxy
    for i in range(5):
        res = client.post(
            "/auth/login",
            json={"login": "non_existent_a", "password": "bad_password"},
            headers={"X-Forwarded-For": f"{real_ip_a}, 10.0.0.1"}
        )
        assert res.status_code == 401

    # 6th request from IP A should get 429
    res_a_blocked = client.post(
        "/auth/login",
        json={"login": "non_existent_a", "password": "bad_password"},
        headers={"X-Forwarded-For": f"{real_ip_a}, 10.0.0.1"}
    )
    assert res_a_blocked.status_code == 429
    assert "Too many authentication attempts" in res_a_blocked.json()["detail"]

    # IP B through same proxy should NOT be blocked
    res_b_ok = client.post(
        "/auth/login",
        json={"login": "non_existent_b", "password": "bad_password"},
        headers={"X-Forwarded-For": f"{real_ip_b}, 10.0.0.1"}
    )
    assert res_b_ok.status_code == 401, "Distinct client IP behind proxy was incorrectly rate limited"


def test_untrusted_peer_ignores_spoofed_x_forwarded_for():
    """Verify that an untrusted direct peer cannot spoof client IP via X-Forwarded-For header."""
    from unittest.mock import MagicMock
    from fastapi import Request

    # Create mock request with untrusted public client host
    mock_request = MagicMock(spec=Request)
    mock_request.client.host = "203.0.113.195"  # Public untrusted peer
    mock_request.headers.get.return_value = "8.8.8.8, 1.1.1.1"  # Spoofed XFF header

    # get_client_ip must return the direct untrusted peer, NOT the spoofed header
    extracted_ip = get_client_ip(mock_request)
    assert extracted_ip == "203.0.113.195"
