-- Migration 003: Add unique index on location_id to optimize credentials lookup by location_id only.
-- Since google location_ids are globally unique, we can enforce uniqueness at this level as well.
CREATE UNIQUE INDEX IF NOT EXISTS idx_gbp_credentials_location_id ON gbp_credentials(location_id);
