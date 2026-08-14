import sqlite3

conn = sqlite3.connect("data/prawko.sqlite")
c = conn.cursor()

# Search questions containing ecodriving / ekologia keywords
c.execute("""
    SELECT q.id, q.q_pl, qe.legal_basis, qe.explanation, qc_b.value as axis_b
    FROM questions q
    JOIN question_explanations qe ON q.id = qe.question_id
    LEFT JOIN (
        SELECT question_id, value FROM question_classification WHERE axis = 'B' GROUP BY question_id
    ) qc_b ON q.id = qc_b.question_id
    WHERE q.categories LIKE '%"B"%'
      AND (
          q.q_pl LIKE '%ekolog%' OR q.q_pl LIKE '%paliw%' OR q.q_pl LIKE '%obrot%'
          OR q.q_pl LIKE '%emisj%' OR q.q_pl LIKE '%bieg%' OR qc_b.value = 'ekologia'
      )
""")
rows = c.fetchall()
print(f"Found {len(rows)} potential ecodriving / ekologia questions:")
for r in rows[:10]:
    print("--------------------------------------------------")
    print(f"ID: {r[0]} | Axis B: {r[4]}")
    print(f"Q: {r[1]}")
    print(f"Legal: {r[2]}")
    print(f"Exp: {r[3][:100]}...")

conn.close()
