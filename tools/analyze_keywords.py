import sqlite3
import json

conn = sqlite3.connect("data/prawko.sqlite")
c = conn.cursor()

c.execute("SELECT id, q_pl, correct, type FROM questions WHERE categories LIKE '%\"B\"%'")
questions = c.fetchall()

print(f"Loaded {len(questions)} Category B questions.")

# Check for specific words
for q_id, q_pl, correct, q_type in questions:
    q_low = q_pl.lower()
    # Check if accident question
    if "wypadk" in q_low or "rann" in q_low or "poszkodowan" in q_low:
        pass
    # Check if roundabout
    if "rond" in q_low or "ruchu okrężnym" in q_low or "c-12" in q_low:
        pass

conn.close()
