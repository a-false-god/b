-- Migration 004: Explanations cache & Weekly exam check metrics

CREATE TABLE IF NOT EXISTS question_explanations (
  question_id INTEGER PRIMARY KEY REFERENCES questions(id),
  explanation TEXT NOT NULL,
  legal_basis TEXT,
  source TEXT NOT NULL CHECK (source IN ('llm', 'manual')),
  content_hash TEXT,
  needs_vision_review INTEGER DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS exam_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  score INTEGER NOT NULL,
  max_score INTEGER NOT NULL DEFAULT 74,
  passed INTEGER NOT NULL,
  time_seconds INTEGER NOT NULL,
  details_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_exam_checks_user ON exam_checks(user_id, created_at);

-- Index to optimize distinct date count for Mastery calculation
CREATE INDEX IF NOT EXISTS idx_events_user_correct_date ON answer_events(user_id, is_correct, question_id, created_at);
