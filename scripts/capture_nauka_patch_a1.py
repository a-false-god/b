"""
Capture comprehensive Nauka review matrix for Patch A1:
- 2 Themes: dark, light
- 2 Viewports: desktop (1280x800), mobile (390x844)
- 2 States: neutral (unanswered), post_answer (answered)
- 2 Question types: TN, ABC
Total = 16 screenshots
"""

import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from playwright.sync_api import sync_playwright
from app.main import app
from app.db import init_db

ARTIFACT_DIR = Path(r"C:\Users\idsid\.gemini\antigravity-ide\brain\1ca08345-52d5-43d8-bb10-30bc2b993a31")
OUT_DIR = ARTIFACT_DIR / "nauka_patch_a1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MOCK_QUESTION_TN = {
    "id": 1003,
    "lp": 1003,
    "scope": "PODSTAWOWY",
    "points": 3,
    "type": "TN",
    "correct": "T",
    "media": "1003.jpg",
    "media_kind": "image",
    "categories": ["B"],
    "q_pl": "Czy w przedstawionej sytuacji masz obowiązek ustąpić pierwszeństwa pojazdowi nadjeżdżającemu z prawej strony?",
    "a_pl": "TAK",
    "b_pl": "NIE",
    "c_pl": "",
    "axis_a": "zastosowanie",
    "axis_b": "pierwszenstwo"
}

MOCK_QUESTION_ABC = {
    "id": 2045,
    "lp": 2045,
    "scope": "SPECJALISTYCZNY",
    "points": 2,
    "type": "ABC",
    "correct": "B",
    "media": None,
    "media_kind": None,
    "categories": ["B"],
    "q_pl": "Jaka jest dopuszczalna prędkość zespołu pojazdów na drodze ekspresowej dwujezdniowej?",
    "a_pl": "100 km/h.",
    "b_pl": "80 km/h.",
    "c_pl": "70 km/h.",
    "axis_a": "pamiec",
    "axis_b": "predkosc_i_odleglosci"
}

MOCK_ANSWER_RESPONSE_TN = {
    "is_correct": 1,
    "correct_answer": "T",
    "explanation": "Na skrzyżowaniu równorzędnym obowiązuje **reguła prawej ręki** (art. 25 ust. 1 ustawy Prawo o ruchu drogowym). Należy ustąpić pierwszeństwa pojazdowi zbliżającemu się z prawej strony.",
    "legal_basis": "Art. 25 ust. 1 ustawy z dnia 20 czerwca 1997 r. Prawo o ruchu drogowym",
    "source": "llm",
    "time_ms": 3200
}

MOCK_ANSWER_RESPONSE_ABC = {
    "is_correct": 1,
    "correct_answer": "B",
    "explanation": "Dopuszczalna prędkość zespołu pojazdów na autostradzie i drodze ekspresowej wynosi **80 km/h** (art. 20 ust. 3 pkt 1 ustawy Prawo o ruchu drogowym).",
    "legal_basis": "Art. 20 ust. 3 pkt 1 ustawy Prawo o ruchu drogowym",
    "source": "llm",
    "time_ms": 2800
}

MOCK_DASHBOARD = {
    "user": {"id": 1, "login": "tester_ritual"},
    "metrics": {"total_answers": 240, "correct_answers": 215, "accuracy_pct": 89.6}
}

class TestServer:
    def __init__(self, app, host="127.0.0.1", port=8140):
        self.host = host
        self.port = port
        self.app = app
        self.server = None
        self.thread = None

    def start(self):
        import uvicorn
        import threading
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

THEMES = ["dark", "light"]
VIEWPORTS = {
    "desktop": {"width": 1280, "height": 800},
    "mobile": {"width": 390, "height": 844}
}

def capture_matrix():
    init_db()
    srv = TestServer(app, host="127.0.0.1", port=8140)
    srv.start()
    server_url = f"http://{srv.host}:{srv.port}"
    print(f"Nauka preview server started at {server_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for theme in THEMES:
            for vp_name, vp_size in VIEWPORTS.items():
                for q_variant, (q_data, ans_data) in [("tn", (MOCK_QUESTION_TN, MOCK_ANSWER_RESPONSE_TN)), ("abc", (MOCK_QUESTION_ABC, MOCK_ANSWER_RESPONSE_ABC))]:
                    context = browser.new_context(viewport=vp_size)
                    page = context.new_page()

                    # Set up route mocks
                    page.route("**/api/session/next*", lambda route: route.fulfill(
                        status=200, content_type="application/json", body=json.dumps([q_data])
                    ))
                    page.route("**/api/questions*", lambda route: route.fulfill(
                        status=200, content_type="application/json", body=json.dumps([q_data])
                    ))
                    page.route("**/api/dashboard/summary*", lambda route: route.fulfill(
                        status=200, content_type="application/json", body=json.dumps(MOCK_DASHBOARD)
                    ))
                    page.route("**/api/answers*", lambda route: route.fulfill(
                        status=200, content_type="application/json", body=json.dumps(ans_data)
                    ))

                    def apply_theme():
                        page.evaluate(f"""(th) => {{
                            localStorage.setItem('prawko_theme', th);
                            if (th === 'dark') {{
                                document.documentElement.classList.add('dark');
                                document.documentElement.classList.remove('light');
                            }} else {{
                                document.documentElement.classList.remove('dark');
                                document.documentElement.classList.add('light');
                            }}
                        }}""", theme)

                    # 1. Neutral (unanswered) state
                    page.goto(f"{server_url}/nauka", wait_until="networkidle")
                    page.evaluate("""() => {
                        localStorage.setItem('prawko_user', JSON.stringify({ id: 1, login: 'tester_ritual' }));
                    }""")
                    apply_theme()
                    page.wait_for_timeout(400)
                    neutral_filename = f"nauka_{q_variant}_neutral_{theme}_{vp_name}.png"
                    page.screenshot(path=str(OUT_DIR / neutral_filename))
                    print(f"Captured: {neutral_filename}")

                    # 2. Post-answer state
                    if q_variant == "tn":
                        btn = page.locator("button:has-text('TAK'), button:has-text('T')").first
                    else:
                        btn = page.locator("button:has-text('80 km/h'), button:has-text('B')").first
                    
                    if btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(500)
                    
                    post_filename = f"nauka_{q_variant}_post_answer_{theme}_{vp_name}.png"
                    page.screenshot(path=str(OUT_DIR / post_filename))
                    print(f"Captured: {post_filename}")

                    context.close()

        browser.close()
    srv.stop()
    print("All 16 Nauka Patch A1 screenshots captured successfully.")

if __name__ == "__main__":
    capture_matrix()
