import sqlite3

conn = sqlite3.connect("data/prawko.sqlite")
c = conn.cursor()

c.execute("""
    SELECT q.id, q.q_pl, q.media, vr.decision, vr.suggested_axis_b
    FROM questions q
    LEFT JOIN question_classification qc ON q.id = qc.question_id AND qc.axis = 'B'
    LEFT JOIN vision_review vr ON q.id = vr.question_id
    WHERE q.categories LIKE '%"B"%' AND qc.value IS NULL
""")
rows = c.fetchall()
print(f"Unclassified questions: {len(rows)}")
for r in rows:
    print(r)

conn.close()
