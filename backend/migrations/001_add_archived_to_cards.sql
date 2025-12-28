-- Migration: Add archived column to cards table
-- Date: 2024-12-27
-- Description: Add archived boolean field to support archiving cards in the Done column

-- Add the archived column with default value FALSE
ALTER TABLE cards ADD COLUMN archived BOOLEAN DEFAULT FALSE NOT NULL;

-- Create an index on the archived column for better query performance
CREATE INDEX idx_cards_archived ON cards(archived);
