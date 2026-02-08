-- Add model configuration columns to cards table
ALTER TABLE cards ADD COLUMN model_plan VARCHAR(20) DEFAULT 'opus-4.5';
ALTER TABLE cards ADD COLUMN model_implement VARCHAR(20) DEFAULT 'opus-4.5';
ALTER TABLE cards ADD COLUMN model_test VARCHAR(20) DEFAULT 'opus-4.5';
ALTER TABLE cards ADD COLUMN model_review VARCHAR(20) DEFAULT 'opus-4.5';
