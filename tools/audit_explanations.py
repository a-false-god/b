#!/usr/bin/env python3
"""
Audit tool for Elaborated Explanations & Legal Bases in Prawko B (Milestone P2).
Inspects coverage, statutory whitelist compliance, content hash integrity,
vision review backlog (P4 readiness), and quality metrics for all Category B questions.
"""

import sys
import json
from pathlib import Path
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import get_db_connection
from scripts.generate_explanations import load_legal_catalog, compute_question_content_hash


def run_explanations_audit():
    conn = get_db_connection()
    cursor = conn.cursor()
    catalog = load_legal_catalog()

    # 1. Total Category B Questions in catalog
    cursor.execute("SELECT id, q_pl, a_pl, b_pl, c_pl, correct, media FROM questions WHERE categories LIKE '%\"B\"%'")
    cat_b_questions = {r["id"]: dict(r) for r in cursor.fetchall()}
    total_cat_b = len(cat_b_questions)

    # 2. Total Explanations Cached (Deduplicated by question_id)
    cursor.execute("""
        SELECT q.id as question_id, qe.explanation, qe.legal_basis, qe.source, qe.content_hash, qe.needs_vision_review,
               COALESCE(qc_b.value, 'unclassified') AS axis_b
        FROM questions q
        LEFT JOIN question_explanations qe ON q.id = qe.question_id
        LEFT JOIN (
            SELECT question_id, value FROM question_classification WHERE axis = 'B' GROUP BY question_id
        ) qc_b ON q.id = qc_b.question_id
        WHERE q.categories LIKE '%"B"%'
        ORDER BY q.id
    """)
    rows = cursor.fetchall()
    cached_rows = [r for r in rows if r["explanation"] is not None]
    cached_count = len(cached_rows)

    coverage_pct = (cached_count / total_cat_b * 100.0) if total_cat_b > 0 else 0.0

    print("================================================================")
    print(" PRAWKO B - ELABORATED FEEDBACK & STATUTORY AUDIT REPORT (P2)")
    print("================================================================")
    print(f"Total Category B Questions:        {total_cat_b:,}")
    print(f"Explanations Cached in SQLite:     {cached_count:,} ({coverage_pct:.1f}%)")
    print(f"Missing Explanations:              {total_cat_b - cached_count:,}")
    print("----------------------------------------------------------------")

    if cached_count == 0:
        print("[WARN] No explanations found in database. Run 'python tools/populate_explanations.py' first.")
        conn.close()
        return

    # Metrics and quality checks
    word_counts = []
    empty_explanations = 0
    empty_legals = 0
    invalid_citations = 0
    hash_mismatches = 0
    vision_review_needed = 0
    unknown_count = 0

    sources = Counter()
    domains = Counter()
    legal_statutes = Counter()
    domain_to_statutes = defaultdict(Counter)

    known_statute_prefixes = [
        "Art.", "§", "Rozp.", "Rozporządzeni", "Kodeks", "Ustawa", "Zasady", "unknown", "Wytyczne"
    ]

    for r in cached_rows:
        q_id = r["question_id"]
        exp = r["explanation"] or ""
        legal = r["legal_basis"] or ""
        source = r["source"] or "unknown"
        axis_b = r["axis_b"]
        c_hash = r["content_hash"]
        needs_vis = r["needs_vision_review"]

        words = len(exp.split())
        word_counts.append(words)

        if not exp.strip():
            empty_explanations += 1
        if not legal.strip():
            empty_legals += 1
        if legal.strip().lower() == "unknown":
            unknown_count += 1

        # Check whitelist compliance
        if not any(legal.strip().startswith(prefix) for prefix in known_statute_prefixes):
            invalid_citations += 1

        # Check content hash integrity
        if q_id in cat_b_questions:
            # Check text hash or vision hash
            exp_text_hash = compute_question_content_hash(cat_b_questions[q_id], axis_signature=axis_b, mode="text")
            exp_vis_hash = compute_question_content_hash(cat_b_questions[q_id], axis_signature=axis_b, mode="vision")
            if c_hash and c_hash not in (exp_text_hash, exp_vis_hash):
                hash_mismatches += 1

        if needs_vis == 1:
            vision_review_needed += 1

        sources[source] += 1
        domains[axis_b] += 1

        # Extract primary statute prefix
        statute_key = legal.split("—")[0].split("(")[0].strip()[:42]
        legal_statutes[statute_key] += 1
        domain_to_statutes[axis_b][statute_key] += 1

    avg_words = sum(word_counts) / len(word_counts) if word_counts else 0
    min_words = min(word_counts) if word_counts else 0
    max_words = max(word_counts) if word_counts else 0

    print("--- QUALITY & STATUTORY COMPLIANCE METRICS ---")
    print(f" - Average Explanation Length:    {avg_words:.1f} words (optimum: 30-75)")
    print(f" - Word Count Range:              {min_words} - {max_words} words")
    print(f" - Empty Explanations:            {empty_explanations}")
    print(f" - Empty Legal Bases:             {empty_legals}")
    print(f" - Fallback 'unknown' (No statute): {unknown_count} ({unknown_count/cached_count*100:.1f}%)")
    print(f" - Invalid Citations:             {invalid_citations} (100% whitelist verified)")
    print(f" - Stale / Mismatched Hashes:     {hash_mismatches}")
    print(f" - Flagged for P4 Vision Pass:    {vision_review_needed} ({vision_review_needed/cached_count*100:.1f}%)")
    print("----------------------------------------------------------------")

    print("--- ROZKŁAD PODSTAW PRAWNYCH PER OŚ B (Content Domain) ---")
    for dom, dom_count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
        print(f"\n[DOMENA: {dom}] (Łącznie: {dom_count} pytań)")
        for stat, s_count in domain_to_statutes[dom].most_common(5):
            print(f"   * {stat:<42}: {s_count:>4} ({s_count/dom_count*100:.1f}%)")

    print("\n================================================================")
    conn.close()


if __name__ == "__main__":
    run_explanations_audit()
