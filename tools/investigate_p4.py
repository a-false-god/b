import sqlite3
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_explanations import compute_question_content_hash

conn = sqlite3.connect("data/prawko.sqlite")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 1. Investigate Hash Mismatches
print("="*70)
print("1. INVESTIGATING HASH MISMATCHES")
print("="*70)
cursor.execute("""
    SELECT q.id, q.q_pl, q.a_pl, q.b_pl, q.c_pl, q.correct, q.media,
           qe.content_hash, qe.needs_vision_review, qe.explanation, qe.legal_basis,
           qc_b.value as axis_b, vr.decision, vr.model
    FROM questions q
    JOIN question_explanations qe ON q.id = qe.question_id
    LEFT JOIN (SELECT question_id, value FROM question_classification WHERE axis = 'B' GROUP BY question_id) qc_b ON q.id = qc_b.question_id
    LEFT JOIN vision_review vr ON q.id = vr.question_id
    WHERE q.categories LIKE '%"B"%'
""")
all_rows = cursor.fetchall()
mismatches = []
for r in all_rows:
    q_dict = dict(r)
    h_text = compute_question_content_hash(q_dict, axis_signature=r["axis_b"], mode="text")
    h_vis = compute_question_content_hash(q_dict, axis_signature=r["axis_b"], mode="vision")
    stored_hash = r["content_hash"]
    if stored_hash not in (h_text, h_vis):
        mismatches.append((q_dict, stored_hash, h_text, h_vis))

print(f"Total Hash Mismatches Found: {len(mismatches)}")
for m, stored, h_text, h_vis in mismatches:
    print(f"\nQuestion #{m['id']}: {m['q_pl']}")
    print(f" - Media: {m['media']}")
    print(f" - Stored Hash: {stored} | Expected text: {h_text} | Expected vision: {h_vis}")
    print(f" - Axis B: {m['axis_b']} | Decision: {m['decision']} | Needs Vision: {m['needs_vision_review']}")
    print(f" - Explanation: {m['explanation'][:80]}...")

# 2. Investigate the 8 Queued Questions
print("\n" + "="*70)
print("2. INVESTIGATING 8 QUEUED QUESTIONS (MANUAL-HOLD / UNCERTAIN)")
print("="*70)
cursor.execute("""
    SELECT vr.question_id, q.q_pl, q.media, q.media_kind,
           qc_a.value as curr_a, qc_a.source as src_a,
           qc_b.value as curr_b, qc_b.source as src_b,
           vr.suggested_axis_a, vr.suggested_axis_b, vr.suggested_axis_c,
           vr.confidence, vr.rationale
    FROM vision_review vr
    JOIN questions q ON vr.question_id = q.id
    LEFT JOIN (SELECT question_id, value, source FROM question_classification WHERE axis = 'A' GROUP BY question_id) qc_a ON q.id = qc_a.question_id
    LEFT JOIN (SELECT question_id, value, source FROM question_classification WHERE axis = 'B' GROUP BY question_id) qc_b ON q.id = qc_b.question_id
    WHERE vr.decision = 'queued'
""")
queued_rows = cursor.fetchall()
print(f"Total Queued Questions: {len(queued_rows)}")
for idx, r in enumerate(queued_rows, 1):
    print(f"\n[{idx}] Question #{r['question_id']}: {r['q_pl']}")
    print(f"    Media: {r['media']} ({r['media_kind']})")
    print(f"    Current: Axis A={r['curr_a']} ({r['src_a']}), Axis B={r['curr_b']} ({r['src_b']})")
    print(f"    Vision Suggestion: Axis A={r['suggested_axis_a']}, Axis B={r['suggested_axis_b']}, Axis C={r['suggested_axis_c']} (Conf: {r['confidence']})")
    print(f"    Rationale: {r['rationale']}")

# 3. Sample 20 Questions Auto-Corrected to znaki_i_sygnaly
print("\n" + "="*70)
print("3. SAMPLE OF 20 QUESTIONS AUTO-CORRECTED TO 'znaki_i_sygnaly'")
print("="*70)
cursor.execute("""
    SELECT vr.question_id, q.q_pl, q.media, q.media_kind,
           vr.suggested_axis_b, vr.confidence, vr.rationale,
           qe.legal_basis, qe.explanation
    FROM vision_review vr
    JOIN questions q ON vr.question_id = q.id
    JOIN question_explanations qe ON q.id = qe.question_id
    WHERE vr.decision = 'auto_corrected' AND vr.suggested_axis_b = 'znaki_i_sygnaly'
""")
auto_corrected = cursor.fetchall()
print(f"Total Auto-Corrected to znaki_i_sygnaly: {len(auto_corrected)}")
random.seed(42)
sample_20 = random.sample(auto_corrected, min(20, len(auto_corrected)))
for idx, r in enumerate(sample_20, 1):
    print(f"\n[{idx:02d}] Question #{r['question_id']}: {r['q_pl']}")
    print(f"     Media: {r['media']} ({r['media_kind']})")
    print(f"     Legal Basis: {r['legal_basis']}")
    print(f"     Rationale: {r['rationale']}")
    print(f"     Explanation: {r['explanation'][:90]}...")

conn.close()
