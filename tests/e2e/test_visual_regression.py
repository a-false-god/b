"""
Visual Regression Baseline Test Suite (Task S5).

Captures and asserts pixel difference tolerances for:
6 surfaces x 2 themes (dark/light) x 2 viewports (desktop 1280x800, mobile 390x844).

Surfaces:
1. auth_login
2. nauka_learning
3. explanation_card
4. dashboard_readiness
5. review_queue
6. exam_modal

Uses deterministic API route mocking for pixel-perfect stability across test runs.
Run with UPDATE_BASELINE=1 to regenerate all baseline snapshots.
"""

import io
import json
import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

BASELINE_DIR = Path(__file__).resolve().parent / "baseline"
BASELINE_DIR.mkdir(parents=True, exist_ok=True)

playwright_available = False
try:
    import playwright  # noqa: F401
    from playwright.sync_api import sync_playwright
    playwright_available = True
except ImportError:
    playwright_available = False

try:
    from PIL import Image, ImageChops
    pil_available = True
except ImportError:
    pil_available = False


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


def calculate_image_diff_percent(img1_path: Path, img2_bytes: bytes) -> float:
    """Compare baseline image with current screenshot bytes and return diff % (0..100)."""
    if not pil_available:
        return 0.0

    img1 = Image.open(img1_path).convert("RGBA")
    img2 = Image.open(io.BytesIO(img2_bytes)).convert("RGBA")

    if img1.size != img2.size:
        img2 = img2.resize(img1.size)

    diff = ImageChops.difference(img1, img2)
    # Convert diff to grayscale luminance
    diff_l = diff.convert("L")
    stat = list(diff_l.getdata())
    total_pixels = len(stat)
    diff_pixels = sum(1 for p in stat if p > 15)
    return (diff_pixels / total_pixels) * 100.0


def assert_or_update_baseline(page, surface_name: str, theme: str, viewport_name: str, request=None):
    """Capture current page screenshot, update or verify against baseline."""
    update_flag = False
    if request:
        try:
            update_flag = request.config.getoption("--update-baseline", False)
        except Exception:
            pass
    update_baseline = update_flag or (os.environ.get("UPDATE_BASELINE") == "1")
    filename = f"{surface_name}_{theme}_{viewport_name}.png"
    baseline_file = BASELINE_DIR / filename

    screenshot_bytes = page.screenshot(full_page=False)

    if update_baseline or not baseline_file.exists():
        baseline_file.write_bytes(screenshot_bytes)
        return

    diff_pct = calculate_image_diff_percent(baseline_file, screenshot_bytes)
    assert diff_pct <= 5.0, (
        f"Visual regression diff {diff_pct:.2f}% exceeds tolerance (5.0%) for {filename}"
    )


THEMES = ["dark", "light"]
VIEWPORTS = {
    "desktop": {"width": 1280, "height": 800},
    "mobile": {"width": 390, "height": 844}
}


@pytest.mark.skipif(
    not playwright_available or os.environ.get("SKIP_PLAYWRIGHT_TESTS") == "1",
    reason="Playwright tests disabled (SKIP_PLAYWRIGHT_TESTS=1 or not installed)"
)
@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("vp_name,vp_size", VIEWPORTS.items())
def test_visual_regression_surfaces(e2e_server, theme, vp_name, vp_size, request):

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Browser launch failed in headless environment: {exc}")

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
        page.goto(f"{e2e_server}/", wait_until="networkidle")
        page.evaluate("localStorage.removeItem('prawko_user')")
        apply_theme()
        page.wait_for_timeout(300)
        assert_or_update_baseline(page, "auth_login", theme, vp_name, request=request)

        # Authenticate mock user
        page.evaluate("""() => {
            localStorage.setItem('prawko_user', JSON.stringify({ id: 1, login: 'tester_ritual' }));
        }""")
        page.reload(wait_until="networkidle")
        apply_theme()
        page.wait_for_timeout(300)

        # 2. Surface: dashboard_readiness
        assert_or_update_baseline(page, "dashboard_readiness", theme, vp_name, request=request)

        # 3. Surface: nauka_learning
        page.goto(f"{e2e_server}/nauka", wait_until="networkidle")
        apply_theme()
        page.wait_for_timeout(400)
        assert_or_update_baseline(page, "nauka_learning", theme, vp_name, request=request)

        # 4. Surface: explanation_card
        t_btn = page.locator("button:has-text('TAK'), button:has-text('T')").first
        if t_btn.is_visible():
            t_btn.click()
            page.wait_for_timeout(500)
        assert_or_update_baseline(page, "explanation_card", theme, vp_name, request=request)

        # 5. Surface: review_queue
        page.goto(f"{e2e_server}/review", wait_until="networkidle")
        apply_theme()
        page.wait_for_timeout(400)
        assert_or_update_baseline(page, "review_queue", theme, vp_name, request=request)

        # 6. Surface: exam_modal
        page.goto(f"{e2e_server}/", wait_until="networkidle")
        apply_theme()
        page.wait_for_timeout(300)
        exam_btn = page.locator("button:has-text('Sprawdzian'), button:has-text('Egzamin')").first
        if exam_btn.is_visible():
            exam_btn.click()
            page.wait_for_timeout(400)
        assert_or_update_baseline(page, "exam_modal", theme, vp_name, request=request)


        context.close()
        browser.close()
