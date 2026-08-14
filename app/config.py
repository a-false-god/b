"""
Configuration constants for Prawko B MVP.
Defines analytics thresholds and classification defaults.
"""

# Reason split thresholds (Section 9.6)
# Slip: wrong answer AND time_ms < 8000
# Mistake: wrong answer AND time_ms >= 8000
# Uncertainty: correct answer AND time_ms > 15000
SLIP_THRESHOLD_MS = 8000
HESITATION_THRESHOLD_MS = 15000

# Rating & Skill Engine configuration (M6.1 Asymmetric Rasch Model)
SKILL_INIT = 0.0      # user ability theta, logit scale
SKILL_LR0 = 0.5       # initial learning rate (decays with n)
DIFF_ALPHA = 2.0      # Beta prior, wrong side
DIFF_BETA = 2.0       # Beta prior, correct side

# Classification review threshold (Section 6)
LOW_CONFIDENCE_THRESHOLD = 0.80
MEDIA_CONFIDENCE_CAP = 0.60

