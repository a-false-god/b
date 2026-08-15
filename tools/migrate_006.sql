-- Migration 006: Extend CHECK constraint on vision_review to allow decision='manual_accepted'
-- and update the 8 manually triaged questions to distinguish human from auto approvals.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS vision_review_new (
  question_id INTEGER PRIMARY KEY REFERENCES questions(id),
  model TEXT NOT NULL,
  n_frames INTEGER NOT NULL,
  suggested_axis_a TEXT NOT NULL,
  suggested_axis_b TEXT NOT NULL,
  suggested_axis_c TEXT NOT NULL,
  confidence REAL NOT NULL,
  rationale TEXT,
  decision TEXT NOT NULL CHECK (decision IN ('auto_accepted', 'auto_corrected', 'queued', 'skipped_no_media', 'manual_accepted')),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO vision_review_new (
  question_id, model, n_frames, suggested_axis_a, suggested_axis_b,
  suggested_axis_c, confidence, rationale, decision, created_at
)
SELECT
  question_id, model, n_frames, suggested_axis_a, suggested_axis_b,
  suggested_axis_c, confidence, rationale, decision, created_at
FROM vision_review;

DROP TABLE IF EXISTS vision_review;
ALTER TABLE vision_review_new RENAME TO vision_review;

CREATE INDEX IF NOT EXISTS idx_vision_review_decision ON vision_review(decision);

-- Update the 8 manually triaged rows
UPDATE vision_review
SET decision = 'manual_accepted'
WHERE question_id IN (100, 469, 475, 477, 478, 480, 486, 544);

COMMIT;
