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
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Ensure tester_shadcn exists and has valid password
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

def main():
    user_id = ensure_tester_user()
    print(f"Tester user ID: {user_id}")

    # Start uvicorn server
    env = os.environ.copy()
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    time.sleep(2.5)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            # Viewport configurations
            configs = [
                {"name": "desktop", "viewport": {"width": 1280, "height": 860}, "is_mobile": False},
                {"name": "mobile", "viewport": {"width": 390, "height": 844}, "is_mobile": True},
            ]

            themes = ["dark", "light"]

            for cfg in configs:
                for theme in themes:
                    context = browser.new_context(
                        viewport=cfg["viewport"],
                        is_mobile=cfg["is_mobile"],
                        device_scale_factor=2,
                    )
                    page = context.new_page()

                    # Set localStorage user and theme
                    page.goto("http://127.0.0.1:8000/")
                    page.evaluate(f"""() => {{
                        localStorage.setItem('prawko_user', JSON.stringify({{ id: {user_id}, login: 'tester_shadcn' }}));
                    }}""")

                    # 1. Dashboard (Pulpit)
                    page.goto("http://127.0.0.1:8000/")
                    page.wait_for_selector("text=Witaj, tester_shadcn")
                    if theme == "dark":
                        page.evaluate("() => { document.documentElement.classList.add('dark'); document.documentElement.classList.remove('light'); }")
                    else:
                        page.evaluate("() => { document.documentElement.classList.remove('dark'); document.documentElement.classList.add('light'); }")
                    time.sleep(0.4)
                    
                    shot_path = SCREENSHOTS_DIR / f"dashboard_{theme}_{cfg['name']}.png"
                    page.screenshot(path=str(shot_path), full_page=False)
                    print(f"Saved {shot_path.name}")

                    # 2. Nauka Screen
                    page.goto("http://127.0.0.1:8000/nauka")
                    page.wait_for_selector("text=SESJA")
                    if theme == "dark":
                        page.evaluate("() => { document.documentElement.classList.add('dark'); document.documentElement.classList.remove('light'); }")
                    else:
                        page.evaluate("() => { document.documentElement.classList.remove('dark'); document.documentElement.classList.add('light'); }")
                    time.sleep(0.4)
                    shot_path = SCREENSHOTS_DIR / f"nauka_{theme}_{cfg['name']}.png"
                    page.screenshot(path=str(shot_path), full_page=False)
                    print(f"Saved {shot_path.name}")

                    # 3. Analiza Screen
                    page.goto("http://127.0.0.1:8000/analiza")
                    page.wait_for_selector("text=Panel Analizy Błędów")
                    if theme == "dark":
                        page.evaluate("() => { document.documentElement.classList.add('dark'); document.documentElement.classList.remove('light'); }")
                    else:
                        page.evaluate("() => { document.documentElement.classList.remove('dark'); document.documentElement.classList.add('light'); }")
                    time.sleep(0.4)
                    shot_path = SCREENSHOTS_DIR / f"analiza_{theme}_{cfg['name']}.png"
                    page.screenshot(path=str(shot_path), full_page=False)
                    print(f"Saved {shot_path.name}")

                    # 4. Weryfikacja (Review Queue)
                    page.goto("http://127.0.0.1:8000/review")
                    page.wait_for_selector("text=Kolejka Weryfikacji Taksonomii")
                    if theme == "dark":
                        page.evaluate("() => { document.documentElement.classList.add('dark'); document.documentElement.classList.remove('light'); }")
                    else:
                        page.evaluate("() => { document.documentElement.classList.remove('dark'); document.documentElement.classList.add('light'); }")
                    time.sleep(0.4)
                    shot_path = SCREENSHOTS_DIR / f"weryfikacja_{theme}_{cfg['name']}.png"
                    page.screenshot(path=str(shot_path), full_page=False)
                    print(f"Saved {shot_path.name}")

                    # 5. Exam Modal
                    page.goto("http://127.0.0.1:8000/")
                    page.wait_for_selector("text=Witaj, tester_shadcn")
                    if theme == "dark":
                        page.evaluate("() => { document.documentElement.classList.add('dark'); document.documentElement.classList.remove('light'); }")
                    else:
                        page.evaluate("() => { document.documentElement.classList.remove('dark'); document.documentElement.classList.add('light'); }")
                    # Click exam button
                    page.click("button:has-text('Uruchom Sprawdzian')")
                    page.wait_for_selector("text=Sprawdzian Gotowości")
                    time.sleep(0.4)
                    shot_path = SCREENSHOTS_DIR / f"exam_{theme}_{cfg['name']}.png"
                    page.screenshot(path=str(shot_path), full_page=False)
                    print(f"Saved {shot_path.name}")

                    # 6. Auth Modal (without logged in user)
                    page.goto("http://127.0.0.1:8000/")
                    page.evaluate("() => { localStorage.removeItem('prawko_user'); }")
                    page.reload()
                    page.wait_for_selector("button:has-text('Zaloguj')")
                    if theme == "dark":
                        page.evaluate("() => { document.documentElement.classList.add('dark'); document.documentElement.classList.remove('light'); }")
                    else:
                        page.evaluate("() => { document.documentElement.classList.remove('dark'); document.documentElement.classList.add('light'); }")
                    page.click("button:has-text('Zaloguj')")
                    page.wait_for_selector("text=Logowanie")
                    time.sleep(0.4)
                    shot_path = SCREENSHOTS_DIR / f"auth_{theme}_{cfg['name']}.png"
                    page.screenshot(path=str(shot_path), full_page=False)
                    print(f"Saved {shot_path.name}")

                    context.close()

            browser.close()

    finally:
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    main()
