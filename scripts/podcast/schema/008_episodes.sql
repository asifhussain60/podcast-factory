-- 008_episodes.sql — Episode metadata and authoring state.
-- Depends on: 003_book_metadata.sql, 007_chapters.sql.

CREATE TABLE IF NOT EXISTS episodes (
    id              TEXT    PRIMARY KEY,           -- "<slug>/ep<NN>"
    book_slug       TEXT    NOT NULL,              -- FK → book_metadata.slug (advisory)
    episode_number  INTEGER NOT NULL,
    chapter_id      TEXT,                          -- FK → chapters.chapter_id (advisory)
    title           TEXT,
    framing_text    TEXT,                          -- NotebookLM customize-prompt text
    source_bundle   TEXT,                          -- path to the uploaded source file
    build_status    TEXT    NOT NULL DEFAULT 'pending'
                    CHECK (build_status IN ('pending', 'built', 'shipped', 'failed')),
    challenger_verdict TEXT,                       -- "SHIP-READY" | "SHIP-WITH-CAUTION" | "REWORK"
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (book_slug, episode_number)
);

CREATE INDEX IF NOT EXISTS idx_episodes_book    ON episodes (book_slug);
CREATE INDEX IF NOT EXISTS idx_episodes_status  ON episodes (build_status);
CREATE INDEX IF NOT EXISTS idx_episodes_verdict ON episodes (challenger_verdict);
