-- Migration 003: Add Password Auth
ALTER TABLE customers ADD COLUMN IF NOT EXISTS username TEXT UNIQUE;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS password_hash TEXT;
