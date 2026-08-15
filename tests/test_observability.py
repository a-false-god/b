"""
Observability Tests (Task S6).

Covers:
- GET /healthz unauthenticated endpoint (status, db_ok, questions_count).
- Request-logging middleware latency & status logging.
- Frontend ErrorBoundary definition & structure.
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app
from app.db import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_healthz_endpoint_success():
    """Verify /healthz returns 200 with db_ok=True and accurate questions_count."""
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "ok"
    assert data["db_ok"] is True
    assert isinstance(data["questions_count"], int)
    assert data["questions_count"] >= 2135


def test_request_logging_middleware(capsys):
    """Verify that request-logging middleware logs method, path, and duration to stdout."""
    res = client.get("/healthz")
    assert res.status_code == 200

    captured = capsys.readouterr()
    assert "[GET] /healthz -> 200" in captured.out
    assert "ms)" in captured.out


def test_error_boundary_component_structure():
    """Verify that ErrorBoundary component file exists and defines error handling."""
    eb_file = PROJECT_ROOT / "frontend" / "src" / "components" / "common" / "ErrorBoundary.tsx"
    assert eb_file.exists(), "ErrorBoundary.tsx not found"

    content = eb_file.read_text(encoding="utf-8")
    assert "class ErrorBoundary extends Component" in content
    assert "getDerivedStateFromError" in content
    assert "componentDidCatch" in content
    assert "Coś poszło nie tak" in content
