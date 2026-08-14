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

def seed_calibrated_user():
    db_path = Path("data/prawko.sqlite")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE login = 'tester_shadcn'")
    row = cur.fetchone()
    hashed = hash_password("secret123")
    if not row:
        cur.execute("INSERT INTO users (login, password_hash) VALUES ('tester_shadcn', ?)", (hashed,))
        user_id = cur.lastrowid
    else:
        user_id = row[0]
        cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, user_id))
    
    # Insert 15 answers with theta = 1.45
    cur.execute("DELETE FROM answer_events WHERE user_id = ?", (user_id,))
    cur.execute("DELETE FROM user_skill WHERE user_id = ?", (user_id,))
    
    cur.execute("INSERT INTO user_skill (user_id, axis_value, theta, n, updated_at) VALUES (?, NULL, 1.45, 18, datetime('now'))", (user_id,))
    for i in range(1, 19):
        is_cor = 1 if i != 4 and i != 11 else 0
        cur.execute("INSERT INTO answer_events (user_id, question_id, chosen, is_correct, time_ms, session_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, i, 'T', is_cor, 5200 if is_cor else 11000, 'sess_test'))
        cur.execute("INSERT INTO skill_history (user_id, theta, created_at) VALUES (?, ?, datetime('now'))", (user_id, 0.1 * i))
    conn.commit()
    conn.close()
    return user_id

def cleanup():
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
    user_id = seed_calibrated_user()
    
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
            context = browser.new_context(viewport={"width": 1280, "height": 880}, device_scale_factor=2)
            page = context.new_page()
            page.request.post("http://127.0.0.1:8000/auth/login", data={"login": "tester_shadcn", "password": "secret123"})
            page.goto("http://127.0.0.1:8000/")
            page.evaluate(f"""() => {{
                localStorage.setItem('prawko_user', JSON.stringify({{ id: {user_id}, login: 'tester_shadcn' }}));
                localStorage.setItem('prawko_theme', 'dark');
                document.documentElement.classList.add('dark');
                document.documentElement.classList.remove('light');
            }}""")
            page.reload()
            page.wait_for_timeout(600)

            shot = ARTIFACTS_DIR / "pulpit_dark_desktop_calibrated.png"
            page.screenshot(path=str(shot), full_page=False)
            print(f"Saved {shot.name}", flush=True)
            browser.close()
    finally:
        server_process.terminate()
        server_process.wait()
        cleanup()
        print("Wiped tester_shadcn from DB", flush=True)

if __name__ == "__main__":
    main()
