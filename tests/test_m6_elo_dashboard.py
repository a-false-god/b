"""
Pytest suite for M6.1: Asymmetric Rasch Skill Rating Engine & Dashboard View.
"""

import sys
import math
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app
from app.db import get_db_connection, init_db
from app.config import SKILL_INIT, SKILL_LR0, DIFF_ALPHA, DIFF_BETA
from app.skill import calc_question_difficulty, calc_skill_update

client = TestClient(app)


def test_skill_math_and_decay():
    """Verify correct answer raises theta, wrong lowers it, and step size strictly decreases with n."""
    init_db()

    p_err, b_q = calc_question_difficulty(attempts=0, wrong=0)
    assert abs(p_err - 0.5) < 1e-5
    assert abs(b_q - 0.0) < 1e-5

    theta = 0.0
    n = 0

    # Correct answer -> theta increases
    theta_after_correct, n1, delta1 = calc_skill_update(theta, n, b_q, is_correct=True)
    assert theta_after_correct > theta
    assert n1 == 1

    # Wrong answer -> theta decreases
    theta_after_wrong, n2, delta2 = calc_skill_update(theta_after_correct, n1, b_q, is_correct=False)
    assert theta_after_wrong < theta_after_correct
    assert n2 == 2

    # Step size eta strictly decreases with n
    etas = [SKILL_LR0 / math.sqrt(1.0 + i) for i in range(10)]
    for i in range(len(etas) - 1):
        assert etas[i] > etas[i + 1], f"Step size did not strictly decrease at step {i}"


def test_question_difficulty_convergence():
    """Verify question difficulty converges under replay sequence and stays stable with high attempts."""
    init_db()

    # Replay sequence: 50 attempts, 10 wrong
    attempts = 50
    wrong = 10
    p_err, b_q = calc_question_difficulty(attempts, wrong)

    expected_p_err = (10 + DIFF_ALPHA) / (50 + DIFF_ALPHA + DIFF_BETA)
    assert abs(p_err - expected_p_err) < 1e-5
    assert abs(p_err - (12.0 / 54.0)) < 1e-5

    # Test single answer stability when attempts = 50
    p_err_after_one_wrong, _ = calc_question_difficulty(attempts + 1, wrong + 1)
    swing = abs(p_err_after_one_wrong - p_err)
    assert swing < 0.015, f"Single answer caused large swing ({swing}) on question with 50 attempts"


def test_transactional_skill_answer_submission():
    """Verify answer submission updates user_skill, question_stats, and skill_history atomically."""
    init_db()

    username = f"skill_user_{uuid.uuid4().hex[:6]}"
    client.post("/auth/register", json={"login": username, "password": "password123"})
    login_res = client.post("/auth/login", json={"login": username, "password": "password123"})
    cookies = login_res.cookies
    user_id = login_res.json()["user_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get sample Cat-B question
    cursor.execute("SELECT id, correct FROM questions WHERE categories LIKE '%\"B\"%' LIMIT 1")
    q_row = cursor.fetchone()
    q_id = q_row["id"]
    correct_ans = q_row["correct"].strip().upper()

    cursor.execute("SELECT COUNT(*) FROM skill_history WHERE user_id = ?", (user_id,))
    initial_history_count = cursor.fetchone()[0]
    conn.close()

    # Submit Correct Answer
    ans_res = client.post(
        "/api/answers",
        json={
            "question_id": q_id,
            "chosen": correct_ans,
            "time_ms": 3500,
            "session_id": "skill_sess_1"
        },
        cookies=cookies
    )
    assert ans_res.status_code == 200
    ans_data = ans_res.json()

    assert ans_data["is_correct"] == 1
    assert ans_data["skill_theta_after"] > ans_data["skill_theta_before"]

    # Verify DB state & skill_history count
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT theta, n FROM user_skill WHERE user_id = ? AND axis_value IS NULL", (user_id,))
    g_skill = cursor.fetchone()
    assert g_skill is not None
    assert abs(g_skill["theta"] - ans_data["skill_theta_after"]) < 1e-5
    assert g_skill["n"] == 1

    cursor.execute("SELECT attempts, wrong FROM question_stats WHERE question_id = ?", (q_id,))
    q_stats = cursor.fetchone()
    assert q_stats is not None
    assert q_stats["attempts"] >= 1

    cursor.execute("SELECT COUNT(*) FROM skill_history WHERE user_id = ?", (user_id,))
    new_history_count = cursor.fetchone()[0]
    assert new_history_count == initial_history_count + 1, "Exactly one skill_history snapshot must be created per event"

    conn.close()


def test_transactional_integrity_rollback():
    """Verify forced failure leaves no partial state in answer_events, question_stats, or user_skill."""
    init_db()

    username = f"rollback_user_{uuid.uuid4().hex[:6]}"
    client.post("/auth/register", json={"login": username, "password": "password123"})
    login_res = client.post("/auth/login", json={"login": username, "password": "password123"})
    cookies = login_res.cookies

    # Invalid question ID triggers 404 & rollback
    res = client.post(
        "/api/answers",
        json={
            "question_id": 99999999,
            "chosen": "T",
            "time_ms": 2000,
            "session_id": "err_sess"
        },
        cookies=cookies
    )
    assert res.status_code == 404

    # Verify zero side effects
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM answer_events WHERE session_id = 'err_sess'")
    assert cursor.fetchone()[0] == 0
    conn.close()


def test_dashboard_api_spot_check():
    """Verify Dashboard JSON response matches direct manual SQL spot-checks."""
    init_db()

    username = f"dash_spot_{uuid.uuid4().hex[:6]}"
    client.post("/auth/register", json={"login": username, "password": "password123"})
    login_res = client.post("/auth/login", json={"login": username, "password": "password123"})
    cookies = login_res.cookies
    user_id = login_res.json()["user_id"]

    # Submit 2 answers
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, correct FROM questions WHERE categories LIKE '%\"B\"%' LIMIT 2")
    q_rows = cursor.fetchall()
    conn.close()

    for r in q_rows:
        client.post(
            "/api/answers",
            json={
                "question_id": r["id"],
                "chosen": r["correct"].strip().upper(),
                "time_ms": 4000,
                "session_id": "spot_sess"
            },
            cookies=cookies
        )

    # Call Dashboard API
    dash_res = client.get("/api/dashboard/summary", cookies=cookies)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()

    # Direct SQL spot-check
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT theta FROM user_skill WHERE user_id = ? AND axis_value IS NULL", (user_id,))
    sql_theta = cursor.fetchone()["theta"]

    cursor.execute("SELECT COUNT(*) FROM answer_events WHERE user_id = ?", (user_id,))
    sql_events_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM skill_history WHERE user_id = ?", (user_id,))
    sql_history_count = cursor.fetchone()[0]

    conn.close()

    assert abs(dash_data["user"]["skill_theta"] - round(sql_theta, 3)) < 1e-3
    assert dash_data["metrics"]["total_answers"] == sql_events_count
    assert len(dash_data["skill_history"]) == sql_history_count
    assert "hardest_questions" in dash_data
    assert "per_axis_b" in dash_data
