"""
Capture all 24 screenshot permutations (6 surfaces x 2 themes x 2 viewports)
and save them to the artifact directory for visual regression matrix inspection.
"""

import io
import json
import os
import sys
import time
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from playwright.sync_api import sync_playwright
from app.main import app
from app.db import init_db

ARTIFACT_DIR = Path(r"C:\Users\idsid\.gemini\antigravity-ide\brain\1ca08345-52d5-43d8-bb10-30bc2b993a31")
PREVIEW_DIR = ARTIFACT_DIR / "preview_matrix"
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

MOCK_QUESTION = {
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

MOCK_ANSWER_RESPONSE = {
    "is_correct": 1,
    "correct_answer": "T",
    "explanation": "Na skrzyżowaniu równorzędnym obowiązuje **reguła prawej ręki** (art. 25 ust. 1 ustawy Prawo o ruchu drogowym). Należy ustąpić pierwszeństwa pojazdowi zbliżającemu się z prawej strony.",
    "legal_basis": "Art. 25 ust. 1 ustawy z dnia 20 czerwca 1997 r. Prawo o ruchu drogowym",
    "source": "llm",
    "time_ms": 3500
}

MOCK_DASHBOARD = {
    "user": {
        "id": 1,
        "login": "tester_ritual",
        "skill_theta": 1.45,
        "readiness_pct": 86.5,
        "rank": {"title": "Zaawansowany", "icon": "⚡", "color": "#3b82f6", "tier": 3},
        "streak_days": 5
    },
    "metrics": {
        "total_answers": 240,
        "correct_answers": 215,
        "accuracy_pct": 89.6,
        "mastered_questions": 180,
        "seen_questions": 230,
        "unseen_questions": 1905,
        "readiness_score": 86.5
    },
    "skill_history": [
        {"created_at": "2026-08-10T12:00:00", "theta": 0.2},
        {"created_at": "2026-08-11T12:00:00", "theta": 0.6},
        {"created_at": "2026-08-12T12:00:00", "theta": 0.9},
        {"created_at": "2026-08-13T12:00:00", "theta": 1.2},
        {"created_at": "2026-08-14T12:00:00", "theta": 1.45}
    ],
    "per_axis_b": [
        {"axis_b": "znaki_i_sygnaly", "accuracy": 94.0, "total": 60},
        {"axis_b": "pierwszenstwo", "accuracy": 88.0, "total": 50},
        {"axis_b": "manewry_i_pozycja", "accuracy": 85.0, "total": 45},
        {"axis_b": "predkosc_i_odleglosci", "accuracy": 91.0, "total": 35},
        {"axis_b": "technika_pojazdu", "accuracy": 82.0, "total": 30},
        {"axis_b": "pierwsza_pomoc", "accuracy": 96.0, "total": 20}
    ],
    "hardest_questions": [
        {"id": 1003, "q_pl": "Czy w tej sytuacji masz pierwszeństwo?", "error_count": 3, "points": 3},
        {"id": 1045, "q_pl": "Jaka jest dopuszczalna prędkość zespołu pojazdów?", "error_count": 2, "points": 2}
    ]
}

MOCK_REVIEW_QUEUE = {
    "items": [
        {
            "question_id": 1045,
            "q_pl": "Jaka jest dopuszczalna prędkość zespołu pojazdów na drodze ekspresowej dwujezdniowej?",
            "axis_a": "pamiec",
            "axis_b": "predkosc_i_odleglosci",
            "axis_c": ["czysta_pamieciowka"],
            "confidence": 0.62,
            "has_media": False
        },
        {
            "question_id": 1120,
            "q_pl": "Czy widoczny znak ostrzega o zbliżaniu się do skrzyżowania z ruchem okrężnym?",
            "axis_a": "rozumienie",
            "axis_b": "znaki_i_sygnaly",
            "axis_c": [],
            "confidence": 0.70,
            "has_media": True
        }
    ],
    "total": 2
}

class TestServer:
    def __init__(self, app, host="127.0.0.1", port=8135):
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

THEMES = ["dark", "light"]
VIEWPORTS = {
    "desktop": {"width": 1280, "height": 800},
    "mobile": {"width": 390, "height": 844}
}

def capture_all():
    init_db()
    srv = TestServer(app, host="127.0.0.1", port=8135)
    srv.start()
    server_url = f"http://{srv.host}:{srv.port}"
    print(f"Test server started at {server_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for theme in THEMES:
            for vp_name, vp_size in VIEWPORTS.items():
                print(f"Capturing for {theme} - {vp_name}...")
                context = browser.new_context(viewport=vp_size)
                page = context.new_page()

                # Set up deterministic mocks for stability
                page.route("**/api/session/next*", lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps([MOCK_QUESTION])
                ))
                page.route("**/api/questions*", lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps([MOCK_QUESTION])
                ))
                page.route("**/api/dashboard/summary*", lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(MOCK_DASHBOARD)
                ))
                page.route("**/api/classification/review*", lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(MOCK_REVIEW_QUEUE)
                ))
                page.route("**/api/answers*", lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(MOCK_ANSWER_RESPONSE)
                ))
                page.route("**/api/exam/start*", lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "questions": [MOCK_QUESTION],
                        "total_questions": 32,
                        "max_score": 74,
                        "pass_threshold": 68
                    })
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

                # 1. Surface: auth_login (unauthenticated)
                page.goto(f"{server_url}/", wait_until="networkidle")
                page.evaluate("localStorage.removeItem('prawko_user')")
                apply_theme()
                page.wait_for_timeout(300)
                page.screenshot(path=str(PREVIEW_DIR / f"auth_login_{theme}_{vp_name}.png"))

                # Authenticate mock user
                page.evaluate("""() => {
                    localStorage.setItem('prawko_user', JSON.stringify({ id: 1, login: 'tester_ritual' }));
                }""")
                page.reload(wait_until="networkidle")
                apply_theme()
                page.wait_for_timeout(300)

                # 2. Surface: dashboard_readiness
                page.screenshot(path=str(PREVIEW_DIR / f"dashboard_readiness_{theme}_{vp_name}.png"))

                # 3. Surface: nauka_learning
                page.goto(f"{server_url}/nauka", wait_until="networkidle")
                apply_theme()
                page.wait_for_timeout(400)
                page.screenshot(path=str(PREVIEW_DIR / f"nauka_learning_{theme}_{vp_name}.png"))

                # 4. Surface: explanation_card
                t_btn = page.locator("button:has-text('TAK'), button:has-text('T')").first
                if t_btn.is_visible():
                    t_btn.click()
                    page.wait_for_timeout(500)
                page.screenshot(path=str(PREVIEW_DIR / f"explanation_card_{theme}_{vp_name}.png"))

                # 5. Surface: review_queue
                page.goto(f"{server_url}/review", wait_until="networkidle")
                apply_theme()
                page.wait_for_timeout(400)
                page.screenshot(path=str(PREVIEW_DIR / f"review_queue_{theme}_{vp_name}.png"))

                # 6. Surface: exam_modal
                page.goto(f"{server_url}/", wait_until="networkidle")
                apply_theme()
                page.wait_for_timeout(300)
                exam_btn = page.locator("button:has-text('Sprawdzian'):visible, button:has-text('Egzamin'):visible").first
                if exam_btn.is_visible():
                    exam_btn.click()
                    page.wait_for_timeout(500)
                page.screenshot(path=str(PREVIEW_DIR / f"exam_modal_{theme}_{vp_name}.png"))


                context.close()

        browser.close()
    srv.stop()
    print("All 24 preview screenshots captured successfully.")

if __name__ == "__main__":
    capture_all()
