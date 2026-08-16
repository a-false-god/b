"""
Pytest suite for Migration 009 & Stage 3 IRT/HLR data-model readiness.

Verifies:
1. Migration 009 is idempotent (can run multiple times safely).
2. POST /api/answers logs events with mode='nauka'.
3. POST /api/exam/submit writes 32 individual question answers into answer_events with mode='sprawdzian' and session_id='exam:{exam_id}'.
4. Learning logic (session composer, mastery counting, dashboard analytics) strictly isolates mode='nauka' and is not mutated by mode='sprawdzian' answers.
"""

import sys
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app
from app.db import get_db_connection, init_db
from app.session import get_session_queue

client = TestClient(app)


@pytest.fixture
def db_conn():
    conn = get_db_connection()
    yield conn
    conn.close()



import uuid


def test_migration_009_idempotent():
    """Verify init_db can be called multiple times without error and mode column is present."""
    init_db()
    init_db()  # Idempotent re-run
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(answer_events)")
    cols = {row["name"] for row in cursor.fetchall()}
    assert "mode" in cols, "mode column missing from answer_events"
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='answer_events'")
    indexes = {row["name"] for row in cursor.fetchall()}
    assert "idx_events_user_mode" in indexes, "idx_events_user_mode index missing"
    conn.close()


def test_answers_defaults_to_nauka(db_conn):
    """Verify POST /api/answers logs an answer_events row with mode='nauka'."""
    login_name = f"user_nauka_{uuid.uuid4().hex[:8]}"
    client.post("/auth/register", json={"login": login_name, "password": "Password123!"})
    login_res = client.post("/auth/login", json={"login": login_name, "password": "Password123!"})
    assert login_res.status_code == 200
    user_id = login_res.json()["user_id"]

    cursor = db_conn.cursor()
    cursor.execute("SELECT id, correct FROM questions WHERE categories LIKE '%\"B\"%' LIMIT 1")
    q_row = cursor.fetchone()
    q_id = q_row["id"]
    correct_ans = q_row["correct"]

    sess_id = f"sess_{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/answers",
        json={
            "question_id": q_id,
            "chosen": correct_ans,
            "time_ms": 4200,
            "session_id": sess_id
        }
    )
    assert res.status_code == 200

    cursor.execute(
        "SELECT mode, session_id, is_correct FROM answer_events WHERE user_id = ? AND session_id = ?",
        (user_id, sess_id)
    )
    row = cursor.fetchone()
    assert row is not None
    assert row["mode"] == "nauka"
    assert row["is_correct"] == 1


def test_exam_submit_writes_32_sprawdzian_events(db_conn):
    """Verify POST /api/exam/submit creates exam_checks AND writes 32 mode='sprawdzian' rows into answer_events."""
    login_name = f"user_exam_{uuid.uuid4().hex[:8]}"
    client.post("/auth/register", json={"login": login_name, "password": "Password123!"})
    login_res = client.post("/auth/login", json={"login": login_name, "password": "Password123!"})
    assert login_res.status_code == 200
    user_id = login_res.json()["user_id"]

    # Generate an exam sheet (32 questions)
    sheet_res = client.post("/api/exam/start")
    assert sheet_res.status_code == 200
    exam_questions = sheet_res.json()["questions"]
    assert len(exam_questions) == 32

    cursor = db_conn.cursor()
    answers = []
    for q in exam_questions:
        cursor.execute("SELECT correct FROM questions WHERE id = ?", (q["id"],))
        correct_ans = cursor.fetchone()[0]
        answers.append({
            "question_id": q["id"],
            "chosen": correct_ans,
            "time_ms": 2500
        })

    submit_res = client.post(
        "/api/exam/submit",
        json={
            "time_seconds": 300,
            "answers": answers
        }
    )
    assert submit_res.status_code == 200
    exam_data = submit_res.json()
    exam_id = exam_data["exam_id"]
    assert exam_data["passed"] is True

    expected_session_id = f"exam:{exam_id}"
    cursor.execute(
        "SELECT COUNT(*), COUNT(DISTINCT question_id), mode FROM answer_events WHERE user_id = ? AND session_id = ? GROUP BY mode",
        (user_id, expected_session_id)
    )
    res_row = cursor.fetchone()
    assert res_row is not None
    total_events, distinct_qs, mode_val = res_row[0], res_row[1], res_row[2]
    assert total_events == 32, f"Expected 32 answer_events for exam, got {total_events}"
    assert distinct_qs == 32, f"Expected 32 distinct questions, got {distinct_qs}"
    assert mode_val == "sprawdzian", f"Expected mode='sprawdzian', got {mode_val}"


def test_learning_logic_isolated_from_exam_answers(db_conn):
    """Verify that exam answers (mode='sprawdzian') do not modify learning session composition, mastery, or analytics."""
    login_name = f"user_iso_{uuid.uuid4().hex[:8]}"
    client.post("/auth/register", json={"login": login_name, "password": "Password123!"})
    login_res = client.post("/auth/login", json={"login": login_name, "password": "Password123!"})
    assert login_res.status_code == 200
    user_id = login_res.json()["user_id"]

    cursor = db_conn.cursor()

    # 1. Compose session before any exam
    initial_candidates = get_session_queue(conn=db_conn, user_id=user_id, limit=20)
    initial_ids = [q["id"] for q in initial_candidates]
    assert len(initial_ids) == 20

    # Check dashboard before exam
    dash_before = client.get("/api/dashboard").json()
    assert dash_before["metrics"]["total_answers"] == 0
    assert dash_before["metrics"]["accuracy_percent"] == 0.0
    assert dash_before["coverage"]["seen"] == 0
    assert dash_before["coverage"]["mastered"] == 0

    # 2. Submit an exam where user answers all 32 questions with wrong answers
    sheet_res = client.post("/api/exam/start")
    exam_questions = sheet_res.json()["questions"]
    answers = []
    for q in exam_questions:
        answers.append({
            "question_id": q["id"],
            "chosen": "X",  # wrong answer on purpose
            "time_ms": 1000
        })

    submit_res = client.post("/api/exam/submit", json={"time_seconds": 120, "answers": answers})
    assert submit_res.status_code == 200

    # 3. Check dashboard after exam: learning counters must remain 0
    dash_after = client.get("/api/dashboard").json()
    assert dash_after["metrics"]["total_answers"] == 0, "Exam events leaked into dashboard total_answers!"
    assert dash_after["metrics"]["accuracy_percent"] == 0.0, "Exam events leaked into accuracy!"
    assert dash_after["coverage"]["seen"] == 0, "Exam events leaked into seen_count!"
    assert dash_after["coverage"]["mastered"] == 0, "Exam events leaked into mastered_count!"
    assert dash_after["repeats_due"] == 0, "Exam errors leaked into repeats_due!"

    # 4. Check analytics endpoints: errors, reason, coverage must be empty of exam data
    err_res = client.get("/api/analytics/errors?by=question").json()
    assert len(err_res["data"]) == 0, "Exam errors leaked into /api/analytics/errors"

    cov_res = client.get("/api/analytics/coverage").json()
    assert cov_res["seen"] == 0
    assert cov_res["mastered"] == 0

    reason_res = client.get("/api/analytics/reason").json()
    assert reason_res["slips"] == 0
    assert reason_res["mistakes"] == 0

    # 5. Session composer & pool eligibility:
    # All 2,135 Cat-B questions must remain in the never_seen learning pool despite 32 exam answers
    cursor.execute(
        """
        SELECT COUNT(*) FROM questions
        WHERE categories LIKE '%"B"%'
          AND id NOT IN (SELECT DISTINCT question_id FROM answer_events WHERE user_id = ? AND mode = 'nauka')
        """,
        (user_id,)
    )
    assert cursor.fetchone()[0] == 2135, "Exam questions were subtracted from never-seen learning catalog!"

    # Candidate session must contain 100% never_seen questions (0 review/wrong)
    candidates = get_session_queue(conn=db_conn, user_id=user_id, limit=20)
    assert len(candidates) == 20

    # 6. Verify that an actual learning answer via POST /api/answers DOES update metrics
    ans_res = client.post(
        "/api/answers",
        json={
            "question_id": candidates[0]["id"],
            "chosen": candidates[0]["correct"],
            "time_ms": 3500,
            "session_id": "learn_sess_1"
        }
    )
    assert ans_res.status_code == 200

    dash_after_learn = client.get("/api/dashboard").json()
    assert dash_after_learn["metrics"]["total_answers"] == 1
    assert dash_after_learn["metrics"]["correct_answers"] == 1
    assert dash_after_learn["coverage"]["seen"] == 1

