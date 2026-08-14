"""
Database layer for Prawko B MVP.
Connects to SQLite database at data/prawko.sqlite.
"""

import sqlite3
from pathlib import Path
from typing import Generator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "prawko.sqlite"


def get_db_connection() -> sqlite3.Connection:
    """Get a raw sqlite3 connection with Row factory."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def init_db():
    """Ensure migration scripts and taxonomy seeding are executed."""
    conn = get_db_connection()
    conn.execute("PRAGMA journal_mode = WAL")
    cursor = conn.cursor()

    migration_sql = PROJECT_ROOT / "tools" / "migrate_001.sql"
    if migration_sql.exists():
        cursor.executescript(migration_sql.read_text(encoding="utf-8"))

    migration_002_sql = PROJECT_ROOT / "tools" / "migrate_002.sql"
    if migration_002_sql.exists():
        sql_content = migration_002_sql.read_text(encoding="utf-8")
        for statement in sql_content.split(";"):
            stmt = statement.strip()
            if not stmt:
                continue
            try:
                cursor.execute(stmt)
            except sqlite3.OperationalError as e:
                # Ignore duplicate column name errors on repeated migrations
                if "duplicate column name" not in str(e).lower():
                    raise e

    migration_003_sql = PROJECT_ROOT / "tools" / "migrate_003.sql"
    if migration_003_sql.exists():
        cursor.executescript(migration_003_sql.read_text(encoding="utf-8"))

    migration_004_sql = PROJECT_ROOT / "tools" / "migrate_004.sql"
    if migration_004_sql.exists():
        cursor.executescript(migration_004_sql.read_text(encoding="utf-8"))

    migration_005_sql = PROJECT_ROOT / "tools" / "migrate_005.sql"
    if migration_005_sql.exists():
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='question_classification'")
        row = cursor.fetchone()
        if row and "'vision'" not in row[0]:
            cursor.executescript(migration_005_sql.read_text(encoding="utf-8"))
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vision_review (
                  question_id INTEGER PRIMARY KEY REFERENCES questions(id),
                  model TEXT NOT NULL,
                  n_frames INTEGER NOT NULL,
                  suggested_axis_a TEXT NOT NULL,
                  suggested_axis_b TEXT NOT NULL,
                  suggested_axis_c TEXT NOT NULL,
                  confidence REAL NOT NULL,
                  rationale TEXT,
                  decision TEXT NOT NULL CHECK (decision IN ('auto_accepted', 'auto_corrected', 'queued', 'skipped_no_media')),
                  created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vision_review_decision ON vision_review(decision)")

    # Ensure optional columns exist for schema evolution
    for col, col_type in [("content_hash", "TEXT"), ("needs_vision_review", "INTEGER DEFAULT 0")]:
        try:
            cursor.execute(f"ALTER TABLE question_explanations ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    conn.commit()
    conn.close()


