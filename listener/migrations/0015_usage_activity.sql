-- ---------------------------------------------------------------------------
-- usage_activity — admin-only reading and listening visibility
-- ---------------------------------------------------------------------------
-- Forward-looking, country-level activity. This deliberately stores no raw IP
-- address and no user-agent. Country is captured as a two-letter code from
-- Cloudflare request metadata when present, or XX when the local/dev request
-- cannot say.
--
-- The row is a compact ledger entry for an activity target, not a clickstream:
-- one person, one book, one surface, one chapter/episode, one country. Repeated
-- progress writes increment the count and move last_seen_at. That answers the
-- administrator's "who used what, when, and from where" question without keeping
-- a permanent record of every scroll tick.
CREATE TABLE usage_activity (
  user_email      TEXT NOT NULL COLLATE NOCASE,
  slug            TEXT NOT NULL,
  kind            TEXT NOT NULL CHECK (kind IN ('read', 'listen')),
  target_key      TEXT NOT NULL,
  country_code    TEXT NOT NULL DEFAULT 'XX' CHECK (length(country_code) = 2),
  first_seen_at   TEXT NOT NULL,
  last_seen_at    TEXT NOT NULL,
  signal_count    INTEGER NOT NULL DEFAULT 1 CHECK (signal_count >= 1),
  PRIMARY KEY (user_email, slug, kind, target_key, country_code)
);

CREATE INDEX idx_usage_activity_recent ON usage_activity (last_seen_at DESC);
CREATE INDEX idx_usage_activity_person ON usage_activity (user_email, last_seen_at DESC);
CREATE INDEX idx_usage_activity_country ON usage_activity (country_code, last_seen_at DESC);
CREATE INDEX idx_usage_activity_content ON usage_activity (slug, kind, last_seen_at DESC);
