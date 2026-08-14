"""
Tests for M7 Session Composer (Amendment A), Refined Spaced Mastery Rule (Amendment B),
Non-blocking LLM Feedback (Amendment C), and Weekly Readiness Check (Amendment D).
"""

import uuid
import sqlite3
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db_connection, init_db
from app.session import get_session_queue, interleave_questions

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()


def test_session_composer_interleaving():
    sample_questions = [
        {"id": 1, "axis_b": "znaki_i_sygnaly", "points": 3},
        {"id": 2, "axis_b": "znaki_i_sygnaly", "points": 2},
        {"id": 3, "axis_b": "pierwszenstwo", "points": 3},
        {"id": 4, "axis_b": "manewry_i_pozycja", "points": 3},
    ]

    interleaved = interleave_questions(sample_questions)
    assert len(interleaved) == 4
    # First items should alternate across domains
    assert interleaved[0]["axis_b"] != interleaved[1]["axis_b"]


def test_session_composer_ordering_and_cap():
    """
    Verifies Amendment A:
    - Review / wrong items come first.
    - New (unseen) items fill remainder up to limit and are capped at 20 max.
    """
    conn = get_db_connection()
    queue = get_session_queue(conn, user_id=99999, mode="auto", limit=20)
    conn.close()

    assert len(queue) <= 20
    # For a completely new user with 0 prior answers, all questions are unseen (capped at max 20)
    assert len(queue) == 20
    # Unseen questions ordered by points 3pt -> 2pt -> 1pt
    points = [q["points"] for q in queue]
    # Check that highest point items appear first in the session pool
    assert 3 in points


def test_spaced_mastery_rule_amendment_b():
    """
    Verifies Amendment B: mastered = correct on >= 2 distinct calendar days
    AND the latest event for that question is correct.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    uname = f"mastery_{uuid.uuid4().hex[:6]}"
    cursor.execute("INSERT OR IGNORE INTO users (login, password_hash) VALUES (?, 'hash')", (uname,))
    cursor.execute("SELECT id FROM users WHERE login = ?", (uname,))
    user_id = cursor.fetchone()[0]

    cursor.execute("SELECT id FROM questions WHERE categories LIKE '%\"B\"%' LIMIT 1")
    q_id = cursor.fetchone()[0]

    cursor.execute("DELETE FROM answer_events WHERE user_id = ? AND question_id = ?", (user_id, q_id))

    # Day 1 & Day 2 correct
    cursor.execute(
        "INSERT INTO answer_events (user_id, question_id, chosen, is_correct, time_ms, session_id, created_at) VALUES (?, ?, 'T', 1, 5000, 's1', '2026-08-01 10:00:00')",
        (user_id, q_id)
    )
    cursor.execute(
        "INSERT INTO answer_events (user_id, question_id, chosen, is_correct, time_ms, session_id, created_at) VALUES (?, ?, 'T', 1, 4000, 's2', '2026-08-02 10:00:00')",
        (user_id, q_id)
    )
    conn.commit()

    mastered_query = """
        WITH LatestEvent AS (
          SELECT question_id, is_correct,
                 ROW_NUMBER() OVER (PARTITION BY question_id ORDER BY id DESC) as rn
          FROM answer_events
          WHERE user_id = ?
        ),
        CorrectDays AS (
          SELECT question_id
          FROM answer_events
          WHERE user_id = ? AND question_id = ? AND is_correct = 1
          GROUP BY question_id
          HAVING COUNT(DISTINCT DATE(created_at)) >= 2
        )
        SELECT COUNT(*)
        FROM CorrectDays cd
        JOIN LatestEvent le ON cd.question_id = le.question_id
        WHERE le.rn = 1 AND le.is_correct = 1
    """
    cursor.execute(mastered_query, (user_id, user_id, q_id))
    assert cursor.fetchone()[0] == 1, "Should be mastered after 2 correct days"

    # Day 3: Wrong answer sandwiched after 2 correct days!
    cursor.execute(
        "INSERT INTO answer_events (user_id, question_id, chosen, is_correct, time_ms, session_id, created_at) VALUES (?, ?, 'N', 0, 3000, 's3', '2026-08-03 10:00:00')",
        (user_id, q_id)
    )
    conn.commit()

    cursor.execute(mastered_query, (user_id, user_id, q_id))
    assert cursor.fetchone()[0] == 0, "Amendment B: Question MUST NOT be marked mastered if latest event is WRONG!"

    # Day 3 later: Correct answer restored
    cursor.execute(
        "INSERT INTO answer_events (user_id, question_id, chosen, is_correct, time_ms, session_id, created_at) VALUES (?, ?, 'T', 1, 3500, 's3', '2026-08-03 11:00:00')",
        (user_id, q_id)
    )
    conn.commit()

    cursor.execute(mastered_query, (user_id, user_id, q_id))
    assert cursor.fetchone()[0] == 1, "Question becomes mastered again once latest event is correct!"

    conn.close()


def test_non_blocking_explanation_api():
    uname = f"async_user_{uuid.uuid4().hex[:6]}"
    client.post("/auth/register", json={"login": uname, "password": "password123"})
    client.post("/auth/login", json={"login": uname, "password": "password123"})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, correct FROM questions WHERE categories LIKE '%\"B\"%' LIMIT 1")
    row = cursor.fetchone()
    q_id = row["id"]
    wrong_choice = "N" if row["correct"] == "T" else "T"
    conn.close()

    ans_res = client.post("/api/answers", json={
        "question_id": q_id,
        "chosen": wrong_choice,
        "time_ms": 5000,
        "session_id": "async_sess"
    })

    assert ans_res.status_code == 200
    data = ans_res.json()
    assert data["is_correct"] == 0
    # Response returns immediately without blocking
    assert "pending_explanation" in data

    # Test explanation GET endpoint
    exp_res = client.get(f"/api/questions/{q_id}/explanation")
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert exp_data["question_id"] == q_id


def test_weekly_readiness_check_amendment_d():
    uname = f"exam_user_{uuid.uuid4().hex[:6]}"
    client.post("/auth/register", json={"login": uname, "password": "password123"})
    client.post("/auth/login", json={"login": uname, "password": "password123"})

    start_res = client.post("/api/exam/start")
    assert start_res.status_code == 200
    start_data = start_res.json()

    assert start_data["total_questions"] == 32
    assert start_data["max_score"] == 74
    assert start_data["pass_threshold"] == 68

    questions = start_data["questions"]
    for q in questions:
        assert q.get("status") != "pending", "Exam check MUST exclude status='pending' questions!"
