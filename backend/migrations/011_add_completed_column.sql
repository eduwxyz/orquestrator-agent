-- Add completed_at column to cards table for auto-cleanup
ALTER TABLE cards ADD COLUMN completed_at TIMESTAMP;

-- Migrate existing cards in 'done' column to have a completed_at timestamp
-- Using updated_at as a fallback for retroactive timestamping
UPDATE cards
SET completed_at = updated_at
WHERE column_id = 'done' AND completed_at IS NULL;
