-- Migration 008: Secondary performance indexes
-- Speeds up Review Queue / untriaged classification lookups, Exam pool selection, and Answer Event window partitioning.

CREATE INDEX IF NOT EXISTS idx_qc_source ON question_classification(source);
CREATE INDEX IF NOT EXISTS idx_questions_scope_points ON questions(scope, points);
CREATE INDEX IF NOT EXISTS idx_events_user_qid_id ON answer_events(user_id, question_id, id DESC);
