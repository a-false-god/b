#!/usr/bin/env python3
"""
Audit and Reporting Tool for Milestone P4: Vision Pass.
Analyzes multimodal review decisions, classification shifts,
concordance per axis, and the delta in domain distributions.
"""

import sys
import json
import sqlite3
from pathlib import Path
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import get_db_connection


def run_vision_audit():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Total questions with media
    cursor.execute("""
        SELECT id, media, media_kind
        FROM questions
        WHERE categories LIKE '%"B"%' AND media IS NOT NULL AND TRIM(media) != ''
    """)
    media_questions = {r["id"]: dict(r) for r in cursor.fetchall()}
    total_media_questions = len(media_questions)

    # 2. Vision Review entries
    cursor.execute("""
        SELECT vr.*, q.q_pl, q.media
        FROM vision_review vr
        JOIN questions q ON vr.question_id = q.id
    """)
    reviews = {r["question_id"]: dict(r) for r in cursor.fetchall()}
    processed_count = len(reviews)

    # Decisions breakdown
    decisions = Counter(r["decision"] for r in reviews.values())

    # 3. Concordance stats
    cursor.execute("""
        SELECT q.id,
               qc_a.value as curr_a, qc_b.value as curr_b,
               vr.suggested_axis_a, vr.suggested_axis_b, vr.suggested_axis_c,
               vr.confidence, vr.decision, vr.model
        FROM questions q
        JOIN vision_review vr ON q.id = vr.question_id
        LEFT JOIN (SELECT question_id, value FROM question_classification WHERE axis = 'A' GROUP BY question_id) qc_a ON q.id = qc_a.question_id
        LEFT JOIN (SELECT question_id, value FROM question_classification WHERE axis = 'B' GROUP BY question_id) qc_b ON q.id = qc_b.question_id
        WHERE q.categories LIKE '%"B"%'
    """)
    comp_rows = cursor.fetchall()

    axis_a_matches = 0
    axis_b_matches = 0
    total_compared = 0

    for r in comp_rows:
        if r["decision"] != "skipped_no_media":
            total_compared += 1
            if r["curr_a"] == r["suggested_axis_a"]:
                axis_a_matches += 1
            if r["curr_b"] == r["suggested_axis_b"]:
                axis_b_matches += 1

    # 4. Domain distribution in question_classification
    cursor.execute("""
        SELECT qc.value as domain, COUNT(*) as count, qc.source
        FROM question_classification qc
        JOIN questions q ON qc.question_id = q.id
        WHERE qc.axis = 'B' AND q.categories LIKE '%"B"%'
        GROUP BY qc.value, qc.source
    """)
    domain_source_rows = cursor.fetchall()

    domain_counts = Counter()
    domain_sources = defaultdict(Counter)
    for r in domain_source_rows:
        domain_counts[r["domain"]] += r["count"]
        domain_sources[r["domain"]][r["source"]] += r["count"]

    # 5. Citations in domena znaki_i_sygnaly
    cursor.execute("""
        SELECT qe.legal_basis, COUNT(*) as count
        FROM question_explanations qe
        JOIN question_classification qc ON qe.question_id = qc.question_id AND qc.axis = 'B'
        WHERE qc.value = 'znaki_i_sygnaly'
        GROUP BY qe.legal_basis
        ORDER BY count DESC
    """)
    signs_citations = cursor.fetchall()

    # 6. Flagged count
    cursor.execute("""
        SELECT COUNT(*) FROM question_explanations WHERE needs_vision_review = 1
    """)
    needs_vision_remaining = cursor.fetchone()[0]

    conn.close()

    print("================================================================")
    print("      PRAWKO B — AUDYT WYNIKÓW VISION PASS (MILESTONE P4)      ")
    print("================================================================")
    print(f"Łączna liczba pytań z mediami:         {total_media_questions:,}")
    print(f"Przetworzone w vision_review:          {processed_count:,} ({(processed_count/total_media_questions*100):.1f}%)" if total_media_questions else "0%")
    print(f"Pozostałe w kolejce (needs_review=1):  {needs_vision_remaining:,}")
    print("----------------------------------------------------------------")
    print("ROZKŁAD DECYZJI VISION PASS:")
    print(f" - Auto-Accepted (Zgodność -> conf 0.9):  {decisions.get('auto_accepted', 0):>5} ({(decisions.get('auto_accepted', 0)/total_media_questions*100):.1f}%)")
    print(f" - Auto-Corrected (Korekta -> vision):    {decisions.get('auto_corrected', 0):>5} ({(decisions.get('auto_corrected', 0)/total_media_questions*100):.1f}%)")
    print(f" - Queued (Niepewne / Manual-Hold):       {decisions.get('queued', 0):>5} ({(decisions.get('queued', 0)/total_media_questions*100):.1f}%)")
    print(f" - Skipped (Brak pliku na dysku):        {decisions.get('skipped_no_media', 0):>5} ({(decisions.get('skipped_no_media', 0)/total_media_questions*100):.1f}%)")
    print("----------------------------------------------------------------")

    if total_compared > 0:
        pct_a = (axis_a_matches / total_compared * 100)
        pct_b = (axis_b_matches / total_compared * 100)
        print("ZGODNOŚĆ KLASYFIKACJI WIZYJNEJ Z TEKSTOWĄ:")
        print(f" - Oś A (Wymóg poznawczy):   {axis_a_matches}/{total_compared} ({pct_a:.1f}%)")
        print(f" - Oś B (Domena treści):     {axis_b_matches}/{total_compared} ({pct_b:.1f}%)")
        print("----------------------------------------------------------------")

    print("AKTUALNY ROZKŁAD DOMEN OSI B (Wszystkie 2 135 pytań kat. B):")
    for dom, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True):
        src_str = ", ".join(f"{s}:{c}" for s, c in domain_sources[dom].items())
        print(f" - {dom:<25}: {count:>4} pytań [{src_str}]")

    print("----------------------------------------------------------------")
    print("CYTOWANIA W DOMENIE 'znaki_i_sygnaly':")
    for row in signs_citations[:5]:
        legal_short = str(row["legal_basis"])[:45]
        print(f"   * {legal_short:<45}: {row['count']:>4}")

    print("================================================================\n")


if __name__ == "__main__":
    run_vision_audit()
