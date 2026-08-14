#!/usr/bin/env python3
"""
Clarify media metrics for Category B:
- 1 941: Total Question References in Category B active pool.
- 1 789: Total Unique / Distinct Media Files on disk.
"""

import sqlite3
import unicodedata
from pathlib import Path

PROJECT_B_ROOT = Path("c:/Users/idsid/Documents/GitHub/b")
MEDIA_DIR = PROJECT_B_ROOT / "media"
DB_PATH = PROJECT_B_ROOT / "data" / "prawko.sqlite"


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Total Question Media References for Category B
    cursor.execute("""
        SELECT id, media, media_kind, scope
        FROM questions
        WHERE categories LIKE '%"B"%' AND media IS NOT NULL AND TRIM(media) != ''
    """)
    all_refs = cursor.fetchall()

    # Distinct Media Filenames for Category B
    cursor.execute("""
        SELECT DISTINCT media
        FROM questions
        WHERE categories LIKE '%"B"%' AND media IS NOT NULL AND TRIM(media) != ''
    """)
    distinct_medias = cursor.fetchall()
    conn.close()

    total_refs = len(all_refs)
    total_distinct = len(distinct_medias)

    print("==================================================")
    print("           MEDIA METRICS CLARIFICATION            ")
    print("==================================================")
    print(f"1. Total Question References (Cat-B Pool):    {total_refs}")
    print(f"2. Unique / Distinct Media Filenames:        {total_distinct}")
    print("==================================================\n")


if __name__ == "__main__":
    main()
