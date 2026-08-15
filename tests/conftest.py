"""
Root Pytest Configuration for Prawko B.
Resets authentication rate limit state between test functions to avoid test bleed.
Ensures SQLite test database is seeded from data/questions_full.json in fresh checkouts / CI.
"""

import json
import sqlite3
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.auth import reset_rate_limits
from app.db import init_db


@pytest.fixture(scope="session", autouse=True)
def ensure_test_database():
    """Ensure data/prawko.sqlite exists and is seeded from questions_full.json if missing."""
    db_path = PROJECT_ROOT / "data" / "prawko.sqlite"
    if not db_path.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
        json_path = PROJECT_ROOT / "data" / "questions_full.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                questions = json.load(f)

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            mig_001 = PROJECT_ROOT / "tools" / "migrate_001.sql"
            if mig_001.exists():
                cursor.executescript(mig_001.read_text(encoding="utf-8"))

            from tools.seed_taxonomy import TAXONOMY_SEED
            cursor.executemany(
                "INSERT OR REPLACE INTO taxonomy_values (axis, value, definition) VALUES (?, ?, ?)",
                TAXONOMY_SEED
            )

            for q in questions:
                cursor.execute(
                    """
                    INSERT INTO questions (
                      id, lp, scope, points, type, correct, media, media_kind,
                      categories, status, q_pl, a_pl, b_pl, c_pl,
                      q_en, a_en, b_en, c_en, q_de, a_de, b_de, c_de,
                      q_ua, a_ua, b_ua, c_ua, pjm_q
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        q["id"], q["lp"], q["scope"], q["points"], q["type"], q["correct"], q["media"], q["media_kind"],
                        json.dumps(q["categories"]), q["status"], q["q_pl"], q["a_pl"], q["b_pl"], q["c_pl"],
                        q["q_en"], q["a_en"], q["b_en"], q["c_en"], q["q_de"], q["a_de"], q["b_de"], q["c_de"],
                        q["q_ua"], q["a_ua"], q["b_ua"], q["c_ua"], q["pjm_q"]
                    )
                )
            conn.commit()
            conn.close()

            from scripts.classify_questions import classify_questions
            classify_questions(limit=0, dry_run=False)

            from scripts.generate_explanations import batch_generate_explanations
            batch_generate_explanations(dry_run=False, limit=0, force_recompute=False)

    init_db()


@pytest.fixture(autouse=True)
def reset_auth_rate_limits_each_test():
    """Ensure rate limit memory is clean for each test."""
    reset_rate_limits()
    yield
    reset_rate_limits()

