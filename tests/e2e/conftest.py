"""
Playwright E2E Fixtures & Server Lifecycle (Task S5).
Gated cleanly: skipped if SKIP_PLAYWRIGHT_TESTS=1 or playwright is not available.
"""

import os
import sys
import time
import threading
import sqlite3
import uuid
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def pytest_addoption(parser):
    parser.addoption(
        "--update-baseline",
        action="store_true",
        default=False,
        help="Update visual regression baseline images",
    )

playwright_available = False
try:
    import playwright  # noqa: F401
    from playwright.sync_api import sync_playwright
    playwright_available = True
except ImportError:
    playwright_available = False

from app.main import app
from app.db import init_db, DB_PATH
from app.auth import hash_password


class UvicornE2EServer:
    def __init__(self, fastapi_app, host="127.0.0.1", port=8128):
        self.host = host
        self.port = port
        self.app = fastapi_app
        self.server = None
        self.thread = None

    def start(self):
        import uvicorn
        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="warning")
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        time.sleep(1.0)

    def stop(self):
        if self.server:
            self.server.should_exit = True
            if self.thread:
                self.thread.join(timeout=3.0)


@pytest.fixture(scope="session")
def e2e_server():
    if not playwright_available or os.environ.get("SKIP_PLAYWRIGHT_TESTS") == "1":
        pytest.skip("Playwright tests disabled or not installed")

    init_db()
    srv = UvicornE2EServer(app, host="127.0.0.1", port=8128)
    srv.start()
    base_url = f"http://{srv.host}:{srv.port}"
    yield base_url
    srv.stop()


@pytest.fixture(scope="function")
def authenticated_user(e2e_server):
    """Creates a dedicated user in DB and returns credentials dict."""
    login = f"e2e_user_{uuid.uuid4().hex[:8]}"
    password = "E2ePassword123!"
    pw_hash = hash_password(password)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (login, password_hash) VALUES (?, ?)", (login, pw_hash))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    return {
        "id": user_id,
        "login": login,
        "password": password,
        "server_url": e2e_server
    }
