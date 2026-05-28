-- 007_chapters.sql — Per-chapter pipeline state and content snapshot.
-- Depends on: 003_book_metadata.sql.

CREATE TABLE IF NOT EXISTS chapters (
    id              TEXT    PRIMARY KEY,           -- "<slug>/<chapter_id>"
    book_slug       TEXT    NOT NULL,              -- FK → book_metadata.slug (advisory)
    chapter_id      TEXT    NOT NULL,              -- e.g. "ch01", "ch02"
    chapter_title   TEXT,
    source_text     TEXT,                          -- original Arabic (post-OCR)
    refined_text    TEXT,                          -- post-0b English refinement
    word_count      INTEGER,
    phase_reached   TEXT,                          -- last successfully completed phase
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (book_slug, chapter_id)
);

CREATE INDEX IF NOT EXISTS idx_chapters_book  ON chapters (book_slug);
CREATE INDEX IF NOT EXISTS idx_chapters_phase ON chapters (phase_reached);
