-- Migration 009: Add mode column to answer_events for Stage 3 IRT/HLR data-model readiness
-- Differentiates standard learning events ('nauka') from readiness exam events ('sprawdzian').

ALTER TABLE answer_events ADD COLUMN mode TEXT NOT NULL DEFAULT 'nauka' CHECK (mode IN ('nauka', 'sprawdzian'));

CREATE INDEX IF NOT EXISTS idx_events_user_mode ON answer_events(user_id, mode);
