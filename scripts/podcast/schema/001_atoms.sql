-- 001_atoms.sql — Core atom table (Quran verses, hadith, terms, citations).
-- Idempotent: guarded by IF NOT EXISTS. Run order matters — this is applied first.

CREATE TABLE IF NOT EXISTS atoms (
    id               TEXT    PRIMARY KEY,  -- e.g. "quran:2:255", "hadith:bukhari:1"
    type             TEXT    NOT NULL      -- "quran" | "hadith" | "term" | "citation"
                     CHECK  (type IN ('quran', 'hadith', 'term', 'citation')),
    body             TEXT    NOT NULL,     -- JSON1 — type-specific schema
    first_seen_book  TEXT,                 -- FK → book_metadata.slug (advisory)
    first_seen_chapter TEXT,
    first_seen_date  TEXT,                 -- ISO-8601 date
    confidence       REAL    NOT NULL DEFAULT 1.0
                     CHECK  (confidence >= 0.0 AND confidence <= 1.0),
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_atoms_type ON atoms (type);
CREATE INDEX IF NOT EXISTS idx_atoms_first_seen_book ON atoms (first_seen_book);
