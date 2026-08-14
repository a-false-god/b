import sqlite3

conn = sqlite3.connect("data/prawko.sqlite")
c = conn.cursor()

c.execute("SELECT axis, COUNT(DISTINCT question_id), COUNT(*) FROM question_classification GROUP BY axis")
for axis, distinct_q, total_rows in c.fetchall():
    print(f"Axis {axis}: {distinct_q} distinct questions, {total_rows} total rows")

c.execute("SELECT value, COUNT(*) FROM question_classification WHERE axis = 'B' GROUP BY value ORDER BY COUNT(*) DESC")
print("\nBreakdown for Axis B (Content Domains):")
for val, cnt in c.fetchall():
    print(f" - {val:<25}: {cnt:>5} ({cnt/2135*100:.1f}%)")

conn.close()
