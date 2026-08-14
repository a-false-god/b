"""
M6.1 Rating engine revision: Asymmetric Rasch skill model & question difficulty.
"""

import math
from typing import Tuple
from app.config import SKILL_INIT, SKILL_LR0, DIFF_ALPHA, DIFF_BETA


def calc_question_difficulty(attempts: int, wrong: int) -> Tuple[float, float]:
    """
    Calculate question error probability (p_err) and log-odds difficulty (b_q).
    p_err = (wrong + DIFF_ALPHA) / (attempts + DIFF_ALPHA + DIFF_BETA)
    b_q   = ln(p_err / (1 - p_err))
    """
    p_err = (wrong + DIFF_ALPHA) / (attempts + DIFF_ALPHA + DIFF_BETA)
    b_q = math.log(p_err / (1.0 - p_err))
    return p_err, b_q


def calc_skill_update(
    theta: float,
    n: int,
    b_q: float,
    is_correct: bool
) -> Tuple[float, int, float]:
    """
    Calculate updated user ability theta and n.
    P     = 1 / (1 + exp(-(theta - b_q)))   # predicted P(correct)
    eta   = SKILL_LR0 / sqrt(1 + n)         # decaying step
    theta = theta + eta * (S - P)           # S = 1 if correct else 0
    n    += 1
    Returns (new_theta, new_n, delta_theta).
    """
    P = 1.0 / (1.0 + math.exp(-(theta - b_q)))
    eta = SKILL_LR0 / math.sqrt(1.0 + n)
    S = 1.0 if is_correct else 0.0
    delta_theta = eta * (S - P)
    new_theta = theta + delta_theta
    new_n = n + 1
    return new_theta, new_n, delta_theta
