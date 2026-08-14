#!/usr/bin/env python3
import sqlite3
from pathlib import Path

MEDIA_DIR = Path("c:/Users/idsid/Documents/GitHub/b/media")
DB_PATH = Path("c:/Users/idsid/Documents/GitHub/b/data/prawko.sqlite")
REPORT_PATH = Path("c:/Users/idsid/Documents/GitHub/b/data/audit_fuzzy.txt")

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, media, media_kind
        FROM questions
        WHERE categories LIKE '%"B"%' AND media IS NOT NULL AND TRIM(media) != ''
    """)
    rows = cursor.fetchall()
    conn.close()

    all_media_files = {f.name.lower(): f.name for f in MEDIA_DIR.glob("*")}

    matches = []
    missing = []

    for q_id, media_name, media_kind in rows:
        stem = Path(media_name).stem.lower()
        exact = media_name.lower()
        mp4_name = f"{stem}.mp4"

        found = False
        if exact in all_media_files:
            found = True
        elif mp4_name in all_media_files:
            found = True
        else:
            # Check for any file with same stem
            for f_lower, f_real in all_media_files.items():
                if Path(f_lower).stem == stem:
                    found = True
                    break

        if not found:
            missing.append((q_id, media_name, media_kind))

    report = f"Fuzzy Audit: Total Missing: {len(missing)}\n"
    for item in missing:
        report += f"  - Q#{item[0]}: {item[1]} (kind: {item[2]})\n"

    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)

if __name__ == "__main__":
    main()
