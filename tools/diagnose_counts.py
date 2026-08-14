import sqlite3
import json

conn = sqlite3.connect("data/prawko.sqlite")
c = conn.cursor()

# 1. Check total questions with category B
c.execute("SELECT id, categories, status FROM questions WHERE categories LIKE '%\"B\"%'")
cat_b_all = c.fetchall()
print(f"Total Category B questions in 'questions' table: {len(cat_b_all)}")

c.execute("SELECT id, categories, status FROM questions WHERE categories LIKE '%\"B\"%' AND status = 'active'")
cat_b_active = c.fetchall()
print(f"Active Category B questions: {len(cat_b_active)}")

c.execute("SELECT id, categories, status FROM questions WHERE categories LIKE '%\"B\"%' AND status != 'active'")
cat_b_pending = c.fetchall()
print(f"Non-active Category B questions (status={cat_b_pending[0][2] if cat_b_pending else None}): {len(cat_b_pending)}")

# 2. Check question_explanations rows
c.execute("SELECT question_id, explanation, legal_basis, source FROM question_explanations")
exp_rows = c.fetchall()
print(f"Total rows in 'question_explanations': {len(exp_rows)}")

cat_b_ids = {r[0] for r in cat_b_all}
non_cat_b_in_exp = [r for r in exp_rows if r[0] not in cat_b_ids]
print(f"Explanations for question_ids NOT in Category B catalog: {len(non_cat_b_in_exp)}")
for r in non_cat_b_in_exp:
    print(f" - Question ID: {r[0]}, Source: {r[3]}, Legal: {r[2]}")
    c.execute("SELECT id, categories, status, q_pl FROM questions WHERE id = ?", (r[0],))
    q_info = c.fetchone()
    print(f"   In questions table: {q_info}")

# 3. Check duplicate IDs in question_explanations
c.execute("SELECT question_id, COUNT(*) FROM question_explanations GROUP BY question_id HAVING COUNT(*) > 1")
dups = c.fetchall()
print(f"Duplicate question_ids in question_explanations: {dups}")

conn.close()
