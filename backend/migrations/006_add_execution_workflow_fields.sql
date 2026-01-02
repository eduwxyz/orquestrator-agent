-- Migration: Add workflow fields to executions table
-- Description: Add title, workflow_stage, and workflow_error columns to executions table

-- Add title column
ALTER TABLE executions ADD COLUMN title TEXT;

-- Add workflow_stage column
ALTER TABLE executions ADD COLUMN workflow_stage TEXT;

-- Add workflow_error column
ALTER TABLE executions ADD COLUMN workflow_error TEXT;
