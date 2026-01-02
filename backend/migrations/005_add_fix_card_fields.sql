-- Add fix card tracking fields to cards table
-- This migration adds support for automatic fix card creation when tests fail

ALTER TABLE cards
ADD COLUMN parent_card_id VARCHAR(36) DEFAULT NULL,
ADD COLUMN is_fix_card BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN test_error_context TEXT DEFAULT NULL;

-- Add foreign key constraint for parent_card_id
ALTER TABLE cards
ADD CONSTRAINT fk_parent_card
FOREIGN KEY (parent_card_id)
REFERENCES cards(id)
ON DELETE SET NULL;

-- Create index for faster queries on parent cards
CREATE INDEX idx_parent_card_id ON cards(parent_card_id);

-- Create index for finding active fix cards
CREATE INDEX idx_fix_cards ON cards(is_fix_card, column_id) WHERE is_fix_card = TRUE;