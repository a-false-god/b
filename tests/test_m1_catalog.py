"""
Pytest suite for Milestone M1 of Prawko B MVP.

Acceptance criteria for M1:
- Pytest proves 3 698 total questions in database
- Cat-B questions = 2 135
- Zero missing correct answers
- Schema tables & indexes exist
- Taxonomy seeded
- Re-import preserves question_classification & answer_events
"""

import json
import sqlite3
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
DB_PATH = PROJECT_ROOT / "data" / "prawko.sqlite"


@pytest.fixture(scope="module")
def db_conn():
    assert DB_PATH.exists(), f"Database file {DB_PATH} must exist for M1 testing."
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.close()


def test_migration_and_tables_exist(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    expected_tables = {
        "questions",
        "users",
        "taxonomy_values",
        "question_classification",
        "answer_events"
    }

    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

    # Check indexes on answer_events
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='answer_events'")
    indexes = {row[0] for row in cursor.fetchall()}
    assert "idx_events_user" in indexes
    assert "idx_events_question" in indexes


def test_total_question_count(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM questions")
    total_count = cursor.fetchone()[0]
    assert total_count == 3698, f"Expected 3,698 questions, found {total_count}"


def test_category_b_count(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT categories FROM questions")
    rows = cursor.fetchall()

    b_count = 0
    for (cats_json,) in rows:
        try:
            cats = json.loads(cats_json) if cats_json else []
            if "B" in cats:
                b_count += 1
        except Exception:
            pass

    assert b_count == 2135, f"Expected 2,135 category B questions, found {b_count}"


def test_zero_missing_correct(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM questions WHERE correct IS NULL OR TRIM(correct) = ''")
    missing_count = cursor.fetchone()[0]
    assert missing_count == 0, f"Expected 0 missing correct answers, found {missing_count}"


def test_taxonomy_seeded(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT axis, COUNT(*) FROM taxonomy_values GROUP BY axis")
    axis_counts = dict(cursor.fetchall())

    assert axis_counts.get("A", 0) == 4, f"Expected 4 Axis A values, found {axis_counts.get('A')}"
    assert axis_counts.get("B", 0) == 8, f"Expected 8 Axis B values, found {axis_counts.get('B')}"
    assert axis_counts.get("C", 0) == 4, f"Expected 4 Axis C values, found {axis_counts.get('C')}"


def test_reimport_diff_safety(db_conn):
    cursor = db_conn.cursor()

    # Get a sample question id
    cursor.execute("SELECT id FROM questions LIMIT 1")
    q_id = cursor.fetchone()[0]

    # Insert dummy user & dummy classification & dummy answer event
    cursor.execute("INSERT OR IGNORE INTO users (id, login, password_hash) VALUES (99999, 'testuser', 'hash')")
    cursor.execute("INSERT OR REPLACE INTO question_classification (question_id, axis, value, confidence, source) VALUES (?, 'A', 'pamiec', 0.9, 'manual')", (q_id,))
    cursor.execute("INSERT INTO answer_events (user_id, question_id, chosen, is_correct, time_ms, session_id) VALUES (99999, ?, 'T', 1, 3000, 'sess1')", (q_id,))
    db_conn.commit()

    # Re-import test
    from tools.import_catalog import import_questions_to_db
    sample_update = [{
        "id": q_id,
        "lp": q_id,
        "scope": "PODSTAWOWY",
        "points": 3,
        "type": "TN",
        "correct": "T",
        "media": None,
        "media_kind": "none",
        "categories": json.dumps(["B"]),
        "status": "active",
        "q_pl": "Pytanie testowe updated",
        "a_pl": None, "b_pl": None, "c_pl": None,
        "q_en": None, "a_en": None, "b_en": None, "c_en": None,
        "q_de": None, "a_de": None, "b_de": None, "c_de": None,
        "q_ua": None, "a_ua": None, "b_ua": None, "c_ua": None,
        "pjm_q": None
    }]

    import_questions_to_db(sample_update, DB_PATH)

    # Verify existing classification and event remain intact
    cursor.execute("SELECT COUNT(*) FROM question_classification WHERE question_id = ?", (q_id,))
    assert cursor.fetchone()[0] >= 1, "Question classification was modified or removed on re-import!"

    cursor.execute("SELECT COUNT(*) FROM answer_events WHERE question_id = ?", (q_id,))
    assert cursor.fetchone()[0] >= 1, "Answer events were modified or removed on re-import!"


def test_migration_008_secondary_indexes(db_conn):
    """Verify that migration 008 indexes are created and present in SQLite schema."""
    from app.db import init_db
    init_db()
    cursor = db_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    all_indexes = {row[0] for row in cursor.fetchall()}

    assert "idx_qc_source" in all_indexes, "idx_qc_source missing from SQLite indexes"
    assert "idx_questions_scope_points" in all_indexes, "idx_questions_scope_points missing from SQLite indexes"
    assert "idx_events_user_qid_id" in all_indexes, "idx_events_user_qid_id missing from SQLite indexes"

