-- 031_action_items.sql
-- Deferred AI action-item queue: the human stamps a paragraph or a selected term
-- in the Studio editor with an action (etymology, rewrite, improve, ...); a later
-- CLI pass drains the pending rows and writes results back into `result`.
--
-- Anchoring: para_ordinal is the 0-based top-level node index (a display hint that
-- can drift if the chapter is re-edited). anchor_text stores the ACTUAL target text
-- so the CLI never depends on the ordinal being stable. term_text holds the selected
-- word/phrase for scope='term' and '' (empty string, not NULL) for scope='paragraph'
-- so the UNIQUE identity below is well-defined.
--
-- Identity = (book_slug, chapter_id, para_ordinal, term_text, action_kind): stamping
-- the same action on the same target twice is a no-op (toggle handled in the API/UI).

CREATE TABLE IF NOT EXISTS action_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    book_slug    TEXT    NOT NULL,
    chapter_id   TEXT    NOT NULL,
    scope        TEXT    NOT NULL,                    -- 'paragraph' | 'term'
    para_ordinal INTEGER NOT NULL,                    -- 0-based top-level node index (display hint)
    term_text    TEXT    NOT NULL DEFAULT '',         -- selected word/phrase for term scope; '' for paragraph
    anchor_text  TEXT    NOT NULL DEFAULT '',         -- drift-proof copy of the target text
    action_kind  TEXT    NOT NULL,                    -- registry kind: etymology | rewrite | rephrase | ...
    note         TEXT,                                -- optional human note
    status       TEXT    NOT NULL DEFAULT 'pending',  -- 'pending' | 'resolved' | 'dismissed'
    result       TEXT,                                -- JSON written by the CLI drain pass (step 3); NULL until resolved
    source       TEXT    NOT NULL DEFAULT 'human',    -- 'human' | 'pipeline'
    created_at   TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at   TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (book_slug, chapter_id, para_ordinal, term_text, action_kind)
);

CREATE INDEX IF NOT EXISTS idx_action_items_chapter
    ON action_items (book_slug, chapter_id);

CREATE INDEX IF NOT EXISTS idx_action_items_pending
    ON action_items (book_slug, status);
