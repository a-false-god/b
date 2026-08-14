-- Migration 001: Schema setup for Prawko B MVP

CREATE TABLE IF NOT EXISTS questions (
  id INTEGER PRIMARY KEY,
  lp INTEGER,
  scope TEXT NOT NULL,
  points INTEGER NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('TN', 'ABC')),
  correct TEXT NOT NULL,
  media TEXT,
  media_kind TEXT,
  categories TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'pending')),
  q_pl TEXT NOT NULL,
  a_pl TEXT,
  b_pl TEXT,
  c_pl TEXT,
  q_en TEXT,
  a_en TEXT,
  b_en TEXT,
  c_en TEXT,
  q_de TEXT,
  a_de TEXT,
  b_de TEXT,
  c_de TEXT,
  q_ua TEXT,
  a_ua TEXT,
  b_ua TEXT,
  c_ua TEXT,
  pjm_q TEXT
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  login TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS taxonomy_values (
  axis TEXT NOT NULL CHECK (axis IN ('A','B','C')),
  value TEXT NOT NULL,
  definition TEXT NOT NULL,
  PRIMARY KEY (axis, value)
);

CREATE TABLE IF NOT EXISTS question_classification (
  question_id INTEGER NOT NULL REFERENCES questions(id),
  axis TEXT NOT NULL CHECK (axis IN ('A','B','C')),
  value TEXT NOT NULL,
  confidence REAL,
  source TEXT NOT NULL CHECK (source IN ('llm','manual')),
  PRIMARY KEY (question_id, axis, value)
);

CREATE TABLE IF NOT EXISTS answer_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  question_id INTEGER NOT NULL REFERENCES questions(id),
  chosen TEXT NOT NULL,
  is_correct INTEGER NOT NULL,
  time_ms INTEGER NOT NULL,
  session_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_user ON answer_events(user_id, question_id);
CREATE INDEX IF NOT EXISTS idx_events_question ON answer_events(question_id);
