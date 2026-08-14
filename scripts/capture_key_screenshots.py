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

ARTIFACTS_DIR = Path(r"C:\Users\idsid\.gemini\antigravity-ide\brain\de7f737a-353a-4ef0-8e43-a69e73a890db")
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"
SRC_SCREENSHOTS_DIR = ROOT_DIR / "src" / "screenshots"
FRONTEND_SRC_SCREENSHOTS_DIR = ROOT_DIR / "frontend" / "src" / "screenshots"
SRC_DIR = ROOT_DIR / "src"

for d in [SCREENSHOTS_DIR, SRC_SCREENSHOTS_DIR, FRONTEND_SRC_SCREENSHOTS_DIR, SRC_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def save_shot(page, filename: str):
    targets = [
        ARTIFACTS_DIR / filename,
        SCREENSHOTS_DIR / filename,
        SRC_SCREENSHOTS_DIR / filename,
        FRONTEND_SRC_SCREENSHOTS_DIR / filename,
        SRC_DIR / filename,
    ]
    for t in targets:
        t.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(targets[0]), full_page=False)
    for t in targets[1:]:
        import shutil
        shutil.copy2(targets[0], t)
    print(f"Saved {filename} across artifact and src/ dirs", flush=True)

def ensure_tester_user():
    db_path = Path("data/prawko.sqlite")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE login = 'tester_shadcn'")
    row = cur.fetchone()
    hashed = hash_password("secret123")
    if not row:
        cur.execute("INSERT INTO users (login, password_hash) VALUES ('tester_shadcn', ?)", (hashed,))
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
    cur.execute("SELECT id FROM users WHERE login = 'tester_shadcn'")
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

            # 1. Nauka Dark Mobile WITH Explanation Card
            print("1. Capturing nauka_dark_mobile_explanation.png ...", flush=True)
            context_mobile_dark = browser.new_context(
                viewport={"width": 390, "height": 920},
                is_mobile=True,
                device_scale_factor=2,
            )
            page = context_mobile_dark.new_page()
            page.request.post("http://127.0.0.1:8000/auth/login", data={"login": "tester_shadcn", "password": "secret123"})
            page.goto("http://127.0.0.1:8000/nauka")
            page.evaluate(f"""() => {{
                localStorage.setItem('prawko_user', JSON.stringify({{ id: {user_id}, login: 'tester_shadcn' }}));
                localStorage.setItem('prawko_theme', 'dark');
                document.documentElement.classList.add('dark');
                document.documentElement.classList.remove('light');
            }}""")
            page.reload()
            page.wait_for_timeout(600)

            # Click answer button 'TAK' (or first button) to trigger answer + explanation
            buttons = page.locator("button:has-text('TAK'), button:has-text('NIE')")
            if buttons.count() > 0:
                buttons.first.click()
            else:
                page.locator("button.group").first.click()
            
            # Wait for explanation card animation
            page.wait_for_timeout(800)
            save_shot(page, "nauka_dark_mobile_explanation.png")
            context_mobile_dark.close()

            # 2. Nauka Light Mobile
            print("2. Capturing nauka_light_mobile.png ...", flush=True)
            context_mobile_light = browser.new_context(
                viewport={"width": 390, "height": 844},
                is_mobile=True,
                device_scale_factor=2,
            )
            page2 = context_mobile_light.new_page()
            page2.request.post("http://127.0.0.1:8000/auth/login", data={"login": "tester_shadcn", "password": "secret123"})
            page2.goto("http://127.0.0.1:8000/nauka")
            page2.evaluate(f"""() => {{
                localStorage.setItem('prawko_user', JSON.stringify({{ id: {user_id}, login: 'tester_shadcn' }}));
                localStorage.setItem('prawko_theme', 'light');
                document.documentElement.classList.remove('dark');
                document.documentElement.classList.add('light');
            }}""")
            page2.reload()
            page2.wait_for_timeout(600)

            save_shot(page2, "nauka_light_mobile.png")
            context_mobile_light.close()

            # 3. Pulpit Dark Desktop
            print("3. Capturing pulpit_dark_desktop.png ...", flush=True)
            context_desktop_dark = browser.new_context(
                viewport={"width": 1280, "height": 880},
                is_mobile=False,
                device_scale_factor=2,
            )
            page3 = context_desktop_dark.new_page()
            page3.request.post("http://127.0.0.1:8000/auth/login", data={"login": "tester_shadcn", "password": "secret123"})
            page3.goto("http://127.0.0.1:8000/")
            page3.evaluate(f"""() => {{
                localStorage.setItem('prawko_user', JSON.stringify({{ id: {user_id}, login: 'tester_shadcn' }}));
                localStorage.setItem('prawko_theme', 'dark');
                document.documentElement.classList.add('dark');
                document.documentElement.classList.remove('light');
            }}""")
            page3.reload()
            page3.wait_for_timeout(600)

            save_shot(page3, "pulpit_dark_desktop.png")
            context_desktop_dark.close()

            browser.close()

    finally:
        server_process.terminate()
        server_process.wait()
        cleanup_tester_user()
        print("Wiped tester_shadcn from DB", flush=True)

if __name__ == "__main__":
    main()
