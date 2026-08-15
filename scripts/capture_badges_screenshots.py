import os
import sys
import time
import subprocess
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from playwright.sync_api import sync_playwright
from app.auth import hash_password

CURRENT_CONV_DIR = Path(r"C:\Users\idsid\.gemini\antigravity-ide\brain\bdd021be-6f09-4d16-9272-523cec572b4e")
SCREENSHOTS_DIR = CURRENT_CONV_DIR / "screenshots"
SRC_SCREENSHOTS_DIR = ROOT_DIR / "src" / "screenshots"
FRONTEND_SRC_SCREENSHOTS_DIR = ROOT_DIR / "frontend" / "src" / "screenshots"

for d in [CURRENT_CONV_DIR, SCREENSHOTS_DIR, SRC_SCREENSHOTS_DIR, FRONTEND_SRC_SCREENSHOTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def save_shot(page, filename: str):
    targets = [
        CURRENT_CONV_DIR / filename,
        SCREENSHOTS_DIR / filename,
        SRC_SCREENSHOTS_DIR / filename,
        FRONTEND_SRC_SCREENSHOTS_DIR / filename,
    ]
    for t in targets:
        t.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(targets[0]), full_page=False)
    for t in targets[1:]:
        import shutil
        shutil.copy2(targets[0], t)
    print(f"Saved {filename} across artifact dirs", flush=True)

def ensure_tester_user():
    db_path = Path("data/prawko.sqlite")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE login = 'Mike'")
    row = cur.fetchone()
    hashed = hash_password("secret123")
    if not row:
        cur.execute("INSERT INTO users (login, password_hash) VALUES ('Mike', ?)", (hashed,))
        conn.commit()
        user_id = cur.lastrowid
    else:
        user_id = row[0]
        cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, user_id))
        conn.commit()
    conn.close()
    return user_id

def cleanup_tester_user():
    db_path = Path("data/prawko.sqlite")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE login = 'Mike'")
    row = cur.fetchone()
    if row:
        user_id = row[0]
        cur.execute("DELETE FROM answer_events WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM user_skill WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    conn.close()

def main():
    user_id = ensure_tester_user()
    print(f"Tester user ID: {user_id}", flush=True)

    env = os.environ.copy()
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    time.sleep(2.0)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # 1. Nauka view with left badges (Dark Mobile & Desktop)
            print("1. Capturing nauka_left_badges.png ...", flush=True)
            ctx_nauka = browser.new_context(
                viewport={"width": 420, "height": 860},
                device_scale_factor=2,
            )
            page1 = ctx_nauka.new_page()
            page1.request.post("http://127.0.0.1:8000/auth/login", data={"login": "Mike", "password": "secret123"})
            page1.goto("http://127.0.0.1:8000/nauka")
            page1.evaluate(f"""() => {{
                localStorage.setItem('prawko_user', JSON.stringify({{ id: {user_id}, login: 'Mike' }}));
                localStorage.setItem('prawko_theme', 'dark');
                document.documentElement.classList.add('dark');
                document.documentElement.classList.remove('light');
            }}""")
            page1.reload()
            page1.wait_for_timeout(800)
            save_shot(page1, "nauka_left_badges.png")
            ctx_nauka.close()

            # 2. Sprawdzian (Exam Modal) with left badges
            print("2. Capturing sprawdzian_left_badges.png ...", flush=True)
            ctx_exam = browser.new_context(
                viewport={"width": 540, "height": 880},
                device_scale_factor=2,
            )
            page2 = ctx_exam.new_page()
            page2.request.post("http://127.0.0.1:8000/auth/login", data={"login": "Mike", "password": "secret123"})
            page2.goto("http://127.0.0.1:8000/")
            page2.evaluate(f"""() => {{
                localStorage.setItem('prawko_user', JSON.stringify({{ id: {user_id}, login: 'Mike' }}));
                localStorage.setItem('prawko_theme', 'dark');
                document.documentElement.classList.add('dark');
                document.documentElement.classList.remove('light');
            }}""")
            page2.reload()
            page2.wait_for_timeout(600)

            # Click "Sprawdzian" / Exam trigger button in navbar or floating bar
            exam_btn = page2.locator("button:has-text('Sprawdzian'), button:has-text('Egzamin')").first
            if exam_btn.is_visible():
                exam_btn.click()
                page2.wait_for_timeout(1000)
                save_shot(page2, "sprawdzian_left_badges.png")

                # Advance to an ABC question (Specialist part starts at Q21)
                for i in range(20):
                    btn = page2.locator("div.grid button").first
                    if btn.is_visible():
                        btn.click()
                        page2.wait_for_timeout(150)
                page2.wait_for_timeout(500)
                save_shot(page2, "sprawdzian_abc_left_badges.png")
            else:
                print("Could not find Sprawdzian button", flush=True)

            ctx_exam.close()
            browser.close()

    finally:
        server_process.terminate()
        server_process.wait()
        cleanup_tester_user()
        print("Done capturing badges screenshots", flush=True)

if __name__ == "__main__":
    main()
