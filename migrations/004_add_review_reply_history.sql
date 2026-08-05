-- Migration 004: Add Review Reply History
CREATE TABLE IF NOT EXISTS review_reply_history (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    location_id         TEXT NOT NULL,
    review_id           TEXT NOT NULL,
    reviewer_name       TEXT,
    review_text         TEXT,
    star_rating         INT,
    draft_reply         TEXT NOT NULL,
    owner_decision       TEXT NOT NULL DEFAULT 'pending'
                          CHECK (owner_decision IN ('pending', 'approved', 'rejected')),
    published_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (location_id, review_id)
);

CREATE INDEX IF NOT EXISTS idx_review_reply_customer ON review_reply_history(customer_id);
CREATE INDEX IF NOT EXISTS idx_review_reply_status ON review_reply_history(owner_decision);

CREATE TRIGGER trg_review_reply_history_updated_at
    BEFORE UPDATE ON review_reply_history
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
