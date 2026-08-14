import sqlite3

conn = sqlite3.connect("data/prawko.sqlite")
c = conn.cursor()

# Remove duplicate LLM rows where vision classification exists
c.execute("""
    DELETE FROM question_classification
    WHERE source = 'llm'
      AND question_id IN (
          SELECT DISTINCT question_id
          FROM question_classification
          WHERE source = 'vision'
      )
""")
print(f"Deleted duplicate llm rows: {c.rowcount}")

# Check any remaining duplicates on Axis A or Axis B
c.execute("""
    SELECT question_id, axis, COUNT(*)
    FROM question_classification
    WHERE axis IN ('A', 'B')
    GROUP BY question_id, axis
    HAVING COUNT(*) > 1
""")
remaining_dups = c.fetchall()
print(f"Remaining duplicate single-value axis rows: {len(remaining_dups)}")

conn.commit()
conn.close()
