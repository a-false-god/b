import sqlite3

conn = sqlite3.connect("data/prawko.sqlite")
c = conn.cursor()

c.execute("""
    SELECT q.id, COUNT(*) as cnt
    FROM questions q
    LEFT JOIN question_classification qc_b ON q.id = qc_b.question_id AND qc_b.axis = 'B'
    WHERE q.categories LIKE '%"B"%'
    GROUP BY q.id
    HAVING COUNT(*) > 1
""")
dups_join = c.fetchall()
print(f"Questions with duplicate Axis B classifications: {len(dups_join)}")
for q_id, cnt in dups_join:
    c.execute("SELECT * FROM question_classification WHERE question_id = ? AND axis = 'B'", (q_id,))
    rows = c.fetchall()
    print(f"Question ID {q_id} has {cnt} rows in question_classification:", rows)

conn.close()
