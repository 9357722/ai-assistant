-- Migration: Add idempotency_key column to orders table
-- Date: 2026-06-07

-- Add idempotency_key column
ALTER TABLE orders ADD COLUMN idempotency_key VARCHAR(64) AFTER remark;

-- Add unique index (ignores NULL values, so multiple NULLs are allowed)
ALTER TABLE orders ADD UNIQUE INDEX idx_idempotency (idempotency_key, user_id);
