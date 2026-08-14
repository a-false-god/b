#!/usr/bin/env python3
"""
Utility script to clear demo/testing user data prior to live user session start.
Clears answer_events, exam_checks, user_skill, skill_history, question_stats, and users.
Preserves questions, taxonomy, taxonomy_values, and question_classification data.
"""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "prawko.sqlite"


def clear_demo_data():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM answer_events;")
    cursor.execute("DELETE FROM exam_checks;")
    cursor.execute("DELETE FROM user_skill;")
    cursor.execute("DELETE FROM skill_history;")
    cursor.execute("DELETE FROM question_stats;")
    cursor.execute("DELETE FROM users;")

    conn.commit()
    conn.close()

    print("Demo/test data wiped successfully. Application is ready for fresh real-user registration and learning sessions.")


if __name__ == "__main__":
    clear_demo_data()
