-- 006_manual_review_queue.sql — Items flagged for human resolution.
-- Depends on: 003_book_metadata.sql.

CREATE TABLE IF NOT EXISTS manual_review_queue (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    book_slug    TEXT    NOT NULL,         -- FK → book_metadata.slug (advisory)
    chapter_id   TEXT,
    reason       TEXT    NOT NULL,
    payload      TEXT,                    -- JSON1 — context data (atom candidate, citation, etc.)
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    resolved_at  TEXT,                    -- NULL until human resolves
    resolution   TEXT                     -- free-text note on how it was resolved
);

CREATE INDEX IF NOT EXISTS idx_mrq_book       ON manual_review_queue (book_slug);
CREATE INDEX IF NOT EXISTS idx_mrq_resolved   ON manual_review_queue (resolved_at);
