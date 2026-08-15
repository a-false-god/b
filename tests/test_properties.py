"""
Property-based tests for algorithmic core (Task S3).
Uses Hypothesis to verify mathematical and compositional invariants across >=200 examples per property.
"""

import collections
import math
import sys
from pathlib import Path
import pytest
from hypothesis import given, settings, strategies as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import get_db_connection, init_db
from app.config import SKILL_LR0, DIFF_ALPHA, DIFF_BETA
from app.skill import calc_question_difficulty, calc_skill_update
from app.session import interleave_questions, get_session_queue, generate_exam_sheet, AXIS_B_DOMAINS


# ==============================================================================
# 1. app/skill.py Invariants (Asymmetric Rasch Engine)
# ==============================================================================

@settings(max_examples=200)
@given(
    theta=st.floats(min_value=-15.0, max_value=15.0, allow_nan=False, allow_infinity=False),
    n=st.integers(min_value=0, max_value=50000),
    b_q=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    is_correct=st.booleans()
)
def test_property_skill_update_monotonicity_and_step(theta, n, b_q, is_correct):
    """
    Invariants:
    1. Correct on any item strictly increases theta (delta > 0).
    2. Wrong on any item strictly decreases theta (delta < 0).
    3. n always increases by exactly 1.
    4. new_theta and delta are always finite real numbers.
    """
    new_theta, new_n, delta_theta = calc_skill_update(theta, n, b_q, is_correct)

    assert new_n == n + 1
    assert math.isfinite(new_theta)
    assert math.isfinite(delta_theta)

    if is_correct:
        assert delta_theta > 0.0, f"Expected delta > 0 for correct answer, got {delta_theta}"
        assert new_theta > theta, f"Expected theta to increase on correct answer"
    else:
        assert delta_theta < 0.0, f"Expected delta < 0 for wrong answer, got {delta_theta}"
        assert new_theta < theta, f"Expected theta to decrease on wrong answer"


@settings(max_examples=200)
@given(
    initial_theta=st.floats(min_value=-3.0, max_value=3.0, allow_nan=False, allow_infinity=False),
    events=st.lists(
        st.tuples(
            st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
            st.booleans()
        ),
        min_size=1,
        max_size=100
    )
)
def test_property_skill_trajectory_bounded(initial_theta, events):
    """
    Invariant: theta remains bounded and finite under any realistic sequence of answer events.
    """
    theta = initial_theta
    n = 0
    for b_q, is_correct in events:
        theta, n, _ = calc_skill_update(theta, n, b_q, is_correct)
        assert math.isfinite(theta)
        assert -25.0 < theta < 25.0, f"Theta drifted out of bounds: {theta}"

    assert n == len(events)


@settings(max_examples=200)
@given(
    attempts=st.integers(min_value=0, max_value=100000),
    wrong_ratio=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
def test_property_laplace_smoothed_difficulty_never_zero_or_one(attempts, wrong_ratio):
    """
    Invariant: Laplace-smoothed error probability p_err strictly stays in (0, 1)
    and log-odds difficulty b_q remains finite for all attempts >= wrong >= 0.
    """
    wrong = int(attempts * wrong_ratio)
    assert 0 <= wrong <= attempts

    p_err, b_q = calc_question_difficulty(attempts, wrong)

    assert 0.0 < p_err < 1.0, f"p_err {p_err} reached boundary [0, 1]"
    assert math.isfinite(b_q), f"b_q {b_q} is not finite"

    # Monotonicity: higher wrong at same attempts yields higher p_err
    if attempts > 0 and wrong < attempts:
        p_err_higher, b_q_higher = calc_question_difficulty(attempts, wrong + 1)
        assert p_err_higher > p_err
        assert b_q_higher > b_q


# ==============================================================================
# 2. app/session.py Invariants (Session Composition & Interleaving)
# ==============================================================================

@settings(max_examples=200)
@given(
    questions=st.lists(
        st.fixed_dictionaries({
            "id": st.integers(min_value=1, max_value=100000),
            "axis_b": st.sampled_from(AXIS_B_DOMAINS)
        }),
        min_size=1,
        max_size=60
    )
)
def test_property_interleave_questions_domains(questions):
    """
    Invariants for interleave_questions:
    1. Output contains the exact same multiset of items as input (length and IDs preserved).
    2. When multiple distinct domains exist, no domain appears >3 times consecutively
       while questions from other domains are still available.
    """
    interleaved = interleave_questions(questions)
    assert len(interleaved) == len(questions)

    in_ids = [q["id"] for q in questions]
    out_ids = [q["id"] for q in interleaved]
    assert collections.Counter(in_ids) == collections.Counter(out_ids)

    # Check consecutive domain runs
    distinct_domains = {q["axis_b"] for q in questions}
    if len(distinct_domains) > 1:
        consecutive_count = 1
        for i in range(1, len(interleaved)):
            if interleaved[i]["axis_b"] == interleaved[i - 1]["axis_b"]:
                consecutive_count += 1
            else:
                consecutive_count = 1

            # If consecutive count > 3, it should only be because no other domain had questions left
            if consecutive_count > 3:
                # All remaining items after index i should belong only to this domain
                remaining_domains = {x["axis_b"] for x in interleaved[i:]}
                assert len(remaining_domains) == 1, (
                    f"More than 3 consecutive items from {interleaved[i]['axis_b']} "
                    f"while other domains {remaining_domains} were present"
                )


@settings(max_examples=200)
@given(
    limit=st.integers(min_value=1, max_value=50),
    user_id=st.integers(min_value=1, max_value=9999)
)
def test_property_session_queue_invariants(limit, user_id):
    """
    Invariants for get_session_queue:
    1. Output size is at most limit.
    2. Zero duplicate question IDs in the queue.
    3. All questions belong to Category B.
    """
    init_db()
    conn = get_db_connection()
    try:
        queue = get_session_queue(conn, user_id=user_id, mode="auto", limit=limit)
        assert len(queue) <= limit

        q_ids = [q["id"] for q in queue]
        assert len(q_ids) == len(set(q_ids)), f"Duplicate question IDs found in session queue: {q_ids}"

        for q in queue:
            cats = q.get("categories")
            if isinstance(cats, list):
                assert "B" in cats, f"Non-Category B question in queue: {q['id']}"
    finally:
        conn.close()


# ==============================================================================
# 3. Exam Sheet Generator Invariants
# ==============================================================================

@settings(max_examples=200)
@given(seed=st.integers(min_value=1, max_value=1000000))
def test_property_exam_sheet_composition(seed):
    """
    Invariants for Official Category B Exam generation:
    1. Exactly 32 questions total.
    2. Exactly 20 Basic ('PODSTAWOWY') + 12 Specialist ('SPECJALISTYCZNY').
    3. Pass threshold is 68 points.
    4. Max score is 74 points.
    5. Zero duplicate question IDs.
    """
    init_db()
    conn = get_db_connection()
    try:
        exam_data = generate_exam_sheet(conn)
        questions = exam_data["questions"]
        basic = exam_data["basic_questions"]
        spec = exam_data["spec_questions"]

        assert exam_data["total_questions"] == 32
        assert len(questions) == 32, f"Expected 32 items, got {len(questions)}"
        assert len(basic) == 20, f"Expected 20 basic items, got {len(basic)}"
        assert len(spec) == 12, f"Expected 12 specialist items, got {len(spec)}"

        assert exam_data["max_score"] == 74
        assert exam_data["pass_threshold"] == 68

        ids = [q["id"] for q in questions]
        assert len(ids) == len(set(ids)), f"Duplicate question IDs found in exam: {ids}"
    finally:
        conn.close()

