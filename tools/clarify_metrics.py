#!/usr/bin/env python3
"""
Clarify & Pin Metric Definitions for Prawko B.

Resolution of Historical Drift (1 941 vs 1 789 vs 1 566):
--------------------------------------------------------------------------------
- 1 941: Media references in Category B (ALL records, including pending verification).
  SQL: SELECT COUNT(*) FROM questions WHERE categories LIKE '%"B"%' AND media IS NOT NULL AND TRIM(media) != '';

- 1 789:
  A) Distinct media filenames across ALL Category B records (1 789 unique files):
     SQL: SELECT COUNT(DISTINCT media) FROM questions WHERE categories LIKE '%"B"%' AND media IS NOT NULL AND TRIM(media) != '';
  B) Total media references in Category B ACTIVE pool (1 789 references):
     SQL: SELECT COUNT(*) FROM questions WHERE categories LIKE '%"B"%' AND (status IS NULL OR status != 'pending') AND media IS NOT NULL AND TRIM(media) != '';

- 1 566: Distinct media filenames referenced in Category B ACTIVE pool (1 566 unique files):
  SQL: SELECT COUNT(DISTINCT media) FROM questions WHERE categories LIKE '%"B"%' AND (status IS NULL OR status != 'pending') AND media IS NOT NULL AND TRIM(media) != '';
--------------------------------------------------------------------------------
"""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "prawko.sqlite"


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Total database questions
    sql_total = "SELECT COUNT(*) FROM questions"
    cursor.execute(sql_total)
    total_db = cursor.fetchone()[0]

    # 2. Total active Cat-B questions
    sql_cat_b = "SELECT COUNT(*) FROM questions WHERE categories LIKE '%\"B\"%' AND (status IS NULL OR status != 'pending')"
    cursor.execute(sql_cat_b)
    cat_b_active = cursor.fetchone()[0]

    # 3. 1941: Media refs in all Cat-B
    sql_all_b_refs = "SELECT COUNT(*) FROM questions WHERE categories LIKE '%\"B\"%' AND media IS NOT NULL AND TRIM(media) != ''"
    cursor.execute(sql_all_b_refs)
    all_b_refs = cursor.fetchone()[0]

    # 4. 1789: Distinct media across all Cat-B
    sql_all_b_distinct = "SELECT COUNT(DISTINCT media) FROM questions WHERE categories LIKE '%\"B\"%' AND media IS NOT NULL AND TRIM(media) != ''"
    cursor.execute(sql_all_b_distinct)
    all_b_distinct = cursor.fetchone()[0]

    # 5. 1789: Active pool media references
    sql_active_refs = "SELECT COUNT(*) FROM questions WHERE categories LIKE '%\"B\"%' AND (status IS NULL OR status != 'pending') AND media IS NOT NULL AND TRIM(media) != ''"
    cursor.execute(sql_active_refs)
    active_refs = cursor.fetchone()[0]

    # 6. 1566: Distinct media in active pool
    sql_active_distinct = "SELECT COUNT(DISTINCT media) FROM questions WHERE categories LIKE '%\"B\"%' AND (status IS NULL OR status != 'pending') AND media IS NOT NULL AND TRIM(media) != ''"
    cursor.execute(sql_active_distinct)
    active_distinct = cursor.fetchone()[0]

    # 7. Media kind breakdown (Active)
    sql_video = "SELECT COUNT(*) FROM questions WHERE categories LIKE '%\"B\"%' AND (status IS NULL OR status != 'pending') AND media_kind = 'video'"
    cursor.execute(sql_video)
    video_count = cursor.fetchone()[0]

    sql_image = "SELECT COUNT(*) FROM questions WHERE categories LIKE '%\"B\"%' AND (status IS NULL OR status != 'pending') AND media_kind = 'image'"
    cursor.execute(sql_image)
    image_count = cursor.fetchone()[0]

    sql_no_media = "SELECT COUNT(*) FROM questions WHERE categories LIKE '%\"B\"%' AND (status IS NULL OR status != 'pending') AND (media IS NULL OR TRIM(media) = '')"
    cursor.execute(sql_no_media)
    no_media_count = cursor.fetchone()[0]

    conn.close()

    print("=" * 76)
    print("             PRAWKO B — CANONICAL METRIC DEFINITIONS & VALUES             ")
    print("=" * 76)
    print(f"\n1. Całkowita liczba pytań w bazie: {total_db}")
    print(f"   SQL: {sql_total}")

    print(f"\n2. Aktywna pula pytań kat. B: {cat_b_active}")
    print(f"   SQL: {sql_cat_b}")

    print("\n--- WYJAŚNIENIE METRYK MEDIALNYCH (1 941 / 1 789 / 1 566) ---")
    print(f"3. Odwołania do mediów (WSZYSTKIE pytania kat. B, w tym weryfikowane): {all_b_refs} [Metryka 1 941]")
    print(f"   SQL: {sql_all_b_refs}")

    print(f"4. Unikalne pliki mediów (WSZYSTKIE pytania kat. B):                 {all_b_distinct} [Metryka 1 789 (pliki)]")
    print(f"   SQL: {sql_all_b_distinct}")

    print(f"5. Odwołania do mediów w AKTYWNEJ puli kat. B:                        {active_refs} [Metryka 1 789 (odwołania)]")
    print(f"   SQL: {sql_active_refs}")

    print(f"6. Unikalne pliki mediów w AKTYWNEJ puli kat. B:                      {active_distinct} [Metryka 1 566]")
    print(f"   SQL: {sql_active_distinct}")

    print("\n--- STRUKTURA MEDIÓW W AKTYWNEJ PULI KAT. B ---")
    print(f"- Wideo (klipy MP4):   {video_count} (SQL: {sql_video})")
    print(f"- Zdjęcia (JPG/PNG):   {image_count} (SQL: {sql_image})")
    print(f"- Pytania tekstowe:    {no_media_count} (SQL: {sql_no_media})")
    print("=" * 76)


if __name__ == "__main__":
    main()
