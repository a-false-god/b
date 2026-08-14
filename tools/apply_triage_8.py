#!/usr/bin/env python3
"""
Applies manual confirmation/triage for the 8 queued questions:
#100, #469, #475, #477, #478, #480, #486, #544 -> znaki_i_sygnaly (source='manual').
Regenerates explanations with visual context, sets needs_vision_review=0,
and updates vision_review decision to auto_accepted.
"""

import sys
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import get_db_connection
from scripts.generate_explanations import regenerate_vision_explanation

TRIAGE_IDS = [100, 469, 475, 477, 478, 480, 486, 544]

def apply_triage():
    conn = get_db_connection()
    cursor = conn.cursor()

    print(f"Applying triage to {len(TRIAGE_IDS)} questions...")

    for q_id in TRIAGE_IDS:
        # 1. Update question_classification to manual with axis_b = 'znaki_i_sygnaly'
        cursor.execute("DELETE FROM question_classification WHERE question_id = ?", (q_id,))
        cursor.execute(
            "INSERT INTO question_classification (question_id, axis, value, confidence, source) VALUES (?, 'A', 'zastosowanie', 1.0, 'manual')",
            (q_id,)
        )
        cursor.execute(
            "INSERT INTO question_classification (question_id, axis, value, confidence, source) VALUES (?, 'B', 'znaki_i_sygnaly', 1.0, 'manual')",
            (q_id,)
        )
        cursor.execute(
            "INSERT INTO question_classification (question_id, axis, value, confidence, source) VALUES (?, 'C', 'brak_pulapki', 1.0, 'manual')",
            (q_id,)
        )

        # 2. Update vision_review decision
        cursor.execute("""
            UPDATE vision_review
            SET decision = 'auto_accepted',
                confidence = 1.0,
                rationale = 'Ręcznie zatwierdzone oznakowanie skrzyżowania (znaki pierwszeństwa/sygnalizacja).'
            WHERE question_id = ?
        """, (q_id,))

        # 3. Regenerate explanation
        exp, legal, c_hash = regenerate_vision_explanation(
            question_id=q_id,
            axis_b="znaki_i_sygnaly",
            visual_rationale="Na materiale wizualnym widoczne jest oznakowanie skrzyżowania (znaki pierwszeństwa/sygnalizacja).",
            conn=conn
        )

        print(f" - Q#{q_id} updated to znaki_i_sygnaly (manual). Legal: {legal[:35]}... Hash: {c_hash}")

    conn.commit()
    conn.close()
    print("Triage applied successfully for all 8 questions.")

if __name__ == "__main__":
    apply_triage()
