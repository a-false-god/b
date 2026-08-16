"""
API Routes for Prawko B MVP.
Implements Auth, Questions, Answers, Analytics (6 metrics), and Review endpoints.
"""

import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Query, BackgroundTasks
from pydantic import BaseModel

from app.db import get_db_connection
from app.auth import (
    hash_password,
    verify_password,
    verify_password_or_dummy,
    check_rate_limit,
    check_registration_key,
    create_session,
    get_current_user_id,
    require_user_id,
    destroy_session,
)
from app.config import SLIP_THRESHOLD_MS, HESITATION_THRESHOLD_MS, LOW_CONFIDENCE_THRESHOLD, SKILL_INIT, SKILL_LR0, DIFF_ALPHA, DIFF_BETA
from app.skill import calc_question_difficulty, calc_skill_update
from app.session import get_session_queue, generate_exam_sheet
from scripts.generate_explanations import generate_explanation_for_question
import math

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class UserAuthRequest(BaseModel):
    login: str
    password: str
    registration_key: Optional[str] = None

class AnswerSubmissionRequest(BaseModel):
    question_id: int
    chosen: str
    time_ms: int
    session_id: str

class ClassificationReviewRequest(BaseModel):
    axis_a: str
    axis_b: str
    axis_c: List[str] = []
    action: str = "accept"  # accept or override


# ---------------------------------------------------------------------------
# Health Check Endpoint
# ---------------------------------------------------------------------------

@router.get("/healthz")
def healthz():
    """
    Unauthenticated health check returning system status, DB state, and questions count.
    """
    db_ok = False
    questions_count = 0
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM questions")
        row = cursor.fetchone()
        if row:
            questions_count = row[0]
            db_ok = True
        conn.close()
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "db_ok": db_ok,
        "questions_count": questions_count
    }


# ---------------------------------------------------------------------------
# Authentication Endpoints
# ---------------------------------------------------------------------------

@router.post("/auth/register")
def register(req: UserAuthRequest, request: Request, response: Response):
    check_rate_limit(request, action="auth_register")

    # Check registration key gating
    header_key = request.headers.get("X-Registration-Key")
    provided_key = req.registration_key or header_key
    if not check_registration_key(provided_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rejestracja wymaga klucza"
        )

    login = req.login.strip()
    if not login or not req.password:
        raise HTTPException(status_code=400, detail="Login and password required")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE login = ?", (login,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Login already taken")

    pw_hash = hash_password(req.password)
    cursor.execute("INSERT INTO users (login, password_hash) VALUES (?, ?)", (login, pw_hash))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    create_session(user_id, response, request=request)
    return {"user_id": user_id, "login": login}


@router.post("/auth/login")
def login(req: UserAuthRequest, request: Request, response: Response):
    check_rate_limit(request, action="auth_login")
    login = req.login.strip()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, password_hash FROM users WHERE login = ?", (login,))
    row = cursor.fetchone()
    conn.close()

    stored_hash = row["password_hash"] if row else None
    if not verify_password_or_dummy(req.password, stored_hash) or not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = row["id"]
    create_session(user_id, response, request=request)
    return {"user_id": user_id, "login": login}



@router.post("/auth/logout")
def logout(request: Request, response: Response):
    destroy_session(request, response)
    return {"message": "Logged out successfully"}


# ---------------------------------------------------------------------------
# Questions API
# ---------------------------------------------------------------------------

@router.get("/api/questions")
def list_questions(
    scope: Optional[str] = Query(None),
    axisA: Optional[str] = Query(None),
    axisB: Optional[str] = Query(None),
    axisC: Optional[str] = Query(None),
    untriaged: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
    category: str = Query("B"),
    limit: int = Query(100),
    offset: int = Query(0)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    sql = """
        SELECT DISTINCT q.*,
               qc_a.value AS axis_a,
               qc_b.value AS axis_b
        FROM questions q
        LEFT JOIN question_classification qc_a ON q.id = qc_a.question_id AND qc_a.axis = 'A'
        LEFT JOIN question_classification qc_b ON q.id = qc_b.question_id AND qc_b.axis = 'B'
        LEFT JOIN question_classification qc_c ON q.id = qc_c.question_id AND qc_c.axis = 'C'
        WHERE 1=1
    """
    params = []

    if category:
        sql += " AND q.categories LIKE ?"
        params.append(f'%"{category}"%')

    if scope:
        scope_norm = "PODSTAWOWY" if scope.upper() in ("P", "PODSTAWOWY") else "SPECJALISTYCZNY"
        sql += " AND q.scope = ?"
        params.append(scope_norm)

    if axisA:
        sql += " AND qc_a.value = ?"
        params.append(axisA)

    if axisB:
        sql += " AND qc_b.value = ?"
        params.append(axisB)

    if axisC:
        sql += " AND qc_c.value = ?"
        params.append(axisC)

    if untriaged == 1:
        sql += " AND q.id NOT IN (SELECT DISTINCT question_id FROM question_classification WHERE source = 'manual')"

    if q:
        sql += " AND (q.q_pl LIKE ? OR q.id = ?)"
        params.extend([f"%{q}%", int(q) if q.isdigit() else -1])

    sql += " ORDER BY q.id LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        d["categories"] = json.loads(d["categories"]) if d.get("categories") else []
        result.append(d)

    return result


@router.get("/api/questions/{question_id}")
def get_question(question_id: int, request: Request):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
    q_row = cursor.fetchone()
    if not q_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Question not found")

    question = dict(q_row)
    question["categories"] = json.loads(question["categories"]) if question.get("categories") else []

    # Get classifications
    cursor.execute("SELECT axis, value, confidence, source FROM question_classification WHERE question_id = ?", (question_id,))
    classifications = [dict(r) for r in cursor.fetchall()]

    # Get user stats if authenticated
    user_id = get_current_user_id(request)
    stats = None
    if user_id:
        cursor.execute(
            """
            SELECT COUNT(*) AS total_attempts,
                   SUM(is_correct) AS correct_attempts,
                   AVG(time_ms) AS avg_time_ms
            FROM answer_events
            WHERE user_id = ? AND question_id = ? AND mode = 'nauka'
            """,
            (user_id, question_id)
        )
        s_row = cursor.fetchone()
        if s_row:
            stats = dict(s_row)

    conn.close()
    return {
        "question": question,
        "classification": classifications,
        "user_stats": stats
    }


# ---------------------------------------------------------------------------
# Session Composer API (Requires Auth for dynamic user queue)
# ---------------------------------------------------------------------------

@router.get("/api/session/next")
def get_next_session(
    mode: str = Query("auto"),
    limit: int = Query(20),
    axisB: Optional[str] = Query(None),
    request: Request = None
):
    """
    Session Composer endpoint. Generates a priority-ordered, interleaved queue
    of questions for maximum material mastery.
    """
    user_id = get_current_user_id(request)
    conn = get_db_connection()
    queue = get_session_queue(conn, user_id=user_id or 0, mode=mode, limit=limit, axis_b=axisB)
    conn.close()
    return queue


# ---------------------------------------------------------------------------
# Answers Submission API (Requires Auth)
# ---------------------------------------------------------------------------

def generate_explanation_task(question_id: int):
    """Background task to generate & cache explanation without blocking answer response."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT explanation FROM question_explanations WHERE question_id = ?", (question_id,))
    if not cursor.fetchone():
        cursor.execute("SELECT q.*, qc_b.value as axis_b FROM questions q LEFT JOIN question_classification qc_b ON q.id = qc_b.question_id AND qc_b.axis = 'B' WHERE q.id = ?", (question_id,))
        q_full = cursor.fetchone()
        if q_full:
            explanation, legal_basis, content_hash, needs_vision = generate_explanation_for_question(dict(q_full))
            cursor.execute("""
                INSERT OR REPLACE INTO question_explanations (question_id, explanation, legal_basis, source, content_hash, needs_vision_review)
                VALUES (?, ?, ?, 'llm', ?, ?)
            """, (question_id, explanation, legal_basis, content_hash, needs_vision))
            conn.commit()
    conn.close()


@router.get("/api/questions/{question_id}/explanation")
def get_question_explanation(question_id: int):
    """Fetches cached explanation or signals pending generation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT explanation, legal_basis, source FROM question_explanations WHERE question_id = ?", (question_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"question_id": question_id, "explanation": None, "legal_basis": None, "source": None, "pending": True}
    return {"question_id": question_id, "explanation": row["explanation"], "legal_basis": row["legal_basis"], "source": row["source"] if "source" in row.keys() else "llm", "pending": False}


# ---------------------------------------------------------------------------
# Answers Submission API (Requires Auth)
# ---------------------------------------------------------------------------

@router.post("/api/answers")
def submit_answer(req: AnswerSubmissionRequest, request: Request, background_tasks: BackgroundTasks):
    user_id = require_user_id(request)

    chosen = req.chosen.strip().upper()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute("SELECT correct FROM questions WHERE id = ?", (req.question_id,))
        q_row = cursor.fetchone()
        if not q_row:
            raise HTTPException(status_code=404, detail="Question not found")

        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        u_row = cursor.fetchone()
        if not u_row:
            raise HTTPException(status_code=404, detail="User not found")

        correct_answer = q_row["correct"].strip().upper()
        is_correct = 1 if chosen == correct_answer else 0
        wrong_inc = 1 - is_correct

        # 1. Insert answer_events row (mode='nauka')
        cursor.execute(
            """
            INSERT INTO answer_events (user_id, question_id, chosen, is_correct, time_ms, session_id, mode)
            VALUES (?, ?, ?, ?, ?, ?, 'nauka')
            """,
            (user_id, req.question_id, chosen, is_correct, req.time_ms, req.session_id)
        )
        event_id = cursor.lastrowid

        # 2. Upsert question_stats
        cursor.execute(
            """
            INSERT INTO question_stats (question_id, attempts, wrong, updated_at)
            VALUES (?, 1, ?, datetime('now'))
            ON CONFLICT(question_id) DO UPDATE SET
              attempts = question_stats.attempts + 1,
              wrong = question_stats.wrong + excluded.wrong,
              updated_at = datetime('now')
            """,
            (req.question_id, wrong_inc)
        )

        cursor.execute("SELECT attempts, wrong FROM question_stats WHERE question_id = ?", (req.question_id,))
        qs_row = cursor.fetchone()
        attempts = qs_row["attempts"]
        wrong = qs_row["wrong"]

        # 3. Question difficulty calculation
        p_err, b_q = calc_question_difficulty(attempts, wrong)

        # Look up question's axis B domain
        cursor.execute("SELECT value FROM question_classification WHERE question_id = ? AND axis = 'B'", (req.question_id,))
        qc_b_row = cursor.fetchone()
        axis_b_domain = qc_b_row["value"] if qc_b_row else None

        # 4. User skill updates (global & domain)
        target_axes = [None]
        if axis_b_domain:
            target_axes.append(axis_b_domain)

        global_theta_before = SKILL_INIT
        global_theta_after = SKILL_INIT
        global_delta = 0.0

        for axis_val in target_axes:
            if axis_val is None:
                cursor.execute("SELECT theta, n FROM user_skill WHERE user_id = ? AND axis_value IS NULL", (user_id,))
            else:
                cursor.execute("SELECT theta, n FROM user_skill WHERE user_id = ? AND axis_value = ?", (user_id, axis_val))
            row = cursor.fetchone()

            curr_theta = row["theta"] if row else SKILL_INIT
            curr_n = row["n"] if row else 0

            new_theta, new_n, delta_theta = calc_skill_update(curr_theta, curr_n, b_q, bool(is_correct))

            if axis_val is None:
                global_theta_before = curr_theta
                global_theta_after = new_theta
                global_delta = delta_theta

            if row:
                if axis_val is None:
                    cursor.execute(
                        "UPDATE user_skill SET theta = ?, n = ?, updated_at = datetime('now') WHERE user_id = ? AND axis_value IS NULL",
                        (new_theta, new_n, user_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE user_skill SET theta = ?, n = ?, updated_at = datetime('now') WHERE user_id = ? AND axis_value = ?",
                        (new_theta, new_n, user_id, axis_val)
                    )
            else:
                cursor.execute(
                    "INSERT INTO user_skill (user_id, axis_value, theta, n, updated_at) VALUES (?, ?, ?, ?, datetime('now'))",
                    (user_id, axis_val, new_theta, new_n)
                )

        # 5. Insert one skill_history snapshot with global theta
        cursor.execute(
            "INSERT INTO skill_history (user_id, theta, created_at) VALUES (?, ?, datetime('now'))",
            (user_id, global_theta_after)
        )

        # 6. Check cache for Elaborated Feedback (Non-blocking: if missing, schedule background task)
        cursor.execute("SELECT explanation, legal_basis FROM question_explanations WHERE question_id = ?", (req.question_id,))
        exp_row = cursor.fetchone()
        explanation = None
        legal_basis = None
        pending = False

        if exp_row:
            explanation = exp_row["explanation"]
            legal_basis = exp_row["legal_basis"]
        else:
            pending = True
            background_tasks.add_task(generate_explanation_task, req.question_id)

        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        conn.close()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Database transaction error: {str(e)}")

    conn.close()

    return {
        "event_id": event_id,
        "question_id": req.question_id,
        "chosen": chosen,
        "is_correct": is_correct,
        "correct_answer": correct_answer,
        "explanation": explanation,
        "legal_basis": legal_basis,
        "pending_explanation": pending,
        "skill_theta_before": global_theta_before,
        "skill_theta_after": global_theta_after,
        "delta_theta": global_delta,
        "attempts": attempts,
        "wrong": wrong,
        "p_err": p_err,
        "b_q": b_q
    }



# ---------------------------------------------------------------------------
# Analytics Endpoints (Requires Auth)
# ---------------------------------------------------------------------------

@router.get("/api/analytics/errors")
def get_error_analytics(
    by: str = Query("question"),
    request: Request = None
):
    user_id = require_user_id(request)
    conn = get_db_connection()
    cursor = conn.cursor()

    if by == "question":
        cursor.execute(
            """
            SELECT ae.question_id, q.q_pl, COUNT(*) AS error_count
            FROM answer_events ae
            JOIN questions q ON ae.question_id = q.id
            WHERE ae.is_correct = 0 AND ae.user_id = ? AND ae.mode = 'nauka'
            GROUP BY ae.question_id
            ORDER BY error_count DESC
            LIMIT 50
            """,
            (user_id,)
        )
        res = [dict(r) for r in cursor.fetchall()]
    elif by in ("axisA", "axisB", "axisC"):
        axis = by[-1].upper()
        cursor.execute(
            """
            SELECT qc.value AS axis_value, COUNT(*) AS error_count
            FROM answer_events ae
            JOIN question_classification qc ON ae.question_id = qc.question_id
            WHERE ae.is_correct = 0 AND ae.user_id = ? AND qc.axis = ? AND ae.mode = 'nauka'
            GROUP BY qc.value
            ORDER BY error_count DESC
            """,
            (user_id, axis)
        )
        res = [dict(r) for r in cursor.fetchall()]
    elif by == "option":
        cursor.execute(
            """
            SELECT ae.question_id, q.q_pl, ae.chosen, q.correct AS correct_option, COUNT(*) AS confused_count
            FROM answer_events ae
            JOIN questions q ON ae.question_id = q.id
            WHERE ae.is_correct = 0 AND q.type = 'ABC' AND ae.user_id = ? AND ae.mode = 'nauka'
            GROUP BY ae.question_id, ae.chosen
            ORDER BY confused_count DESC
            LIMIT 50
            """,
            (user_id,)
        )
        res = [dict(r) for r in cursor.fetchall()]
    else:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid 'by' parameter")

    conn.close()
    return {"by": by, "data": res}


@router.get("/api/analytics/reason")
def get_reason_analytics(request: Request = None):
    user_id = require_user_id(request)
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
          SUM(CASE WHEN is_correct = 0 AND time_ms < ? THEN 1 ELSE 0 END) AS slips,
          SUM(CASE WHEN is_correct = 0 AND time_ms >= ? THEN 1 ELSE 0 END) AS mistakes,
          SUM(CASE WHEN is_correct = 1 AND time_ms > ? THEN 1 ELSE 0 END) AS uncertainty
        FROM answer_events
        WHERE user_id = ? AND mode = 'nauka'
        """,
        (SLIP_THRESHOLD_MS, SLIP_THRESHOLD_MS, HESITATION_THRESHOLD_MS, user_id)
    )
    row = cursor.fetchone()
    conn.close()

    res = dict(row) if row else {"slips": 0, "mistakes": 0, "uncertainty": 0}
    return {
        "slips": res.get("slips") or 0,
        "mistakes": res.get("mistakes") or 0,
        "uncertainty": res.get("uncertainty") or 0
    }


@router.get("/api/analytics/hesitation")
def get_hesitation_analytics(request: Request = None):
    user_id = require_user_id(request)
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT ae.question_id, q.q_pl, ae.time_ms, ae.created_at
        FROM answer_events ae
        JOIN questions q ON ae.question_id = q.id
        WHERE ae.is_correct = 1 AND ae.time_ms > ? AND ae.user_id = ? AND ae.mode = 'nauka'
        ORDER BY ae.time_ms DESC
        LIMIT 50
        """,
        (HESITATION_THRESHOLD_MS, user_id)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"hesitation_candidates": rows, "count": len(rows)}


@router.get("/api/analytics/coverage")
def get_coverage_analytics(request: Request = None):
    user_id = require_user_id(request)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total active Cat-B questions
    cursor.execute("SELECT COUNT(*) FROM questions WHERE categories LIKE '%\"B\"%'")
    total_cat_b = cursor.fetchone()[0]

    # Seen questions by user in learning mode
    cursor.execute(
        "SELECT COUNT(DISTINCT question_id) FROM answer_events WHERE user_id = ? AND mode = 'nauka'",
        (user_id,)
    )
    seen_count = cursor.fetchone()[0]
    never_seen_count = max(0, total_cat_b - seen_count)

    # Mastered count evaluated in a single SQL query via ROW_NUMBER() window function
    cursor.execute(
        """
        WITH LatestEvent AS (
          SELECT question_id, is_correct,
                 ROW_NUMBER() OVER (PARTITION BY question_id ORDER BY id DESC) as rn
          FROM answer_events
          WHERE user_id = ? AND mode = 'nauka'
        ),
        CorrectDays AS (
          SELECT question_id
          FROM answer_events
          WHERE user_id = ? AND is_correct = 1 AND mode = 'nauka'
          GROUP BY question_id
          HAVING COUNT(DISTINCT DATE(created_at)) >= 2
        )
        SELECT COUNT(*)
        FROM CorrectDays cd
        JOIN LatestEvent le ON cd.question_id = le.question_id
        WHERE le.rn = 1 AND le.is_correct = 1
        """,
        (user_id, user_id)
    )
    mastered_count = cursor.fetchone()[0]
    conn.close()

    return {
        "total_cat_b": total_cat_b,
        "never_seen": never_seen_count,
        "seen": seen_count,
        "mastered": mastered_count
    }


# ---------------------------------------------------------------------------
# Classification Review Queue API
# ---------------------------------------------------------------------------

@router.get("/api/classification/review")
def get_review_queue(limit: int = Query(20)):
    """Questions with confidence < 0.8 OR media != null that need human triage."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT DISTINCT q.id, q.q_pl, q.type, q.media, q.media_kind,
               qc_a.value AS sugg_a, qc_a.confidence AS conf_a,
               qc_b.value AS sugg_b, qc_b.confidence AS conf_b
        FROM questions q
        LEFT JOIN question_classification qc_a ON q.id = qc_a.question_id AND qc_a.axis = 'A'
        LEFT JOIN question_classification qc_b ON q.id = qc_b.question_id AND qc_b.axis = 'B'
        WHERE q.categories LIKE '%"B"%'
          AND (qc_a.confidence < ? OR q.media IS NOT NULL OR qc_a.question_id IS NULL)
          AND q.id NOT IN (SELECT question_id FROM question_classification WHERE source = 'manual')
        LIMIT ?
        """,
        (LOW_CONFIDENCE_THRESHOLD, limit)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


@router.post("/api/classification/{question_id}")
def update_question_classification(question_id: int, req: ClassificationReviewRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Delete existing classifications for this question
    cursor.execute("DELETE FROM question_classification WHERE question_id = ?", (question_id,))

    # Insert Axis A
    cursor.execute(
        "INSERT OR REPLACE INTO question_classification (question_id, axis, value, confidence, source) VALUES (?, 'A', ?, 1.0, 'manual')",
        (question_id, req.axis_a)
    )

    # Insert Axis B
    cursor.execute(
        "INSERT OR REPLACE INTO question_classification (question_id, axis, value, confidence, source) VALUES (?, 'B', ?, 1.0, 'manual')",
        (question_id, req.axis_b)
    )

    # Insert Axis C (multi-label)
    for val in req.axis_c:
        cursor.execute(
            "INSERT OR REPLACE INTO question_classification (question_id, axis, value, confidence, source) VALUES (?, 'C', ?, 1.0, 'manual')",
            (question_id, val)
        )

    conn.commit()
    conn.close()
    return {"message": "Classification updated", "question_id": question_id, "source": "manual"}


# ---------------------------------------------------------------------------
# Dashboard & Elo Analytics Endpoints (Requires Auth)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Dashboard & Skill Analytics Endpoints (Requires Auth)
# ---------------------------------------------------------------------------

@router.get("/api/dashboard")
@router.get("/api/dashboard/summary")
def get_dashboard(request: Request):
    user_id = require_user_id(request)
    conn = get_db_connection()
    cursor = conn.cursor()

    # User profile & global skill theta
    cursor.execute("SELECT id, login, created_at FROM users WHERE id = ?", (user_id,))
    u_row = cursor.fetchone()
    if not u_row:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    user_data = dict(u_row)

    cursor.execute("SELECT theta, n FROM user_skill WHERE user_id = ? AND axis_value IS NULL", (user_id,))
    sk_row = cursor.fetchone()
    global_theta = sk_row["theta"] if sk_row else SKILL_INIT
    global_n = sk_row["n"] if sk_row else 0

    # Per axis-B skill theta dictionary
    cursor.execute("SELECT axis_value, theta, n FROM user_skill WHERE user_id = ? AND axis_value IS NOT NULL", (user_id,))
    per_axis_b_rows = cursor.fetchall()
    per_axis_b = {r["axis_value"]: round(r["theta"], 4) for r in per_axis_b_rows}

    # Total answered & accuracy in learning mode
    cursor.execute(
        """
        SELECT COUNT(*) AS total_answers,
               SUM(is_correct) AS correct_answers,
               AVG(time_ms) AS avg_time_ms
        FROM answer_events
        WHERE user_id = ? AND mode = 'nauka'
        """,
        (user_id,)
    )
    stats_row = dict(cursor.fetchone())
    total_answers = stats_row["total_answers"] or 0
    correct_answers = stats_row["correct_answers"] or 0
    accuracy = round((correct_answers / total_answers * 100), 1) if total_answers > 0 else 0.0

    # Coverage metrics (never_seen, seen, mastered)
    cursor.execute("SELECT COUNT(*) FROM questions WHERE categories LIKE '%\"B\"%'")
    total_cat_b = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT question_id) FROM answer_events WHERE user_id = ? AND mode = 'nauka'", (user_id,))
    seen_count = cursor.fetchone()[0]
    never_seen_count = max(0, total_cat_b - seen_count)

    cursor.execute(
        """
        WITH LatestEvent AS (
          SELECT question_id, is_correct,
                 ROW_NUMBER() OVER (PARTITION BY question_id ORDER BY id DESC) as rn
          FROM answer_events
          WHERE user_id = ? AND mode = 'nauka'
        ),
        CorrectDays AS (
          SELECT question_id
          FROM answer_events
          WHERE user_id = ? AND is_correct = 1 AND mode = 'nauka'
          GROUP BY question_id
          HAVING COUNT(DISTINCT DATE(created_at)) >= 2
        )
        SELECT COUNT(*)
        FROM CorrectDays cd
        JOIN LatestEvent le ON cd.question_id = le.question_id
        WHERE le.rn = 1 AND le.is_correct = 1
        """,
        (user_id, user_id)
    )
    mastered_count = cursor.fetchone()[0]

    # Domain Performance (Axis B breakdown)
    cursor.execute(
        """
        SELECT qc.value AS axis_b,
               COUNT(*) AS total_attempts,
               SUM(CASE WHEN ae.is_correct = 0 THEN 1 ELSE 0 END) AS error_count
        FROM answer_events ae
        JOIN question_classification qc ON ae.question_id = qc.question_id
        WHERE ae.user_id = ? AND qc.axis = 'B' AND ae.mode = 'nauka'
        GROUP BY qc.value
        ORDER BY error_count DESC, total_attempts DESC
        """,
        (user_id,)
    )
    domain_performance = []
    for r in cursor.fetchall():
        axis_val = r["axis_b"]
        d_err = r["error_count"] or 0
        d_tot = r["total_attempts"] or 0
        d_acc = round(((d_tot - d_err) / d_tot * 100), 1) if d_tot > 0 else 100.0
        d_theta = per_axis_b.get(axis_val, SKILL_INIT)
        domain_performance.append({
            "axis_b": axis_val,
            "theta": round(d_theta, 3),
            "error_count": d_err,
            "total_attempts": d_tot,
            "accuracy_pct": d_acc
        })

    # Repeats due (Questions answered incorrectly or hesitations)
    cursor.execute(
        """
        SELECT COUNT(DISTINCT question_id)
        FROM answer_events
        WHERE user_id = ? AND (is_correct = 0 OR time_ms > ?) AND mode = 'nauka'
        """,
        (user_id, HESITATION_THRESHOLD_MS)
    )
    repeats_due = cursor.fetchone()[0]

    # Reason split
    cursor.execute(
        """
        SELECT
          SUM(CASE WHEN is_correct = 0 AND time_ms < ? THEN 1 ELSE 0 END) AS slips,
          SUM(CASE WHEN is_correct = 0 AND time_ms >= ? THEN 1 ELSE 0 END) AS mistakes,
          SUM(CASE WHEN is_correct = 1 AND time_ms > ? THEN 1 ELSE 0 END) AS uncertainty
        FROM answer_events
        WHERE user_id = ? AND mode = 'nauka'
        """,
        (SLIP_THRESHOLD_MS, SLIP_THRESHOLD_MS, HESITATION_THRESHOLD_MS, user_id)
    )
    r_row = dict(cursor.fetchone())
    reason_split = {
        "slips": r_row.get("slips") or 0,
        "mistakes": r_row.get("mistakes") or 0,
        "uncertainty": r_row.get("uncertainty") or 0
    }

    # Skill history (theta trajectory capped to latest 100 points for dashboard latency)
    cursor.execute(
        """
        SELECT id, theta, created_at
        FROM skill_history
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 100
        """,
        (user_id,)
    )
    skill_history_rows = [dict(r) for r in cursor.fetchall()][::-1]

    # Hardest questions ordered by smoothed error % (p_err) and including attempts
    cursor.execute(
        """
        SELECT q.id, q.q_pl, q.scope, q.type,
               COALESCE(qs.attempts, 0) AS attempts,
               COALESCE(qs.wrong, 0) AS wrong,
               (CAST(COALESCE(qs.wrong, 0) AS REAL) + ?) / (CAST(COALESCE(qs.attempts, 0) AS REAL) + ? + ?) AS p_err
            FROM questions q
            LEFT JOIN question_stats qs ON q.id = qs.question_id
            WHERE q.categories LIKE '%"B"%'
            ORDER BY p_err DESC, attempts DESC, q.id ASC
            LIMIT 5
            """,
            (DIFF_ALPHA, DIFF_ALPHA, DIFF_BETA)
        )
    hardest_questions = []
    for r in cursor.fetchall():
        d = dict(r)
        d["error_pct"] = round(d["p_err"] * 100, 1)
        d["p_err"] = round(d["p_err"], 4)
        p_val = d["p_err"]
        d["b_q"] = round(math.log(p_val / (1.0 - p_val)), 2)
        hardest_questions.append(d)

    # Recent activity logs (recent 10 events)
    cursor.execute(
        """
        SELECT ae.id, ae.question_id, q.q_pl, ae.chosen, ae.is_correct, ae.time_ms, ae.created_at
        FROM answer_events ae
        JOIN questions q ON ae.question_id = q.id
        WHERE ae.user_id = ? AND ae.mode = 'nauka'
        ORDER BY ae.id DESC
        LIMIT 10
        """,
        (user_id,)
    )
    recent_activity = [dict(r) for r in cursor.fetchall()]

    # ---------------------------------------------------------------------------
    # Dashboard V3 Metrics (Today, Readiness, Streak, Weak Points)
    # ---------------------------------------------------------------------------
    import datetime
    today_date = datetime.date.today()
    pl_day_names = ["PONIEDZIAŁEK", "WTOREK", "ŚRODA", "CZWARTEK", "PIĄTEK", "SOBOTA", "NIEDZIELA"]
    today_pl_day = pl_day_names[today_date.weekday()]
    formatted_date = f"{today_pl_day} {today_date.strftime('%d.%m')}"

    # Today's answers
    cursor.execute(
        """
        SELECT COUNT(*) AS today_answers,
               COUNT(DISTINCT question_id) AS distinct_today
        FROM answer_events
        WHERE user_id = ? AND mode = 'nauka' AND DATE(created_at) = DATE('now')
        """,
        (user_id,)
    )
    today_row = cursor.fetchone()
    today_answers = today_row["today_answers"] if today_row else 0
    daily_goal = 20

    # New questions seen today
    cursor.execute(
        """
        SELECT COUNT(DISTINCT ae.question_id)
        FROM answer_events ae
        WHERE ae.user_id = ? AND ae.mode = 'nauka' AND DATE(ae.created_at) = DATE('now')
          AND NOT EXISTS (
            SELECT 1 FROM answer_events prev
            WHERE prev.user_id = ae.user_id AND prev.question_id = ae.question_id
              AND DATE(prev.created_at) < DATE('now')
          )
        """,
        (user_id,)
    )
    new_today_row = cursor.fetchone()
    new_today = new_today_row[0] if new_today_row else 0
    repeats_today = max(0, today_answers - new_today)
    remaining_q = max(0, daily_goal - today_answers)
    est_minutes = max(1, round(remaining_q * 0.6)) if today_answers < daily_goal else 0
    if today_answers == 0:
        est_minutes = 12

    # Exam Readiness calculation
    estimated_prob = 1.0 / (1.0 + math.exp(-(global_theta * 1.1 + 0.3)))
    estimated_points = 0 if total_answers == 0 else min(74, max(15, round(estimated_prob * 74)))

    cursor.execute(
        """
        SELECT score, max_score, passed, created_at
        FROM exam_checks
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 2
        """,
        (user_id,)
    )
    exam_rows = cursor.fetchall()
    latest_exam_score = exam_rows[0]["score"] if exam_rows else None
    prev_exam_score = exam_rows[1]["score"] if len(exam_rows) > 1 else None

    readiness_score = latest_exam_score if latest_exam_score is not None else estimated_points
    if total_answers == 0 and not exam_rows:
        readiness_score = 61

    score_delta = (latest_exam_score - prev_exam_score) if (latest_exam_score is not None and prev_exam_score is not None) else 6
    points_needed = max(0, 68 - readiness_score)

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM exam_checks
        WHERE user_id = ? AND created_at >= datetime('now', '-7 days')
        """,
        (user_id,)
    )
    exams_this_week = cursor.fetchone()[0] or 0
    if total_answers == 0 and not exam_rows:
        exams_this_week = 3

    # Streak & Weekly Activity (bounded to 30 days)
    cursor.execute(
        """
        SELECT DATE(created_at) as act_date, COUNT(*) as cnt
        FROM answer_events
        WHERE user_id = ? AND created_at >= datetime('now', '-30 days')
        GROUP BY DATE(created_at)
        ORDER BY act_date DESC
        LIMIT 30
        """,
        (user_id,)
    )
    activity_by_date = {r["act_date"]: r["cnt"] for r in cursor.fetchall()}

    current_streak = 0
    check_date = today_date
    if today_date.isoformat() in activity_by_date:
        current_streak += 1
        check_date -= datetime.timedelta(days=1)
    else:
        yesterday = today_date - datetime.timedelta(days=1)
        if yesterday.isoformat() in activity_by_date:
            check_date = yesterday
        else:
            check_date = None

    if check_date:
        while check_date.isoformat() in activity_by_date:
            current_streak += 1
            check_date -= datetime.timedelta(days=1)

    if not activity_by_date:
        current_streak = 0
        max_streak = 0
        avg_daily = 0
    else:
        max_streak = max(current_streak, len(activity_by_date))
        avg_daily = round(sum(activity_by_date.values()) / max(1, len(activity_by_date)))

    monday = today_date - datetime.timedelta(days=today_date.weekday())
    day_abbrs = ["pn", "wt", "śr", "cz", "pt", "so", "nd"]
    week_days = []
    for i in range(7):
        d_i = monday + datetime.timedelta(days=i)
        d_str = d_i.isoformat()
        has_answers = activity_by_date.get(d_str, 0)
        is_today = (d_i == today_date)
        is_future = (d_i > today_date)
        completed = (has_answers >= 5)
        week_days.append({
            "day_short": day_abbrs[i],
            "date": d_str,
            "completed": completed,
            "is_today": is_today,
            "is_future": is_future,
            "answers_count": has_answers
        })

    # Weak points mapping
    domain_map = {
        "znaki_i_sygnaly": "znaki i sygnały",
        "pierwszenstwo": "pierwszeństwo",
        "manewry_i_pozycja": "manewry i pozycja",
        "predkosc_i_odleglosci": "prędkość i odstępy",
        "technika_pojazdu": "obsługa pojazdu",
        "administracja_i_kary": "przepisy ruchu",
        "pierwsza_pomoc": "pierwsza pomoc",
        "ekologia": "ekologia",
    }

    sorted_domains = sorted(
        domain_performance,
        key=lambda d: (d["accuracy_pct"], -d["error_count"])
    )
    if not sorted_domains or total_answers == 0:
        # Starter domains for fresh users
        weak_points = [
            {"axis_b": "znaki_i_sygnaly", "label": "znaki i sygnały", "accuracy_pct": 0, "error_count": 0, "theta": 0.0},
            {"axis_b": "pierwszenstwo", "label": "pierwszeństwo", "accuracy_pct": 0, "error_count": 0, "theta": 0.0},
            {"axis_b": "manewry_i_pozycja", "label": "manewry i pozycja", "accuracy_pct": 0, "error_count": 0, "theta": 0.0},
        ]
    else:
        weak_points = []
        for d in sorted_domains[:3]:
            weak_points.append({
                "axis_b": d["axis_b"],
                "label": domain_map.get(d["axis_b"], d["axis_b"].replace("_", " ")),
                "accuracy_pct": d["accuracy_pct"],
                "error_count": d["error_count"],
                "theta": d["theta"]
            })

    conn.close()

    return {
        "user": {
            "id": user_data["id"],
            "login": user_data["login"],
            "skill_theta": round(global_theta, 3),
            "n": global_n
        },
        "skill_theta": round(global_theta, 3),
        "per_axis_b": per_axis_b,
        "metrics": {
            "total_answers": total_answers,
            "correct_answers": correct_answers,
            "accuracy_percent": accuracy,
            "mastered_count": mastered_count,
            "avg_time_ms": round(stats_row["avg_time_ms"] or 0, 0)
        },
        "coverage": {
            "total_cat_b": total_cat_b,
            "never_seen": never_seen_count,
            "seen": seen_count,
            "mastered": mastered_count
        },
        "domain_performance": domain_performance,
        "repeats_due": repeats_due,
        "reason_split": reason_split,
        "skill_history": skill_history_rows,
        "hardest_questions": hardest_questions,
        "recent_activity": recent_activity,
        "today": {
            "today_answers": today_answers,
            "daily_goal": daily_goal,
            "repeats_today": repeats_today,
            "new_today": new_today,
            "est_minutes": est_minutes,
            "formatted_date": formatted_date
        },
        "readiness": {
            "score": readiness_score,
            "max_score": 74,
            "pass_threshold": 68,
            "score_delta": score_delta,
            "points_needed": points_needed,
            "exams_this_week": exams_this_week
        },
        "streak": {
            "current_streak": current_streak,
            "max_streak": max_streak,
            "avg_daily_questions": avg_daily,
            "week_days": week_days
        },
        "weak_points": weak_points
    }


@router.get("/api/dashboard/rating_history")
@router.get("/api/dashboard/skill_history")
def get_skill_history(request: Request):
    user_id = require_user_id(request)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, theta, created_at
        FROM skill_history
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 100
        """,
        (user_id,)
    )
    rows = [dict(r) for r in cursor.fetchall()][::-1]
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Weekly Readiness Check API (Tygodniowy Sprawdzian - Readiness Metric)
# ---------------------------------------------------------------------------

class ExamAnswerItem(BaseModel):
    question_id: int
    chosen: str
    time_ms: int = 0

class ExamSubmissionRequest(BaseModel):
    answers: List[ExamAnswerItem]
    time_seconds: int = 0


@router.post("/api/exam/start")
def start_exam_check(request: Request):
    """
    Generates a 32-question official exam simulation (20 basic + 12 specialized)
    with total 74 points and pass threshold 68 points.
    """
    user_id = require_user_id(request)
    conn = get_db_connection()
    try:
        exam_data = generate_exam_sheet(conn)
        return {
            "questions": exam_data["questions"],
            "total_questions": exam_data["total_questions"],
            "max_score": exam_data["max_score"],
            "pass_threshold": exam_data["pass_threshold"]
        }
    finally:
        conn.close()



@router.post("/api/exam/submit")
def submit_exam_check(req: ExamSubmissionRequest, request: Request):
    """
    Grades a 32-question readiness check, logs to exam_checks, and returns readiness metrics.
    """
    user_id = require_user_id(request)
    conn = get_db_connection()
    cursor = conn.cursor()

    q_ids = [item.question_id for item in req.answers]
    if not q_ids:
        conn.close()
        raise HTTPException(status_code=400, detail="No answers submitted")

    placeholders = ",".join(["?"] * len(q_ids))
    cursor.execute(f"SELECT id, points, correct FROM questions WHERE id IN ({placeholders})", q_ids)
    q_map = {r["id"]: dict(r) for r in cursor.fetchall()}

    score = 0
    correct_count = 0
    details = []

    for item in req.answers:
        q_data = q_map.get(item.question_id)
        if not q_data:
            continue
        correct_ans = q_data["correct"].strip().upper()
        chosen = item.chosen.strip().upper()
        is_corr = (chosen == correct_ans)
        pts = q_data["points"] if is_corr else 0
        if is_corr:
            score += pts
            correct_count += 1

        details.append({
            "question_id": item.question_id,
            "chosen": chosen,
            "correct": correct_ans,
            "is_correct": is_corr,
            "points_earned": pts,
            "time_ms": item.time_ms
        })

    passed = 1 if score >= 68 else 0

    cursor.execute(
        """
        INSERT INTO exam_checks (user_id, score, max_score, passed, time_seconds, details_json, created_at)
        VALUES (?, ?, 74, ?, ?, ?, datetime('now'))
        """,
        (user_id, score, passed, req.time_seconds, json.dumps(details))
    )
    exam_id = cursor.lastrowid

    # Log each individual question answer from the exam into answer_events with mode='sprawdzian'
    exam_session_id = f"exam:{exam_id}"
    for d in details:
        cursor.execute(
            """
            INSERT INTO answer_events (user_id, question_id, chosen, is_correct, time_ms, session_id, mode, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'sprawdzian', datetime('now'))
            """,
            (user_id, d["question_id"], d["chosen"], 1 if d["is_correct"] else 0, d["time_ms"], exam_session_id)
        )

    conn.commit()
    conn.close()

    return {
        "exam_id": exam_id,
        "score": score,
        "max_score": 74,
        "passed": bool(passed),
        "correct_count": correct_count,
        "total_questions": len(req.answers),
        "time_seconds": req.time_seconds,
        "details": details
    }


@router.get("/api/exam/history")
def get_exam_history(request: Request):
    user_id = require_user_id(request)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, score, max_score, passed, time_seconds, created_at
        FROM exam_checks
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 20
        """,
        (user_id,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows



