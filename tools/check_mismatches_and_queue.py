import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.generate_explanations import compute_question_content_hash

conn = sqlite3.connect("data/prawko.sqlite")
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("""
    SELECT q.id, q.q_pl, q.a_pl, q.b_pl, q.c_pl, q.correct, qe.content_hash, qe.needs_vision_review,
           qc.value as axis_b, vr.decision
    FROM questions q
    JOIN question_explanations qe ON q.id = qe.question_id
    LEFT JOIN (SELECT question_id, value FROM question_classification WHERE axis = 'B' GROUP BY question_id) qc ON q.id = qc.question_id
    LEFT JOIN vision_review vr ON q.id = vr.question_id
    WHERE q.categories LIKE '%"B"%'
""")
rows = c.fetchall()

mismatches = []
for r in rows:
    qd = dict(r)
    ht = compute_question_content_hash(qd, axis_signature=qd["axis_b"], mode="text")
    hv = compute_question_content_hash(qd, axis_signature=qd["axis_b"], mode="vision")
    if qd["content_hash"] not in (ht, hv):
        mismatches.append((qd["id"], qd["content_hash"], ht, hv, qd["axis_b"], qd["decision"]))

print(f"Total Mismatches: {len(mismatches)}")
for m in mismatches:
    print(f"Q#{m[0]}: stored={m[1]} | text_hash={m[2]} | vis_hash={m[3]} | axis_b={m[4]} | decision={m[5]}")

print("\n8 Queued Questions:")
c.execute("""
    SELECT vr.question_id, q.q_pl, q.media,
           qc_a.value as a_val, qc_a.source as a_src,
           qc_b.value as b_val, qc_b.source as b_src,
           vr.suggested_axis_a, vr.suggested_axis_b, vr.suggested_axis_c,
           vr.confidence, vr.rationale
    FROM vision_review vr
    JOIN questions q ON vr.question_id = q.id
    LEFT JOIN (SELECT question_id, value, source FROM question_classification WHERE axis = 'A' GROUP BY question_id) qc_a ON q.id = qc_a.question_id
    LEFT JOIN (SELECT question_id, value, source FROM question_classification WHERE axis = 'B' GROUP BY question_id) qc_b ON q.id = qc_b.question_id
    WHERE vr.decision = 'queued'
""")
for q in c.fetchall():
    print("-----------------------------------------------------------------")
    print(f"Q#{q['question_id']}: {q['q_pl']}")
    print(f"Media: {q['media']}")
    print(f"Current Classification: Axis A={q['a_val']} ({q['a_src']}), Axis B={q['b_val']} ({q['b_src']})")
    print(f"Vision Suggestion:      Axis A={q['suggested_axis_a']}, Axis B={q['suggested_axis_b']}, Axis C={q['suggested_axis_c']} (Conf: {q['confidence']})")
    print(f"Rationale: {q['rationale']}")

conn.close()
