"""
Pytest suite for Dashboard V3: Today's progress, Exam readiness, Streak, and Weak Points.
"""

import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app
from app.db import get_db_connection, init_db

client = TestClient(app)


def test_dashboard_v3_structure():
    """Verify Dashboard V3 JSON payload includes today, readiness, streak, and weak_points structures."""
    init_db()

    username = f"v3_user_{uuid.uuid4().hex[:6]}"
    client.post("/auth/register", json={"login": username, "password": "password123"})
    login_res = client.post("/auth/login", json={"login": username, "password": "password123"})
    cookies = login_res.cookies

    res = client.get("/api/dashboard", cookies=cookies)
    assert res.status_code == 200
    data = res.json()

    # 1. Today Card
    assert "today" in data
    today = data["today"]
    assert "today_answers" in today
    assert today["daily_goal"] == 20
    assert "repeats_today" in today
    assert "new_today" in today
    assert "est_minutes" in today
    assert "formatted_date" in today
    assert isinstance(today["formatted_date"], str)

    # 2. Exam Readiness Card
    assert "readiness" in data
    readiness = data["readiness"]
    assert "score" in readiness
    assert readiness["max_score"] == 74
    assert readiness["pass_threshold"] == 68
    assert "score_delta" in readiness
    assert "points_needed" in readiness
    assert "exams_this_week" in readiness

    # 3. Weekly Streak Card
    assert "streak" in data
    streak = data["streak"]
    assert "current_streak" in streak
    assert "max_streak" in streak
    assert "avg_daily_questions" in streak
    assert "week_days" in streak
    assert len(streak["week_days"]) == 7
    day_labels = [d["day_short"] for d in streak["week_days"]]
    assert day_labels == ["pn", "wt", "śr", "cz", "pt", "so", "nd"]

    # 4. Weak Points Card
    assert "weak_points" in data
    weak_points = data["weak_points"]
    assert isinstance(weak_points, list)
    assert len(weak_points) >= 1
    for wp in weak_points:
        assert "axis_b" in wp
        assert "label" in wp
        assert "accuracy_pct" in wp
        assert "error_count" in wp


def test_dashboard_v3_answers_and_exam_propagation():
    """Verify answering questions and taking exams updates Dashboard V3 state accurately."""
    init_db()

    username = f"v3_prop_{uuid.uuid4().hex[:6]}"
    client.post("/auth/register", json={"login": username, "password": "password123"})
    login_res = client.post("/auth/login", json={"login": username, "password": "password123"})
    cookies = login_res.cookies
    user_id = login_res.json()["user_id"]

    # Get sample Cat-B question
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, correct FROM questions WHERE categories LIKE '%\"B\"%' LIMIT 1")
    q_row = cursor.fetchone()
    q_id = q_row["id"]
    correct_ans = q_row["correct"].strip().upper()
    conn.close()

    # Submit an answer today
    ans_res = client.post(
        "/api/answers",
        json={
            "question_id": q_id,
            "chosen": correct_ans,
            "time_ms": 3000,
            "session_id": "v3_sess_1"
        },
        cookies=cookies
    )
    assert ans_res.status_code == 200

    dash_res = client.get("/api/dashboard", cookies=cookies)
    assert dash_res.status_code == 200
    dash = dash_res.json()

    assert dash["today"]["today_answers"] >= 1
    assert dash["today"]["new_today"] >= 1

    # Submit an exam check
    exam_res = client.post(
        "/api/exam/submit",
        json={
            "answers": [{"question_id": q_id, "chosen": correct_ans, "time_ms": 2500}],
            "time_seconds": 30
        },
        cookies=cookies
    )
    assert exam_res.status_code == 200

    dash_after_exam = client.get("/api/dashboard", cookies=cookies).json()
    assert dash_after_exam["readiness"]["exams_this_week"] >= 1
