-- Migration: Add activity_logs table
-- Description: Create table to track card activity history with real timestamps

-- Create activity_logs table
CREATE TABLE IF NOT EXISTS activity_logs (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL,
    activity_type TEXT CHECK(activity_type IN ('created', 'moved', 'completed', 'archived', 'updated', 'executed', 'commented')) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Activity metadata
    from_column TEXT,
    to_column TEXT,
    old_value TEXT,
    new_value TEXT,
    user_id TEXT,
    description TEXT,

    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_activity_logs_card ON activity_logs(card_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_activity_logs_type ON activity_logs(activity_type);
