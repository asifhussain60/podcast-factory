-- 003_book_metadata.sql — Per-book pipeline state snapshot.
-- Idempotent: guarded by IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS book_metadata (
    slug           TEXT PRIMARY KEY,
    category       TEXT NOT NULL DEFAULT 'books',  -- "books" | "lectures" | "asbaaq" | ...
    archetype      TEXT,                           -- "scholarly-deep-dive" | "play-novel" | ...
    meta_yml       TEXT,                           -- JSON1 snapshot of the book's meta.yml
    current_phase  TEXT,
    phase_status   TEXT,
    last_updated   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_book_metadata_archetype ON book_metadata (archetype);
CREATE INDEX IF NOT EXISTS idx_book_metadata_category  ON book_metadata (category);
