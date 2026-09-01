-- 033_arabic_search_fold.sql — make Arabic actually findable.
--
-- CORRECTING 032. That migration's comment claimed FTS5's
-- `tokenize = "unicode61 remove_diacritics 2"` folds Arabic tashkeel, so that a
-- search for `حدود` would find `حُدُود` as printed. Measured on 2026-08-31, it
-- does not: `remove_diacritics` covers characters that NFD-decompose into a base
-- letter plus a combining mark, which is a Latin-alphabet story. Arabic tashkeel
-- are standalone combining marks and survive it untouched.
--
-- The measurement, against the live index: `حُدُود` -> 8 hits, `حدود` -> 0.
--
-- WHY THAT IS SERIOUS RATHER THAN COSMETIC. Every Arabic run in these editions
-- carries its marks — that is a standing rule, because Asif does not read
-- unvowelled Arabic. But nobody TYPES tashkeel into a search box. So the one
-- corpus that is most Arabic-bearing was the one nobody could search in Arabic.
--
-- THE FIX is a second indexed column holding the same text with its Arabic runs
-- folded to their consonantal skeletons, by `_arabic_coverage.normalize_arabic`
-- — the function this repo already uses to decide whether two Arabic spans are
-- the same words. Reusing it rather than writing a second folding rule is the
-- point: two answers to "are these the same Arabic" is how they drift.
--
-- Both columns are indexed, and the query is run against both: `refined_text`
-- still matches a vowelled query exactly, `search_text` catches the unvowelled
-- one, and snippets are always drawn from `refined_text` so what is shown to a
-- reader keeps its marks.

ALTER TABLE chapters ADD COLUMN search_text TEXT;

DROP TABLE IF EXISTS chapters_fts;

CREATE VIRTUAL TABLE chapters_fts USING fts5 (
    chapter_title,
    refined_text,
    search_text,           -- Arabic folded to skeletons; English identical
    book_slug UNINDEXED,
    chapter_id UNINDEXED,
    content = 'chapters',
    content_rowid = 'rowid',
    tokenize = "unicode61 remove_diacritics 2"
);
