-- GBP AI Agent SaaS — Phase 1 schema
-- Tables: gbp_credentials, telegram_chat_links, business_content_profiles, post_history

-- Requires pgcrypto for gen_random_uuid(); enable once per database
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- customers: minimal root table so the others have something to key off of.
-- Expand later with billing/tier fields (Phase 6) — kept lean for now.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    customer_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT UNIQUE NOT NULL,
    business_name   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- gbp_credentials: per-customer, per-location OAuth tokens for the forked
-- MCP server to read instead of its stock local-file storage.
-- One row per connected GBP location (v1 = single-location, but don't
-- hardcode that constraint into the schema itself).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gbp_credentials (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    location_id         TEXT NOT NULL,           -- Google GBP location resource id
    account_id          TEXT,                    -- Google GBP account resource id (parent of location)
    access_token        TEXT NOT NULL,           -- store ENCRYPTED (app-layer encryption, e.g. pgcrypto/KMS)
    refresh_token       TEXT NOT NULL,           -- store ENCRYPTED
    token_expires_at    TIMESTAMPTZ NOT NULL,
    scopes              TEXT,                    -- space-delimited OAuth scopes granted
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (customer_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_gbp_credentials_customer ON gbp_credentials(customer_id);

-- ---------------------------------------------------------------------------
-- telegram_chat_links: maps a Telegram chat_id to a customer_id after the
-- one-time-code linking flow (website OAuth -> code -> sent to bot).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS telegram_chat_links (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id         BIGINT UNIQUE NOT NULL,      -- Telegram chat_id (can be negative for groups; BIGINT is safe)
    customer_id     UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    link_code       TEXT,                        -- the one-time code, kept for audit/debugging
    linked_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_telegram_chat_links_customer ON telegram_chat_links(customer_id);

-- ---------------------------------------------------------------------------
-- business_content_profiles: the compact, reusable JSON profile produced by
-- the one-time signup LLM call (tone, pillars, keywords, example phrasing).
-- Refreshed periodically, so keep history via updated_at rather than
-- versioning rows for now — simplest thing that works for v1.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS business_content_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    location_id         TEXT NOT NULL,
    profile_json        JSONB NOT NULL,          -- {tone, core_services, content_pillars, example_phrasing, keywords, ...}
    source_intake_json  JSONB,                   -- raw onboarding form answers, kept for re-derivation if needed
    last_refreshed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (customer_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_content_profiles_customer ON business_content_profiles(customer_id);
CREATE INDEX IF NOT EXISTS idx_content_profiles_json ON business_content_profiles USING GIN (profile_json);

-- ---------------------------------------------------------------------------
-- post_history: every draft the agent produces, its validator outcome, owner
-- decision, and (if published) the resulting GBP post reference. This is
-- both the audit trail and the source for the few-shot feedback loop.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS post_history (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    location_id         TEXT NOT NULL,
    post_type           TEXT NOT NULL CHECK (post_type IN ('standard', 'event', 'offer', 'alert')),
    draft_content       JSONB NOT NULL,          -- {title, body, cta, media_urls, event/offer fields...}
    validator_result    JSONB,                   -- {passed: bool, errors: [...], auto_fixed_fields: [...]}
    owner_decision       TEXT NOT NULL DEFAULT 'pending'
                          CHECK (owner_decision IN ('pending', 'approved', 'edited', 'rejected')),
    final_content       JSONB,                   -- content actually sent to MCP publish tool, if different from draft
    gbp_post_id         TEXT,                    -- resource id returned by create_local_post, once published
    published_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_post_history_customer ON post_history(customer_id);
CREATE INDEX IF NOT EXISTS idx_post_history_status ON post_history(owner_decision);
CREATE INDEX IF NOT EXISTS idx_post_history_created ON post_history(created_at DESC);

-- ---------------------------------------------------------------------------
-- updated_at auto-touch trigger (shared across tables that track it)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE TRIGGER trg_gbp_credentials_updated_at
    BEFORE UPDATE ON gbp_credentials
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE TRIGGER trg_post_history_updated_at
    BEFORE UPDATE ON post_history
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
