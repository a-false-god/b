-- M6.1 — Rating engine revision (Asymmetric Rasch skill model + Question stats)
-- Supersedes Elo ratings and rating_history tables from M6

DROP TABLE IF EXISTS ratings;
DROP TABLE IF EXISTS rating_history;

CREATE TABLE IF NOT EXISTS user_skill (
  user_id INTEGER NOT NULL REFERENCES users(id),
  axis_value TEXT,            -- NULL = global, else axis-B domain
  theta REAL NOT NULL DEFAULT 0.0,
  n INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (user_id, axis_value)
);

CREATE TABLE IF NOT EXISTS skill_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  theta REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_skill_history_user ON skill_history(user_id, created_at);

CREATE TABLE IF NOT EXISTS question_stats (
  question_id INTEGER PRIMARY KEY REFERENCES questions(id),
  attempts INTEGER NOT NULL DEFAULT 0,
  wrong INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
