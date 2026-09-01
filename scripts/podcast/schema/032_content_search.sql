-- 032_content_search.sql — full-text search across every book and session.
--
-- WHY THIS EXISTS. `book_metadata`, `chapters` and `episodes` have been in this
-- schema since the early migrations, and on 2026-08-31 all three were EMPTY:
-- nine of the ten content tables had zero writers anywhere in the repo. The
-- shape for cross-content search was designed and never wired up, so there was
-- no way to ask "which books discuss ostentation" without grepping the tree.
--
-- WHAT THIS ADDS is only the part that was genuinely missing — an FTS index.
-- The three tables above are unchanged; `hydrate_search_index.py` fills them.
--
-- CONTENTLESS FTS5 (`content=`), deliberately: the chapter text already lives in
-- `chapters.refined_text`, and a default FTS5 table would keep a second copy of
-- every chapter of every book. External-content mode stores only the index and
-- reads the text back through the rowid, so the database does not double in
-- size to gain a search.
--
-- NO TRIGGERS, also deliberately. Triggers would fire mid-hydration on every
-- upsert and make a rebuild several times more expensive than the delete-and-
-- reinsert the hydrator does once at the end. The hydrator owns the index and
-- says so in its log; a trigger would divide that ownership between two places.

CREATE VIRTUAL TABLE IF NOT EXISTS chapters_fts USING fts5 (
    chapter_title,
    refined_text,
    book_slug UNINDEXED,   -- filterable in SQL, not a search term
    chapter_id UNINDEXED,
    content = 'chapters',
    content_rowid = 'rowid',
    tokenize = "unicode61 remove_diacritics 2"
);

-- `remove_diacritics 2` is why this is worth stating: it folds Arabic tashkeel,
-- so a search for "الطور" finds "اَلطُّور" as printed in a vowelled edition.
-- Every Arabic run in these books carries its marks (the standing rule), so
-- without folding, searching for what a reader can type would find nothing.

-- The shelf a book sits on, so a search can be scoped to Sessions or Islamic
-- without joining back out to the filesystem. Derived from content_profile by
-- the same resolver the folder layout uses; recorded here so a query does not
-- have to know that rule.
ALTER TABLE book_metadata ADD COLUMN bucket TEXT;
ALTER TABLE book_metadata ADD COLUMN title TEXT;
ALTER TABLE book_metadata ADD COLUMN content_profile TEXT;

CREATE INDEX IF NOT EXISTS idx_book_metadata_bucket ON book_metadata (bucket);
