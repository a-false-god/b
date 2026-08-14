-- Migration 005: Schema evolution for P4 Vision Pass (multimodal verification)
-- 1. Extend CHECK constraint on question_classification to allow source='vision'
CREATE TABLE IF NOT EXISTS question_classification_new (
  question_id INTEGER NOT NULL REFERENCES questions(id),
  axis TEXT NOT NULL CHECK (axis IN ('A','B','C')),
  value TEXT NOT NULL,
  confidence REAL,
  source TEXT NOT NULL CHECK (source IN ('llm','manual','vision')),
  PRIMARY KEY (question_id, axis, value)
);

INSERT OR IGNORE INTO question_classification_new (question_id, axis, value, confidence, source)
SELECT question_id, axis, value, confidence, source FROM question_classification;

DROP TABLE IF EXISTS question_classification;
ALTER TABLE question_classification_new RENAME TO question_classification;

-- 2. Audit and detailed trace log for multimodal vision review runs
CREATE TABLE IF NOT EXISTS vision_review (
  question_id INTEGER PRIMARY KEY REFERENCES questions(id),
  model TEXT NOT NULL,
  n_frames INTEGER NOT NULL,
  suggested_axis_a TEXT NOT NULL,
  suggested_axis_b TEXT NOT NULL,
  suggested_axis_c TEXT NOT NULL,
  confidence REAL NOT NULL,
  rationale TEXT,
  decision TEXT NOT NULL CHECK (decision IN ('auto_accepted', 'auto_corrected', 'queued', 'skipped_no_media')),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_vision_review_decision ON vision_review(decision);
