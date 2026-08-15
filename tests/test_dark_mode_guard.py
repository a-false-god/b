"""
Test suite guarding dark mode CSS custom properties and theme tokens.

Two-layer guard:
1. Always-ON static analysis test: Parses index.css to verify that every variable
   used via var(--x) is defined in BOTH :root and .dark blocks. (Runs instantly,
   Docker-safe, no browser required).
2. Dynamic computed style test (Playwright): Checks that in .dark mode, computed body
   color resolves to hsl(var(--foreground)) and not unstyled rgb(0, 0, 0), dynamically
   comparing with the computed token value rather than hardcoded RGB constants.
"""

import os
import re
import sys
import threading
import time
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

INDEX_CSS_PATH = PROJECT_ROOT / "frontend" / "src" / "index.css"


def extract_css_block(css_content: str, selector: str) -> str:
    """Extract block content for a given CSS selector (e.g. ':root' or '.dark')."""
    pattern = re.compile(rf"{re.escape(selector)}\s*\{{([^}}]+)\}}", re.DOTALL)
    match = pattern.search(css_content)
    return match.group(1) if match else ""


def extract_variables(block_content: str) -> set:
    """Extract all --variable-name declarations from a CSS block."""
    var_pattern = re.compile(r"(--[a-zA-Z0-9_-]+)\s*:")
    return set(var_pattern.findall(block_content))


def extract_variable_usages(css_content: str) -> set:
    """Extract all var(--variable-name) usages in CSS content."""
    usage_pattern = re.compile(r"var\(\s*(--[a-zA-Z0-9_-]+)")
    return set(usage_pattern.findall(css_content))


# ==============================================================================
# Layer 1: Always-ON Static Token Guard Test (Lightweight, No Browser Required)
# ==============================================================================

def test_static_css_token_definitions_root_and_dark():
    """
    Verify statically that:
    1. index.css exists and defines :root and .dark blocks.
    2. --foreground is explicitly defined in both :root and .dark.
    3. Every CSS variable referenced via var(--var_name) is defined in BOTH :root and .dark.
    """
    assert INDEX_CSS_PATH.exists(), f"index.css not found at {INDEX_CSS_PATH}"
    content = INDEX_CSS_PATH.read_text(encoding="utf-8")

    root_block = extract_css_block(content, ":root")
    dark_block = extract_css_block(content, ".dark")

    assert root_block, "CSS :root block not found in index.css"
    assert dark_block, "CSS .dark block not found in index.css"

    root_vars = extract_variables(root_block)
    dark_vars = extract_variables(dark_block)

    # Specific guard for the --foreground incident
    assert "--foreground" in root_vars, "--foreground missing from :root in index.css"
    assert "--foreground" in dark_vars, "--foreground missing from .dark in index.css"
    assert "--background" in root_vars, "--background missing from :root in index.css"
    assert "--background" in dark_vars, "--background missing from .dark in index.css"

    # Verify all var(--...) usages are defined in both scopes
    used_vars = extract_variable_usages(content)
    missing_in_root = used_vars - root_vars
    missing_in_dark = used_vars - dark_vars

    assert not missing_in_root, f"CSS variables used via var() but missing in :root: {missing_in_root}"
    assert not missing_in_dark, f"CSS variables used via var() but missing in .dark: {missing_in_dark}"


# ==============================================================================
# Layer 2: Dynamic Computed Style Test (Skipped in headless environments without browsers)
# ==============================================================================

playwright_available = False
try:
    import playwright  # noqa: F401
    from playwright.sync_api import sync_playwright
    playwright_available = True
except ImportError:
    playwright_available = False


class UvicornTestServer:
    def __init__(self, app, host="127.0.0.1", port=8124):
        self.host = host
        self.port = port
        self.app = app
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


@pytest.fixture(scope="module")
def server():
    if not playwright_available or os.environ.get("SKIP_PLAYWRIGHT_TESTS") == "1":
        pytest.skip("Playwright tests disabled or not installed")
    from app.main import app
    srv = UvicornTestServer(app, host="127.0.0.1", port=8124)
    srv.start()
    yield f"http://{srv.host}:{srv.port}"
    srv.stop()


@pytest.mark.skipif(not playwright_available or os.environ.get("SKIP_PLAYWRIGHT_TESTS") == "1",
                    reason="Playwright not installed or running inside minimal container")
def test_dynamic_dark_mode_computed_token_guard(server):
    """
    Assert that when .dark is active, computed body text color dynamically equals
    the computed hsl(var(--foreground)) token value and is not rgb(0, 0, 0).
    Does NOT hardcode specific RGB values.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Browser launch failed (container environment): {exc}")

        page = browser.new_page()
        page.goto(f"{server}/", wait_until="domcontentloaded")

        # Switch to dark mode
        page.evaluate("""() => {
            document.documentElement.classList.remove('light');
            document.documentElement.classList.add('dark');
        }""")

        # Compare body computed color with a test probe styled with hsl(var(--foreground))
        res = page.evaluate("""() => {
            const bodyColor = window.getComputedStyle(document.body).color;
            const probe = document.createElement('div');
            probe.style.color = 'hsl(var(--foreground))';
            document.body.appendChild(probe);
            const tokenColor = window.getComputedStyle(probe).color;
            probe.remove();
            
            const rawToken = window.getComputedStyle(document.documentElement).getPropertyValue('--foreground').trim();
            return { bodyColor, tokenColor, rawToken };
        }""")

        browser.close()

        assert res["rawToken"] != "", "--foreground token value must not be empty in .dark"
        assert res["bodyColor"] != "rgb(0, 0, 0)", "Dark mode body color must not fall back to rgb(0, 0, 0)"
        assert res["bodyColor"] == res["tokenColor"], (
            f"Body text color ({res['bodyColor']}) does not match computed hsl(var(--foreground)) ({res['tokenColor']})"
        )
