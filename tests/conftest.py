"""
Root Pytest Configuration for Prawko B.
Resets authentication rate limit state between test functions to avoid test bleed.
"""

import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.auth import reset_rate_limits


@pytest.fixture(autouse=True)
def reset_auth_rate_limits_each_test():
    """Ensure rate limit memory is clean for each test."""
    reset_rate_limits()
    yield
    reset_rate_limits()
