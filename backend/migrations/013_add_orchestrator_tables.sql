-- Migration: Add orchestrator tables for autonomous execution
-- Created: 2024-01-14

-- Goals table: Stores user objectives for autonomous execution
CREATE TABLE IF NOT EXISTS goals (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    status TEXT CHECK(status IN ('pending', 'active', 'completed', 'failed', 'paused')) DEFAULT 'pending',

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Decomposed cards (JSON array of card IDs)
    cards TEXT,  -- JSON array

    -- Learning extracted after completion
    learning TEXT,
    learning_id TEXT,  -- Qdrant learning ID

    -- Error info if failed
    error TEXT,

    -- Source info (e.g., chat session)
    source TEXT,
    source_id TEXT,

    -- Metrics
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd REAL DEFAULT 0.0
);

-- Create index for status queries
CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);
CREATE INDEX IF NOT EXISTS idx_goals_created_at ON goals(created_at);

-- Orchestrator Actions table: Tracks decisions and executions
CREATE TABLE IF NOT EXISTS orchestrator_actions (
    id TEXT PRIMARY KEY,
    goal_id TEXT NOT NULL,
    action_type TEXT CHECK(action_type IN ('verify_limit', 'decompose', 'execute_card', 'create_fix', 'wait', 'complete_goal')) NOT NULL,

    -- Context and result as JSON
    input_context TEXT,  -- JSON
    output_result TEXT,  -- JSON

    -- Timestamps
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,

    -- Result
    success BOOLEAN,
    error TEXT,

    -- Related card
    card_id TEXT,

    FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
);

-- Create indexes for action queries
CREATE INDEX IF NOT EXISTS idx_actions_goal_id ON orchestrator_actions(goal_id);
CREATE INDEX IF NOT EXISTS idx_actions_started_at ON orchestrator_actions(started_at);

-- Orchestrator Logs table: Short-term memory logs
CREATE TABLE IF NOT EXISTS orchestrator_logs (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    log_type TEXT CHECK(log_type IN ('read', 'query', 'think', 'act', 'record', 'learn', 'error', 'info')) NOT NULL,
    content TEXT NOT NULL,
    context TEXT,  -- JSON
    goal_id TEXT,
    expires_at TIMESTAMP NOT NULL
);

-- Create indexes for log queries
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON orchestrator_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_expires_at ON orchestrator_logs(expires_at);
CREATE INDEX IF NOT EXISTS idx_logs_goal_id ON orchestrator_logs(goal_id);
CREATE INDEX IF NOT EXISTS idx_logs_type ON orchestrator_logs(log_type);
