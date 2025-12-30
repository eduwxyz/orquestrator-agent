-- Migration: Add executions and execution_logs tables
-- Description: Create tables to persist card execution state and logs

-- Create executions table
CREATE TABLE IF NOT EXISTS executions (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL,
    status TEXT CHECK(status IN ('idle', 'running', 'success', 'error')) DEFAULT 'idle',
    command TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration INTEGER,
    result TEXT,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
);

-- Create execution_logs table
CREATE TABLE IF NOT EXISTS execution_logs (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    type TEXT,
    content TEXT,
    sequence INTEGER NOT NULL,
    FOREIGN KEY (execution_id) REFERENCES executions(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_executions_card_active ON executions(card_id, is_active);
CREATE INDEX IF NOT EXISTS idx_execution_logs_execution ON execution_logs(execution_id, sequence);