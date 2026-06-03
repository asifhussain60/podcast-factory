-- 028_section_depths.sql
-- Wave N: per-chapter section depth assignments (pipeline guesses, human corrects).
-- Each section is identified by (book_slug, chapter_id, section_ordinal).
-- section_slug is derived from the section title at build time and stored for
-- display; ordinal is the stable anchor (titles can be edited, ordinal cannot).

CREATE TABLE IF NOT EXISTS section_depths (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_slug       TEXT    NOT NULL,
    chapter_id      TEXT    NOT NULL,
    section_ordinal INTEGER NOT NULL,   -- 0-based ordinal of the h2 in the chapter
    section_slug    TEXT    NOT NULL,   -- slugified section title (display only, not the key)
    depth_level     TEXT    NOT NULL,   -- one of the 6 CONTENT_LEVEL_LADDER codes
    source          TEXT    NOT NULL DEFAULT 'pipeline',  -- 'pipeline' | 'human'
    created_at      TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at      TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (book_slug, chapter_id, section_ordinal)
);

CREATE INDEX IF NOT EXISTS idx_section_depths_chapter
    ON section_depths (book_slug, chapter_id);
