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

CURRENT_CONV_DIR = Path(r"C:\Users\idsid\.gemini\antigravity-ide\brain\9b3e2a47-799f-41ec-b4d1-f519a558f985")
SCREENSHOTS_DIR = CURRENT_CONV_DIR / "screenshots"
SRC_SCREENSHOTS_DIR = ROOT_DIR / "src" / "screenshots"
FRONTEND_SRC_SCREENSHOTS_DIR = ROOT_DIR / "frontend" / "src" / "screenshots"
SRC_DIR = ROOT_DIR / "src"

for d in [CURRENT_CONV_DIR, SCREENSHOTS_DIR, SRC_SCREENSHOTS_DIR, FRONTEND_SRC_SCREENSHOTS_DIR, SRC_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def save_shot(page, filename: str):
    targets = [
        CURRENT_CONV_DIR / filename,
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

            # 1. Dashboard Dark Mobile (390 x 844)
            print("1. Capturing dashboard_v2_dark.png ...", flush=True)
            ctx_dash_dark = browser.new_context(
                viewport={"width": 390, "height": 844},
                is_mobile=True,
                device_scale_factor=2,
            )
            page1 = ctx_dash_dark.new_page()
            page1.request.post("http://127.0.0.1:8000/auth/login", data={"login": "Mike", "password": "secret123"})
            page1.goto("http://127.0.0.1:8000/")
            page1.evaluate(f"""() => {{
                localStorage.setItem('prawko_user', JSON.stringify({{ id: {user_id}, login: 'Mike' }}));
                localStorage.setItem('prawko_theme', 'dark');
                document.documentElement.classList.add('dark');
                document.documentElement.classList.remove('light');
            }}""")
            page1.reload()
            page1.wait_for_timeout(700)
            save_shot(page1, "dashboard_v2_dark.png")
            ctx_dash_dark.close()

            # 2. Dashboard Light Mobile (390 x 844)
            print("2. Capturing dashboard_v2_light.png ...", flush=True)
            ctx_dash_light = browser.new_context(
                viewport={"width": 390, "height": 844},
                is_mobile=True,
                device_scale_factor=2,
            )
            page2 = ctx_dash_light.new_page()
            page2.request.post("http://127.0.0.1:8000/auth/login", data={"login": "Mike", "password": "secret123"})
            page2.goto("http://127.0.0.1:8000/")
            page2.evaluate(f"""() => {{
                localStorage.setItem('prawko_user', JSON.stringify({{ id: {user_id}, login: 'Mike' }}));
                localStorage.setItem('prawko_theme', 'light');
                document.documentElement.classList.remove('dark');
                document.documentElement.classList.add('light');
            }}""")
            page2.reload()
            page2.wait_for_timeout(700)
            save_shot(page2, "dashboard_v2_light.png")
            ctx_dash_light.close()

            # 3. Nauka Dark Mobile WITH Explanation Card (Bold markdown check)
            print("3. Capturing nauka_dark_mobile_explanation.png ...", flush=True)
            ctx_nauka_dark = browser.new_context(
                viewport={"width": 390, "height": 920},
                is_mobile=True,
                device_scale_factor=2,
            )
            page3 = ctx_nauka_dark.new_page()
            page3.request.post("http://127.0.0.1:8000/auth/login", data={"login": "Mike", "password": "secret123"})
            page3.goto("http://127.0.0.1:8000/nauka")
            page3.evaluate(f"""() => {{
                localStorage.setItem('prawko_user', JSON.stringify({{ id: {user_id}, login: 'Mike' }}));
                localStorage.setItem('prawko_theme', 'dark');
                document.documentElement.classList.add('dark');
                document.documentElement.classList.remove('light');
            }}""")
            page3.reload()
            page3.wait_for_timeout(600)

            # Click answer button 'TAK' (or first button) to trigger answer + explanation
            buttons = page3.locator("button:has-text('TAK'), button:has-text('NIE')")
            if buttons.count() > 0:
                buttons.first.click()
            else:
                page3.locator("button.group").first.click()
            
            # Wait for explanation card animation
            page3.wait_for_timeout(800)
            save_shot(page3, "nauka_dark_mobile_explanation.png")
            ctx_nauka_dark.close()

            browser.close()

    finally:
        server_process.terminate()
        server_process.wait()
        cleanup_tester_user()
        print("Done capturing v2 screenshots", flush=True)

if __name__ == "__main__":
    main()
