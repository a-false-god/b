"""
Pytest suite for Milestones M4 and M5 of Prawko B MVP.

Acceptance criteria:
- M4: Classifier script dry-run & batch run, review queue GET & POST override.
- M5: Panel analizy analytics endpoints (all 6 metrics: question, axis, option, reason, hesitation, coverage).
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
from scripts.classify_questions import classify_questions

client = TestClient(app)


def test_m4_classifier_dry_run_and_execution():
    # 1. Dry run classification on 10 questions
    results = classify_questions(limit=10, dry_run=True)
    assert len(results) == 10
    for r in results:
        assert "question_id" in r
        assert "axis_a" in r["classification"]
        assert "axis_b" in r["classification"]
        assert "axis_c" in r["classification"]
        assert 0.0 <= r["classification"]["confidence"] <= 1.0

    # 2. Batch classification commit on 20 questions
    results_commit = classify_questions(limit=20, dry_run=False)
    assert len(results_commit) == 20

    # Verify database insertion
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM question_classification WHERE source = 'llm'")
    count = cursor.fetchone()[0]
    conn.close()
    assert count > 0, "LLM classifications should be written to database."


def test_m4_review_queue_and_manual_override():
    # 1. Fetch review queue items
    res = client.get("/api/classification/review?limit=5")
    assert res.status_code == 200
    queue = res.json()
    assert isinstance(queue, list)

    if queue:
        sample_q = queue[0]
        q_id = sample_q["id"]

        # 2. Override classification manually
        override_payload = {
            "axis_a": "zastosowanie",
            "axis_b": "pierwszenstwo",
            "axis_c": ["brak_pulapki"],
            "action": "override"
        }
        post_res = client.post(f"/api/classification/{q_id}", json=override_payload)
        assert post_res.status_code == 200
        assert post_res.json()["source"] == "manual"

        # 3. Verify manual override in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM question_classification WHERE question_id = ? AND axis = 'A' AND source = 'manual'", (q_id,))
        row = cursor.fetchone()
        conn.close()
        assert row is not None
        assert row["value"] == "zastosowanie"


def test_m5_all_six_analytics():
    # Register and login user for analytics testing
    uname = f"analytics_user_{uuid.uuid4().hex[:6]}"
    reg_resp = client.post("/auth/register", json={"login": uname, "password": "pass"})
    login_resp = client.post("/auth/login", json={"login": uname, "password": "pass"})
    cookies = login_resp.cookies
    user_id = login_resp.json()["user_id"]

    # Seed some answer events for analytics verification
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, type FROM questions WHERE type = 'ABC' LIMIT 1")
    abc_row = cursor.fetchone()
    abc_id = abc_row["id"]

    cursor.execute("SELECT id FROM questions WHERE scope = 'PODSTAWOWY' LIMIT 1")
    tn_row = cursor.fetchone()
    tn_id = tn_row["id"]

    # Log 1 slip, 1 mistake, 1 hesitation, 1 confused option for this user
    cursor.execute("INSERT INTO answer_events (user_id, question_id, chosen, is_correct, time_ms, session_id, created_at) VALUES (?, ?, 'A', 0, 3000, 'sess_an', '2026-08-01 09:00:00')", (user_id, abc_id))
    cursor.execute("INSERT INTO answer_events (user_id, question_id, chosen, is_correct, time_ms, session_id, created_at) VALUES (?, ?, 'B', 0, 12000, 'sess_an', '2026-08-01 09:05:00')", (user_id, abc_id))
    cursor.execute("INSERT INTO answer_events (user_id, question_id, chosen, is_correct, time_ms, session_id, created_at) VALUES (?, ?, 'T', 1, 18000, 'sess_an', '2026-08-01 10:00:00')", (user_id, tn_id))
    cursor.execute("INSERT INTO answer_events (user_id, question_id, chosen, is_correct, time_ms, session_id, created_at) VALUES (?, ?, 'T', 1, 4000, 'sess_an', '2026-08-02 10:00:00')", (user_id, tn_id))
    conn.commit()
    conn.close()

    # 1. Hardest questions (by=question)
    r1 = client.get("/api/analytics/errors?by=question", cookies=cookies)
    assert r1.status_code == 200
    assert "data" in r1.json()

    # 2. Errors per axis (by=axisA)
    r2 = client.get("/api/analytics/errors?by=axisA", cookies=cookies)
    assert r2.status_code == 200
    assert "data" in r2.json()

    # 3. Confused options (by=option)
    r3 = client.get("/api/analytics/errors?by=option", cookies=cookies)
    assert r3.status_code == 200
    assert "data" in r3.json()

    # 4. Reason split
    r4 = client.get("/api/analytics/reason", cookies=cookies)
    assert r4.status_code == 200
    reason = r4.json()
    assert "slips" in reason
    assert "mistakes" in reason
    assert "uncertainty" in reason
    assert reason["slips"] >= 1
    assert reason["mistakes"] >= 1
    assert reason["uncertainty"] >= 1

    # 5. Hesitation
    r5 = client.get("/api/analytics/hesitation", cookies=cookies)
    assert r5.status_code == 200
    hes = r5.json()
    assert "hesitation_candidates" in hes
    assert hes["count"] >= 1

    # 6. Coverage
    r6 = client.get("/api/analytics/coverage", cookies=cookies)
    assert r6.status_code == 200
    cov = r6.json()
    assert "total_cat_b" in cov
    assert "never_seen" in cov
    assert "seen" in cov
    assert "mastered" in cov
    assert cov["seen"] >= 2
    assert cov["mastered"] >= 1
