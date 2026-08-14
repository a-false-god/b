"""
Pytest suite for Milestone M2 of Prawko B MVP.

Acceptance criteria for M2:
- Auth (register, login, logout) works cleanly.
- POST /api/answers enforces auth and returns 401 if unauthenticated.
- POST /api/answers computes is_correct against questions.correct.
- 100% of answer events are logged in answer_events table.
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import uuid
from app.main import app
from app.db import get_db_connection

client = TestClient(app)


def test_auth_flow():
    uname = f"m2_user_{uuid.uuid4().hex[:6]}"
    # 1. Register
    reg_resp = client.post("/auth/register", json={"login": uname, "password": "password123"})
    assert reg_resp.status_code == 200
    data = reg_resp.json()
    assert "user_id" in data
    assert data["login"] == uname

    # 2. Login
    login_resp = client.post("/auth/login", json={"login": uname, "password": "password123"})
    assert login_resp.status_code == 200
    assert "prawko_session" in login_resp.cookies

    # 3. Logout
    logout_resp = client.post("/auth/logout")
    assert logout_resp.status_code == 200


def test_unauthenticated_answer_rejected():
    # Unauthenticated answer submission MUST return 401 Unauthorized
    unauth_resp = client.post(
        "/api/answers",
        json={"question_id": 1, "chosen": "T", "time_ms": 3000, "session_id": "anon"}
    )
    assert unauth_resp.status_code == 401
    assert unauth_resp.json()["detail"] == "Authentication required"


def test_answer_submission_and_event_logging():
    uname = f"ans_user_{uuid.uuid4().hex[:6]}"
    # Register & login
    client.post("/auth/register", json={"login": uname, "password": "pass"})
    login_resp = client.post("/auth/login", json={"login": uname, "password": "pass"})
    cookies = login_resp.cookies

    # Get a sample question from database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, correct FROM questions LIMIT 1")
    q_row = cursor.fetchone()
    q_id = q_row["id"]
    correct_ans = q_row["correct"]
    conn.close()

    sess_id = f"sess_m2_{uuid.uuid4().hex[:6]}"
    # Submit correct answer
    ans_resp = client.post(
        "/api/answers",
        json={"question_id": q_id, "chosen": correct_ans, "time_ms": 4500, "session_id": sess_id},
        cookies=cookies
    )
    assert ans_resp.status_code == 200
    res_data = ans_resp.json()
    assert res_data["is_correct"] == 1
    assert res_data["chosen"] == correct_ans

    # Submit incorrect answer
    wrong_ans = "N" if correct_ans == "T" else ("T" if correct_ans == "N" else ("B" if correct_ans == "A" else "A"))
    ans_resp2 = client.post(
        "/api/answers",
        json={"question_id": q_id, "chosen": wrong_ans, "time_ms": 9000, "session_id": sess_id},
        cookies=cookies
    )
    assert ans_resp2.status_code == 200
    res_data2 = ans_resp2.json()
    assert res_data2["is_correct"] == 0

    # Verify 100% logged in answer_events table
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM answer_events WHERE question_id = ? AND session_id = ?", (q_id, sess_id))
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 2, f"Expected 2 answer events logged, found {count}"
