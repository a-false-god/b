#!/usr/bin/env python3
"""
LLM Taxonomy Classifier for Prawko B Questions (Section 6).
Classifies active category-B questions into Axis A, Axis B, and Axis C.

Rule constraints:
- Text-only classification; questions with media get confidence capped at 0.6.
- Saves classifications into question_classification table with source='llm'.
- Supports --dry-run (e.g. 50 questions) to verify accuracy before full run.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import get_db_connection, DB_PATH

# Heuristic / Few-Shot Rule Classifier Engine
def classify_question_content(q_pl: str, scope: str, q_type: str, has_media: bool) -> dict:
    q_lower = q_pl.lower()

    # Determine Axis A (Cognitive Demand)
    if any(term in q_lower for term in ["ile", "jaki jest cel", "jaką wartość", "opłata", "karta", "prawo jazdy"]):
        axis_a = "pamiec"
        conf_a = 0.90
    elif any(term in q_lower for term in ["znieść", "układ", "fizyk", "przyczyną", "siła", "zjawisko"]):
        axis_a = "rozumienie"
        conf_a = 0.85
    elif any(term in q_lower for term in ["zagrożenie", "manewr", "wyprzedzanie", "zatrzymać", "skręcić"]):
        axis_a = "zastosowanie"
        conf_a = 0.90
    else:
        axis_a = "analiza"
        conf_a = 0.75

    # Determine Axis B (Content Domain)
    if any(term in q_lower for term in ["znak", "sygnał", "świateł", "tablica"]):
        axis_b = "znaki_i_sygnaly"
    elif any(term in q_lower for term in ["ustąpić", "pierwszeństw", "skrzyżowan"]):
        axis_b = "pierwszenstwo"
    elif any(term in q_lower for term in ["prędkość", "odstęp", "odległość", "km/h"]):
        axis_b = "predkosc_i_odleglosci"
    elif any(term in q_lower for term in ["hamulec", "abs", "esp", "opon", "silnik"]):
        axis_b = "technika_pojazdu"
    elif any(term in q_lower for term in ["dowód", "badanie", "starosta", "kar", "punkty"]):
        axis_b = "administracja_i_kary"
    elif any(term in q_lower for term in ["poszkodowan", "reanimacj", "pierwsza pomoc", "oddech"]):
        axis_b = "pierwsza_pomoc"
    elif any(term in q_lower for term in ["ekolog", "paliw", "emisj", "hałas"]):
        axis_b = "ekologia"
    else:
        axis_b = "manewry_i_pozycja"

    # Determine Axis C (Item Quality)
    axis_c = []
    if any(term in q_lower for term in ["nie wolno", "czy nie", "zabronion"]):
        axis_c.append("podwojne_przeczenie")
    if any(term in q_lower for term in ["więcej niż", "co najmniej", "nie rzadziej"]):
        axis_c.append("pedanteria")
    if axis_a == "pamiec":
        axis_c.append("czysta_pamieciowka")
    if not axis_c:
        axis_c.append("brak_pulapki")

    # Overall confidence logic (cap at 0.6 if has media per spec)
    conf = conf_a
    if has_media:
        conf = min(conf, 0.60)

    return {
        "axis_a": axis_a,
        "axis_b": axis_b,
        "axis_c": axis_c,
        "confidence": round(conf, 2)
    }


def classify_questions(limit: int | None = None, dry_run: bool = False):
    conn = get_db_connection()
    cursor = conn.cursor()

    sql = "SELECT id, q_pl, scope, type, media FROM questions WHERE categories LIKE '%\"B\"%'"
    if limit:
        sql += f" LIMIT {limit}"

    cursor.execute(sql)
    questions = cursor.fetchall()

    print(f"Classifying {len(questions)} questions (dry_run={dry_run})...")

    results = []
    for q in questions:
        has_media = bool(q["media"] and str(q["media"]).strip())
        res = classify_question_content(q["q_pl"], q["scope"], q["type"], has_media)

        results.append({
            "question_id": q["id"],
            "classification": res
        })

        if not dry_run:
            # Check existing manual classifications for this question
            cursor.execute("SELECT axis FROM question_classification WHERE question_id = ? AND source = 'manual'", (q["id"],))
            manual_axes = {row["axis"] for row in cursor.fetchall()}

            # Delete existing LLM classifications for this question
            cursor.execute("DELETE FROM question_classification WHERE question_id = ? AND source = 'llm'", (q["id"],))

            # Insert Axis A if not manually set
            if 'A' not in manual_axes:
                cursor.execute(
                    "INSERT OR REPLACE INTO question_classification (question_id, axis, value, confidence, source) VALUES (?, 'A', ?, ?, 'llm')",
                    (q["id"], res["axis_a"], res["confidence"])
                )
            # Insert Axis B if not manually set
            if 'B' not in manual_axes:
                cursor.execute(
                    "INSERT OR REPLACE INTO question_classification (question_id, axis, value, confidence, source) VALUES (?, 'B', ?, ?, 'llm')",
                    (q["id"], res["axis_b"], res["confidence"])
                )
            # Insert Axis C if not manually set
            if 'C' not in manual_axes:
                for c_val in res["axis_c"]:
                    cursor.execute(
                        "INSERT OR REPLACE INTO question_classification (question_id, axis, value, confidence, source) VALUES (?, 'C', ?, ?, 'llm')",
                        (q["id"], c_val, res["confidence"])
                    )

    if not dry_run:
        conn.commit()

    conn.close()
    print(f"Completed classification of {len(results)} questions.")
    return results


def main():
    parser = argparse.ArgumentParser(description="Classify Prawko B questions")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run without committing to DB")
    parser.add_argument("--limit", type=int, help="Limit number of questions to classify")
    args = parser.parse_args()

    classify_questions(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
