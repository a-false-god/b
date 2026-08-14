import sqlite3

conn = sqlite3.connect("data/prawko.sqlite")
c = conn.cursor()

print("=================================================================")
print("PRÓBKA 1: 5 WYJAŚNIEŃ Z DOMENY EKOLOGIA / ECODRIVING")
print("=================================================================")
c.execute("""
    SELECT q.id, q.q_pl, qe.legal_basis, qe.explanation
    FROM questions q
    JOIN question_explanations qe ON q.id = qe.question_id
    WHERE qe.legal_basis = 'unknown' OR q.q_pl LIKE '%ekonomiczna jazda%' OR q.q_pl LIKE '%emisj%'
    LIMIT 5
""")
eco_samples = c.fetchall()
for idx, (qid, qpl, legal, exp) in enumerate(eco_samples, 1):
    print(f"\n[{idx}] Pytanie #{qid}: {qpl}")
    print(f"    Podstawa prawna: {legal}")
    print(f"    Wyjaśnienie:     {exp}")

print("\n=================================================================")
print("PRÓBKA 2: 5 WYJAŚNIEŃ Z DOMENY PIERWSZEŃSTWO / RONDO (Ruch okrężny)")
print("=================================================================")
c.execute("""
    SELECT q.id, q.q_pl, qe.legal_basis, qe.explanation
    FROM questions q
    JOIN question_explanations qe ON q.id = qe.question_id
    WHERE q.q_pl LIKE '%rond%' OR q.q_pl LIKE '%ruchu okrężn%' OR q.q_pl LIKE '%c-12%'
       OR qe.legal_basis LIKE '%C-12%'
    LIMIT 5
""")
rondo_samples = c.fetchall()
for idx, (qid, qpl, legal, exp) in enumerate(rondo_samples, 1):
    print(f"\n[{idx}] Pytanie #{qid}: {qpl}")
    print(f"    Podstawa prawna: {legal}")
    print(f"    Wyjaśnienie:     {exp}")

conn.close()
