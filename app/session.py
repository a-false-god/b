"""
Session Composer Module for Prawko B MVP.
Implements evidence-based priority queue session composition for maximum material mastery:

Amendment A:
1. Due reviews (spaced candidates) and recently-incorrect come FIRST (~60% of session).
2. Never-seen fills the remainder (~40% of session, capped at 20 per session).
3. Never-seen items are sorted by points (3pt -> 2pt -> 1pt) for maximum score impact (~65% of exam score).
4. Domain interleaving applied across Axis B domains.

Amendment B:
Mastered status requires correct answers on >= 2 distinct calendar days AND the latest answer is correct.
"""

import json
from typing import List, Dict, Any, Optional
import sqlite3

AXIS_B_DOMAINS = [
    'znaki_i_sygnaly',
    'pierwszenstwo',
    'manewry_i_pozycja',
    'predkosc_i_odleglosci',
    'technika_pojazdu',
    'administracja_i_kary',
    'pierwsza_pomoc',
    'ekologia'
]


def interleave_questions(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Interleaves a list of question dicts across their axis_b domains.
    Picks one question from each available domain in round-robin fashion.
    """
    if not questions:
        return []

    # Group by axis_b
    by_domain: Dict[str, List[Dict[str, Any]]] = {}
    for q in questions:
        dom = q.get("axis_b") or "other"
        if dom not in by_domain:
            by_domain[dom] = []
        by_domain[dom].append(q)

    interleaved = []
    domain_keys = list(by_domain.keys())
    
    while any(by_domain.values()):
        for dom in domain_keys:
            if by_domain[dom]:
                interleaved.append(by_domain[dom].pop(0))

    return interleaved


def get_session_queue(
    conn: sqlite3.Connection,
    user_id: int,
    mode: str = "auto",
    limit: int = 20,
    axis_b: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generates a session queue of Category B questions.
    """
    cursor = conn.cursor()

    if mode == "drill" and axis_b:
        # Weak point drill mode focused on a single domain
        query = """
            SELECT q.*, qc_a.value as axis_a, qc_b.value as axis_b
            FROM questions q
            LEFT JOIN question_classification qc_a ON q.id = qc_a.question_id AND qc_a.axis = 'A'
            LEFT JOIN question_classification qc_b ON q.id = qc_b.question_id AND qc_b.axis = 'B'
            WHERE q.categories LIKE '%"B"%' AND qc_b.value = ?
            ORDER BY q.points DESC, RANDOM()
            LIMIT ?
        """
        cursor.execute(query, (axis_b, limit))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["categories"] = json.loads(d["categories"]) if d.get("categories") else []
            result.append(d)
        return result

    # Default "auto" mode:
    # 1. Recently incorrect questions (latest answer is wrong)
    incorrect_query = """
        WITH LatestAnswer AS (
            SELECT question_id, is_correct,
                   ROW_NUMBER() OVER (PARTITION BY question_id ORDER BY id DESC) as rn
            FROM answer_events
            WHERE user_id = ?
        )
        SELECT q.*, qc_a.value as axis_a, qc_b.value as axis_b
        FROM questions q
        JOIN LatestAnswer la ON q.id = la.question_id
        LEFT JOIN question_classification qc_a ON q.id = qc_a.question_id AND qc_a.axis = 'A'
        LEFT JOIN question_classification qc_b ON q.id = qc_b.question_id AND qc_b.axis = 'B'
        WHERE la.rn = 1 AND la.is_correct = 0 AND q.categories LIKE '%"B"%'
        ORDER BY q.points DESC, RANDOM()
        LIMIT ?
    """
    cursor.execute(incorrect_query, (user_id, limit))
    incorrect_rows = [dict(r) for r in cursor.fetchall()]

    # 2. Spaced review candidates (seen, not mastered: either < 2 distinct days correct OR latest is incorrect)
    review_query = """
        WITH LatestEvent AS (
            SELECT question_id, is_correct,
                   ROW_NUMBER() OVER (PARTITION BY question_id ORDER BY id DESC) as rn
            FROM answer_events
            WHERE user_id = ?
        ),
        CorrectDays AS (
            SELECT question_id, COUNT(DISTINCT DATE(created_at)) as distinct_days
            FROM answer_events
            WHERE user_id = ? AND is_correct = 1
            GROUP BY question_id
        )
        SELECT DISTINCT q.*, qc_a.value as axis_a, qc_b.value as axis_b
        FROM questions q
        JOIN answer_events ae ON q.id = ae.question_id AND ae.user_id = ?
        LEFT JOIN CorrectDays cd ON q.id = cd.question_id
        LEFT JOIN LatestEvent le ON q.id = le.question_id AND le.rn = 1
        LEFT JOIN question_classification qc_a ON q.id = qc_a.question_id AND qc_a.axis = 'A'
        LEFT JOIN question_classification qc_b ON q.id = qc_b.question_id AND qc_b.axis = 'B'
        WHERE q.categories LIKE '%"B"%' AND (COALESCE(cd.distinct_days, 0) < 2 OR le.is_correct = 0)
        ORDER BY q.points DESC, RANDOM()
        LIMIT ?
    """
    cursor.execute(review_query, (user_id, user_id, user_id, limit))
    review_rows = [dict(r) for r in cursor.fetchall()]

    # Combine review and incorrect pool (FIRST priority)
    seen_ids = set()
    review_wrong_pool = []
    for q in incorrect_rows + review_rows:
        if q["id"] not in seen_ids:
            review_wrong_pool.append(q)
            seen_ids.add(q["id"])

    # Target mix: ~60% review/wrong, ~40% new (new capped at 20)
    target_review_count = int(limit * 0.6)
    target_new_count = limit - min(len(review_wrong_pool), target_review_count)
    target_new_count = min(target_new_count, 20)  # Capped at 20 new per session

    # 3. Never-seen questions (sorted 3pt -> 2pt -> 1pt)
    never_seen_query = """
        SELECT q.*, qc_a.value as axis_a, qc_b.value as axis_b
        FROM questions q
        LEFT JOIN question_classification qc_a ON q.id = qc_a.question_id AND qc_a.axis = 'A'
        LEFT JOIN question_classification qc_b ON q.id = qc_b.question_id AND qc_b.axis = 'B'
        WHERE q.categories LIKE '%"B"%'
          AND q.id NOT IN (SELECT DISTINCT question_id FROM answer_events WHERE user_id = ?)
        ORDER BY q.points DESC, RANDOM()
        LIMIT ?
    """
    cursor.execute(never_seen_query, (user_id, target_new_count * 2))
    never_seen_rows = [dict(r) for r in cursor.fetchall()]

    new_pool = []
    for q in never_seen_rows:
        if q["id"] not in seen_ids:
            new_pool.append(q)
            seen_ids.add(q["id"])
            if len(new_pool) >= target_new_count:
                break

    # Assemble session candidates (Review/Wrong FIRST, then New)
    session_candidates = review_wrong_pool[:limit - len(new_pool)] + new_pool
    if len(session_candidates) < limit:
        # Fill remaining spots with extra review/wrong or new
        for q in review_wrong_pool + never_seen_rows:
            if q["id"] not in [x["id"] for x in session_candidates]:
                session_candidates.append(q)
                if len(session_candidates) >= limit:
                    break

    for q in session_candidates:
        if isinstance(q.get("categories"), str):
            q["categories"] = json.loads(q["categories"])

    # Apply domain interleaving
    interleaved = interleave_questions(session_candidates)
    return interleaved[:limit]


def generate_exam_sheet(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Generates a 32-question official exam simulation (20 basic + 12 specialized)
    with total points and pass threshold 68 points.
    """
    cursor = conn.cursor()

    def fetch_pool(scope: str, pts: int, cnt: int):
        cursor.execute(
            """
            SELECT id, lp, scope, points, type, correct, media, media_kind, q_pl, a_pl, b_pl, c_pl, categories
            FROM questions
            WHERE scope = ? AND points = ? AND (status IS NULL OR status != 'pending') AND categories LIKE '%"B"%'
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (scope, pts, cnt)
        )
        out = []
        for r in cursor.fetchall():
            d = dict(r)
            d["categories"] = json.loads(d["categories"]) if d.get("categories") else []
            out.append(d)
        return out

    # Basic: 10x3pt, 6x2pt, 4x1pt
    b3 = fetch_pool("PODSTAWOWY", 3, 10)
    b2 = fetch_pool("PODSTAWOWY", 2, 6)
    b1 = fetch_pool("PODSTAWOWY", 1, 4)
    basic_questions = b3 + b2 + b1

    if len(basic_questions) < 20:
        existing_ids = tuple(q["id"] for q in basic_questions) or (-1,)
        placeholders = ",".join("?" for _ in existing_ids)
        cursor.execute(
            f"""
            SELECT id, lp, scope, points, type, correct, media, media_kind, q_pl, a_pl, b_pl, c_pl, categories
            FROM questions
            WHERE scope = 'PODSTAWOWY' AND (status IS NULL OR status != 'pending') AND categories LIKE '%"B"%'
              AND id NOT IN ({placeholders})
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (*existing_ids, 20 - len(basic_questions))
        )
        for r in cursor.fetchall():
            d = dict(r)
            d["categories"] = json.loads(d["categories"]) if d.get("categories") else []
            basic_questions.append(d)

    # Specialized: 6x3pt, 4x2pt, 2x1pt
    s3 = fetch_pool("SPECJALISTYCZNY", 3, 6)
    s2 = fetch_pool("SPECJALISTYCZNY", 2, 4)
    s1 = fetch_pool("SPECJALISTYCZNY", 1, 2)
    spec_questions = s3 + s2 + s1

    if len(spec_questions) < 12:
        existing_ids = tuple(q["id"] for q in spec_questions) or (-1,)
        placeholders = ",".join("?" for _ in existing_ids)
        cursor.execute(
            f"""
            SELECT id, lp, scope, points, type, correct, media, media_kind, q_pl, a_pl, b_pl, c_pl, categories
            FROM questions
            WHERE scope = 'SPECJALISTYCZNY' AND (status IS NULL OR status != 'pending') AND categories LIKE '%"B"%'
              AND id NOT IN ({placeholders})
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (*existing_ids, 12 - len(spec_questions))
        )
        for r in cursor.fetchall():
            d = dict(r)
            d["categories"] = json.loads(d["categories"]) if d.get("categories") else []
            spec_questions.append(d)

    questions = basic_questions + spec_questions
    return {
        "questions": questions,
        "basic_questions": basic_questions,
        "spec_questions": spec_questions,
        "total_questions": len(questions),
        "max_score": 74,
        "pass_threshold": 68
    }

