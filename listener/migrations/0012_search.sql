-- Advanced search — the index, and the one table the publisher writes.
--
-- WHY A TABLE OF PASSAGES RATHER THAN AN INDEX OVER `chapter`. A chapter is
-- megabytes of HTML and one row; a search result is one paragraph. Indexing the
-- chapter row would make every hit report "somewhere in chapter 4", which is the
-- thing this feature exists to stop. So the publisher breaks each chapter into
-- the same blocks the reader renders and files one row per block, which is also
-- the unit the reading page can ring when a result is clicked.
--
-- WHY THE TEXT IS STORED FOLDED IN ITS OWN COLUMNS. Arabic is written vowelled
-- throughout this library and nobody types tashkeel into a search box, so a
-- query has to match a skeleton. Rather than trust a tokenizer flag to do that
-- across two scripts, both sides fold explicitly: `_listener_search.fold` at
-- publish time and `fold` in app/lib/search-fold.ts at query time, pinned
-- against each other by search-fold.fixtures.json. That is a FIFTH mirror pair
-- and it is a real cost, taken deliberately — the alternative is a query that
-- silently matches nothing on exactly the material this library is made of.
--
-- The display copies (`quote`, `arabic`) are NOT folded. They are what the
-- reader sees and what the reading page matches on to find the passage again.
--
-- CARRIES NO PRIVILEGE BIT, like every migration since 0004. Nothing here says
-- who may read a passage: every query joins to the visibility expression in
-- app/server/access.server.ts, which is the only place that rule is written.
CREATE TABLE search_passage (
  id             INTEGER PRIMARY KEY,
  slug           TEXT NOT NULL,
  -- What KIND of thing matched, which is also the grouping the results page
  -- uses. A closed list for the same reason `media_asset.kind` is one: a typo in
  -- the publisher would otherwise invent a group the UI never renders.
  kind           TEXT NOT NULL CHECK (kind IN ('chapter', 'verse', 'episode', 'blurb')),
  -- Which chapter the passage sits in. NULL on episodes and blurbs, which do not
  -- live in one. Same key the reader routes by, so a link needs no lookup.
  anchor_key     TEXT,
  -- The chapter's or episode's own title, shown above the hit.
  heading        TEXT,
  -- Ordering within a chapter, so several hits in one chapter read in book order
  -- rather than in relevance order, which on a continuous argument is nonsense.
  ordinal        INTEGER NOT NULL DEFAULT 0,
  episode_number INTEGER,
  -- The passage as the reader sees it. This is the ANCHOR AUTHORITY: the reading
  -- page hands it to resolveAnchor, which finds it wherever it now sits and
  -- refuses when it is absent or ambiguous. Never folded, never trimmed.
  quote          TEXT NOT NULL,
  -- Same job as annotation.prefix — see app/lib/anchor.ts — and EMPTY for every
  -- row the publisher writes today, which is deliberate rather than unfinished.
  -- A passage here is a whole block, so it begins at offset 0, and resolveAnchor
  -- tests a prefix against the text BEFORE the hit *within its own block* —
  -- which for offset 0 is the empty string. A non-empty prefix would therefore
  -- fail every comparison and orphan the link. Two identical paragraphs in one
  -- chapter resolve to `orphaned` instead, which lands the reader on the chapter
  -- rather than on a guess. The column stays because sentence-level passages,
  -- if they are ever added, start at a non-zero offset and would need it.
  prefix         TEXT NOT NULL DEFAULT '',
  -- Quotations only. The Arabic exactly as printed, vowelled, ISOLATED from the
  -- caption that shares its block — `quote` still carries both, because that is
  -- what the reading page's textContent will hold.
  arabic         TEXT,
  -- The caption the edition prints above a quotation: `Saying`, or the citation
  -- it resolved when the book was rendered. Stored rather than recomputed so the
  -- search card calls a quotation what the page calls it.
  label          TEXT,
  -- Verses only, and only when the canonical mushaf could name it. Resolved at
  -- publish time by _mushaf.mushaf_reference, never guessed, and left NULL for
  -- Arabic that is quotation rather than scripture.
  surah          INTEGER,
  ayah           INTEGER,
  -- The folded forms. Indexed; never displayed.
  heading_fold   TEXT NOT NULL DEFAULT '',
  body_fold      TEXT NOT NULL DEFAULT '',
  arabic_fold    TEXT NOT NULL DEFAULT ''
);

CREATE INDEX idx_search_passage_slug ON search_passage (slug);
CREATE INDEX idx_search_passage_ref  ON search_passage (surah, ayah);

-- ---------------------------------------------------------------------------
-- search_fts — the full-text index, mirroring the table above
-- ---------------------------------------------------------------------------
-- EXTERNAL CONTENT, so the text is stored once. `content=` points at the table
-- and `content_rowid=` at its primary key; the FTS table holds only the inverted
-- index and reads the columns back through that link.
--
-- D1 supports FTS5 including fts5vocab. One documented consequence to know
-- before it surprises somebody: `wrangler d1 export` does not support databases
-- containing virtual tables. Nothing in this repo runs an export today. If that
-- changes, the workaround is to DROP this table and the three triggers below,
-- export, then re-create them and run the rebuild in the comment at the bottom.
--
-- The tokenizer still removes diacritics even though both sides pre-fold. That
-- is belt and braces on purpose: if a fold ever regresses, the failure should be
-- degraded ranking, not a search box that returns nothing.
CREATE VIRTUAL TABLE search_fts USING fts5(
  heading_fold,
  body_fold,
  arabic_fold,
  content = 'search_passage',
  content_rowid = 'id',
  tokenize = "unicode61 remove_diacritics 2"
);

-- The triggers are what make this safe to hand to the existing publisher.
--
-- publish_to_listener.py rewrites a book by DELETE-then-INSERT per table, which
-- is what makes a re-publish idempotent and makes deletion actually delete. With
-- these in place that existing shape maintains the index for free: there is no
-- second writer to add, and therefore none to forget. A hand-written index
-- update in the publisher would be the thing that drifts the first time somebody
-- changed one and not the other.
CREATE TRIGGER search_passage_ai AFTER INSERT ON search_passage BEGIN
  INSERT INTO search_fts (rowid, heading_fold, body_fold, arabic_fold)
  VALUES (new.id, new.heading_fold, new.body_fold, new.arabic_fold);
END;

CREATE TRIGGER search_passage_ad AFTER DELETE ON search_passage BEGIN
  INSERT INTO search_fts (search_fts, rowid, heading_fold, body_fold, arabic_fold)
  VALUES ('delete', old.id, old.heading_fold, old.body_fold, old.arabic_fold);
END;

CREATE TRIGGER search_passage_au AFTER UPDATE ON search_passage BEGIN
  INSERT INTO search_fts (search_fts, rowid, heading_fold, body_fold, arabic_fold)
  VALUES ('delete', old.id, old.heading_fold, old.body_fold, old.arabic_fold);
  INSERT INTO search_fts (rowid, heading_fold, body_fold, arabic_fold)
  VALUES (new.id, new.heading_fold, new.body_fold, new.arabic_fold);
END;

-- If the index and the table ever disagree — the way they would if a later
-- migration rebuilt `search_passage` by DROP and RENAME, as 0008 and 0011 both
-- did to `media_asset` — this rebuilds it from the table, which is authoritative:
--
--   INSERT INTO search_fts (search_fts) VALUES ('rebuild');
--
-- test/search-index.test.ts asserts the two carry the same number of rows, so a
-- desync fails a test rather than quietly returning fewer results every day.
