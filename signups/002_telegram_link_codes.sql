-- Short-lived one-time codes used to link a Telegram chat_id to a customer_id.
-- Separate from telegram_chat_links (001) because these rows are disposable —
-- created after website OAuth, consumed once, and irrelevant afterward.

CREATE TABLE IF NOT EXISTS telegram_link_codes (
    code            TEXT PRIMARY KEY,
    customer_id     UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    expires_at      TIMESTAMPTZ NOT NULL,
    used_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_telegram_link_codes_customer ON telegram_link_codes(customer_id);

-- Optional cleanup: periodically delete expired, unused codes.
-- DELETE FROM telegram_link_codes WHERE expires_at < now() AND used_at IS NULL;
