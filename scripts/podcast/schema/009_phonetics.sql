-- 009_phonetics.sql — Per-book phonetics dictionary.
-- Stores the pronunciation guidance generated in phase 0c so it can be
-- reused by downstream authoring without re-running the full phonetics pass.
-- Depends on: 003_book_metadata.sql.

CREATE TABLE IF NOT EXISTS phonetics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    book_slug   TEXT    NOT NULL,              -- FK → book_metadata.slug (advisory)
    term        TEXT    NOT NULL,              -- original Arabic or transliterated form
    pronunciation TEXT  NOT NULL,             -- IPA or anglicised guide string
    term_type   TEXT    NOT NULL DEFAULT 'name'
                CHECK (term_type IN ('name', 'place', 'title', 'concept', 'other')),
    notes       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (book_slug, term)
);

CREATE INDEX IF NOT EXISTS idx_phonetics_book ON phonetics (book_slug);
CREATE INDEX IF NOT EXISTS idx_phonetics_term ON phonetics (term);
