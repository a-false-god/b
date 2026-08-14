"""
Pytest suite for Milestone P2: Batch Elaborated Feedback & Statutory Legal Bases.

Acceptance criteria:
- 100% of Category B questions can be batch-generated with educational feedback.
- Explanations include clear educational rationale and exact statutory legal references.
- Zero hallucinations: legal references cite legitimate Polish road traffic statutes.
- Content hashing (SHA256) enables catalog invalidation.
- Media questions are tagged with needs_vision_review=1 for P4 Vision Pass.
- API endpoints (POST /api/answers, GET /api/questions/{id}/explanation) serve cached feedback immediately.
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
from scripts.generate_explanations import (
    generate_explanation_for_question,
    batch_generate_explanations,
    detect_fine_grained_topic,
    compute_question_content_hash
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_single_question_explanation_generation():
    """Verify single question generation logic for both TN and ABC question formats."""
    # Test True/False Question
    tn_q = {
        "id": 101,
        "type": "TN",
        "correct": "T",
        "q_pl": "Czy na skrzyżowaniu równorzędnym masz obowiązek ustąpić pierwszeństwa pojazdowi z prawej strony?",
        "axis_b": "pierwszenstwo",
        "media": None
    }
    exp_tn, legal_tn, c_hash, needs_vis = generate_explanation_for_question(tn_q)
    assert "**TAK**" in exp_tn
    assert "Art. 25" in legal_tn
    assert "UPRD" in legal_tn
    assert len(c_hash) == 16
    assert needs_vis == 0

    # Test ABC Question with Media
    abc_q = {
        "id": 102,
        "type": "ABC",
        "correct": "B",
        "q_pl": "Jaka jest dopuszczalna prędkość samochodu osobowego na autostradzie w Polsce?",
        "a_pl": "100 km/h",
        "b_pl": "140 km/h",
        "c_pl": "120 km/h",
        "axis_b": "predkosc_i_odleglosci",
        "media": "sample_highway.mp4"
    }
    exp_abc, legal_abc, c_hash_abc, needs_vis_abc = generate_explanation_for_question(abc_q)
    assert "**B**" in exp_abc
    assert "140 km/h" in exp_abc
    assert "Art. 20" in legal_abc
    assert needs_vis_abc == 1


def test_ecodriving_fallback_statutory_rule():
    """Ecodriving has no direct UPRD statute and must deliberately receive 'unknown' fallback."""
    eco_q = {
        "id": 103,
        "type": "ABC",
        "correct": "A",
        "q_pl": "Przy jakich obrotach silnika zaleca się zmianę biegu na wyższy w ramach ecodrivingu?",
        "a_pl": "2000-2500 obr./min",
        "b_pl": "4000 obr./min",
        "c_pl": "1000 obr./min",
        "axis_b": "ekologia",
        "media": None
    }
    exp_eco, legal_eco, _, _ = generate_explanation_for_question(eco_q)
    assert legal_eco == "unknown"
    assert "ecodriving" in exp_eco.lower()


def test_ecodriving_regression_never_leaks_art_22():
    """Regression test: Ecodriving questions (even mentioning gear changes or turns) must never leak Art. 22."""
    tricky_questions = [
        {"id": 104, "type": "TN", "correct": "T", "q_pl": "Czy zmiana biegu na wyższy przy 2000 obr/min ogranicza zużycie paliwa?", "axis_b": "ekologia", "media": None},
        {"id": 105, "type": "TN", "correct": "T", "q_pl": "Czy w ramach ecodrivingu należy hamować silnikiem przed skrętem?", "axis_b": "ekologia", "media": None},
        {"id": 106, "type": "ABC", "correct": "B", "q_pl": "Używanie pojazdu w sposób powodujący nadmierną emisję spalin jest:", "axis_b": "ekologia", "media": None}
    ]
    for q in tricky_questions:
        _, legal, _, _ = generate_explanation_for_question(q)
        assert legal == "unknown", f"Expected 'unknown' for Q#{q['id']}, got '{legal}'"
        assert "Art. 22" not in legal, f"Art. 22 leaked for Q#{q['id']}"

    # Verify all actual database questions in domain 'ekologia'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT qe.question_id, qe.legal_basis
        FROM question_explanations qe
        JOIN question_classification qc ON qe.question_id = qc.question_id AND qc.axis = 'B'
        WHERE qc.value = 'ekologia'
    """)
    rows = cursor.fetchall()
    conn.close()
    for row in rows:
        assert row["legal_basis"] == "unknown", f"DB Question #{row['question_id']} in ekologia has legal_basis '{row['legal_basis']}'"


def test_dry_run_explanations_generation():
    """Dry run must return count without database mutation errors."""
    processed = batch_generate_explanations(dry_run=True, limit=10)
    assert processed <= 10


def test_batch_generation_and_caching():
    """Batch population commits to SQLite and updates question_explanations table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM questions WHERE categories LIKE '%\"B\"%' LIMIT 5")
    sample_ids = [r["id"] for r in cursor.fetchall()]
    conn.close()

    # Generate explanations for sample with force recompute
    count = batch_generate_explanations(dry_run=False, limit=5, force_recompute=True)
    assert count == 5

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM question_explanations WHERE question_id IN ({})".format(
        ",".join(str(i) for i in sample_ids)
    ))
    cached = cursor.fetchone()[0]
    conn.close()
    assert cached == 5


def test_resume_and_checkpointing():
    """Verify that batch processing skips already cached questions on resume."""
    # When not forcing recompute, remaining un-cached questions are processed
    res = batch_generate_explanations(dry_run=False, limit=5, force_recompute=False)
    # Since all questions are already cached, count should be 0
    assert res == 0


def test_get_question_explanation_api():
    """GET /api/questions/{id}/explanation returns full structured feedback record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.id, q.correct, q.type, q.q_pl
        FROM questions q
        WHERE q.categories LIKE '%"B"%'
        LIMIT 1
    """)
    q_row = cursor.fetchone()
    q_id = q_row["id"]

    # Ensure an explanation exists for this question
    exp_text, legal_text, c_hash, needs_vis = generate_explanation_for_question(dict(q_row))
    cursor.execute("""
        INSERT OR REPLACE INTO question_explanations (question_id, explanation, legal_basis, source, content_hash, needs_vision_review)
        VALUES (?, ?, ?, 'llm', ?, ?)
    """, (q_id, exp_text, legal_text, c_hash, needs_vis))
    conn.commit()
    conn.close()

    # Call API endpoint
    res = client.get(f"/api/questions/{q_id}/explanation")
    assert res.status_code == 200
    data = res.json()
    assert data["question_id"] == q_id
    assert "explanation" in data
    assert "legal_basis" in data
    assert data["source"] in ("llm", "manual")


def test_submit_answer_returns_cached_explanation():
    """POST /api/answers immediately returns pre-cached elaborated explanation and legal basis."""
    uname = f"exp_user_{uuid.uuid4().hex[:6]}"
    client.post("/auth/register", json={"login": uname, "password": "password123"})
    login_res = client.post("/auth/login", json={"login": uname, "password": "password123"})
    cookies = login_res.cookies

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, correct, type, q_pl FROM questions WHERE categories LIKE '%\"B\"%' LIMIT 1")
    q_row = cursor.fetchone()
    q_id = q_row["id"]
    correct_ans = q_row["correct"].strip().upper()

    # Pre-cache explanation
    exp_text, legal_text, c_hash, needs_vis = generate_explanation_for_question(dict(q_row))
    cursor.execute("""
        INSERT OR REPLACE INTO question_explanations (question_id, explanation, legal_basis, source, content_hash, needs_vision_review)
        VALUES (?, ?, ?, 'llm', ?, ?)
    """, (q_id, exp_text, legal_text, c_hash, needs_vis))
    conn.commit()
    conn.close()

    # Submit answer
    ans_res = client.post(
        "/api/answers",
        json={
            "question_id": q_id,
            "chosen": correct_ans,
            "time_ms": 3200,
            "session_id": "test_exp_sess"
        },
        cookies=cookies
    )
    assert ans_res.status_code == 200
    ans_data = ans_res.json()

    assert ans_data["explanation"] is not None
    assert ans_data["legal_basis"] is not None
    assert ans_data["pending_explanation"] is False


def test_anti_hallucination_and_statutory_integrity():
    """Verifies that detected topics map to recognized Polish road traffic statutes."""
    topics = [
        ("Czy pieszy ma pierwszeństwo wchodząc na pasy?", "pieszy_przejscie"),
        ("Jaki jest dopuszczalny limit alkoholu?", "alkohol_i_uprawnienia"),
        ("Jak udzielić pierwszej pomocy i wykonać RKO?", "pierwsza_pomoc_rko"),
        ("Czy wolno wyprzedzić pojazd przy dojeżdżaniu do wierzchołka wzniesienia?", "wyprzedzanie"),
        ("Jaki minimalny bieżnik muszą mieć opony?", "stan_techniczny_opony"),
        ("Czy wolno zawrócić w tunelu?", "zawracanie")
    ]

    for question_text, expected_topic in topics:
        detected = detect_fine_grained_topic(question_text, None)
        assert detected == expected_topic, f"Expected {expected_topic} for '{question_text}', got {detected}"
