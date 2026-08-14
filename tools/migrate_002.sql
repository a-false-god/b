-- Migration 002: Add Elo rating columns to users, questions, and answer_events

-- Users Elo
ALTER TABLE users ADD COLUMN elo_rating INTEGER NOT NULL DEFAULT 1500;

-- Questions Elo
ALTER TABLE questions ADD COLUMN elo_rating INTEGER NOT NULL DEFAULT 1500;

-- Answer Events Elo Tracking
ALTER TABLE answer_events ADD COLUMN user_elo_before INTEGER;
ALTER TABLE answer_events ADD COLUMN user_elo_after INTEGER;
ALTER TABLE answer_events ADD COLUMN question_elo_before INTEGER;
ALTER TABLE answer_events ADD COLUMN question_elo_after INTEGER;

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_questions_elo ON questions(elo_rating);
CREATE INDEX IF NOT EXISTS idx_users_elo ON users(elo_rating);
