-- The Scholar Companion — the explanation cards written against a chapter.
--
-- Written by the publish step (scripts/podcast/publish_to_listener.py) from
-- `content/<Bucket>/<slug>/_system/companion-notes/<section-key>.json`, the files
-- the Book Composer's Ismaili Scholar Companion panel writes. They never enter
-- book.md and never enter the PDF, and they do not enter this database as
-- anything a reader can reach: `companionFor` in app/server/catalog.server.ts
-- refuses to issue a query at all unless the session is the administrator's.
--
-- A TABLE OF ITS OWN, not columns on `chapter`, and that is the whole point.
-- `chapterOf` runs for every reader on every chapter; a column there would be
-- read into a loader payload by default and would leak the day someone widened a
-- SELECT. A separate table is a separate query, and the query is simply never
-- made for anyone else — the data has no path to a response it does not belong
-- in, rather than a filter standing between it and one.
--
-- It carries no privilege bit, exactly like 0004_catalog.sql: nothing here
-- decides whether anything is readable, and the publish step still never names
-- `content_unit.status` or `open_to_all`.
CREATE TABLE companion_note (
  slug        TEXT NOT NULL,
  -- The chapter, keyed the way every other table keys one. The notes are filed
  -- on disk under a DIFFERENT key — `sectionKeyFromHeading`, which keeps the
  -- heading's ordinal — and the publish step is where the two are reconciled, so
  -- nothing downstream has to know that two keying rules exist.
  anchor_key  TEXT NOT NULL,
  note_id     TEXT NOT NULL,
  idx         INTEGER NOT NULL,        -- order within the chapter, as filed
  title       TEXT,                    -- the card's short label; may be absent
  -- The VERBATIM chapter sentence the card explains. The reader resolves it
  -- against the chapter's live text to tint the passage, and refuses on
  -- ambiguity rather than guessing — see app/lib/anchor.ts.
  quote       TEXT,
  -- Rendered ONCE, here, by plan-dashboard's cardMarkdownToHtml — the same
  -- function the Composer's cards go through. A second markdown implementation
  -- in the Worker would be a second answer to what one note says.
  body_html   TEXT NOT NULL,
  -- The etymology rows as a JSON array of strings, exactly as stored on disk.
  -- The verified `morphology` block that sits beside them in the Composer is
  -- deliberately absent: it is computed at read time from the Quranic morphology
  -- DB and is never persisted, so persisting it here would be the first copy
  -- able to go stale.
  etymology   TEXT,
  PRIMARY KEY (slug, note_id)
);

CREATE INDEX idx_companion_chapter ON companion_note (slug, anchor_key, idx);
