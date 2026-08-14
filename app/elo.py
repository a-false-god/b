"""
Elo rating system calculations and tier helper functions for Prawko B.
"""

import math
from typing import Tuple, Dict, Any

DEFAULT_ELO = 1500
DEFAULT_K_FACTOR = 32.0


def calc_expected_score(user_elo: float, question_elo: float) -> float:
    """Calculate expected probability of user correctly answering the question."""
    return 1.0 / (1.0 + math.pow(10.0, (question_elo - user_elo) / 400.0))


def calc_elo_updates(
    user_elo: int,
    question_elo: int,
    is_correct: bool,
    k_factor: float = DEFAULT_K_FACTOR
) -> Tuple[int, int, int, int]:
    """
    Calculate new Elo ratings and deltas for user and question.
    Returns (new_user_elo, delta_user, new_question_elo, delta_question).
    """
    expected_u = calc_expected_score(user_elo, question_elo)
    actual_u = 1.0 if is_correct else 0.0

    delta_u = round(k_factor * (actual_u - expected_u))
    delta_q = -delta_u

    new_user_elo = max(100, user_elo + delta_u)
    new_question_elo = max(100, question_elo + delta_q)

    return new_user_elo, delta_u, new_question_elo, delta_q


def get_rank_tier(user_elo: int) -> Dict[str, Any]:
    """Return rank title, icon, color, and level tier for a given Elo rating."""
    if user_elo < 1400:
        return {"title": "Początkujący", "icon": "🔰", "color": "#9e9e9e", "tier": 1}
    elif user_elo < 1600:
        return {"title": "Kierowca", "icon": "🚗", "color": "#4caf50", "tier": 2}
    elif user_elo < 1800:
        return {"title": "Adept", "icon": "🏅", "color": "#2196f3", "tier": 3}
    elif user_elo < 2000:
        return {"title": "Ekspert", "icon": "🌟", "color": "#9c27b0", "tier": 4}
    else:
        return {"title": "Mistrz Egzaminu", "icon": "👑", "color": "#ff9800", "tier": 5}
