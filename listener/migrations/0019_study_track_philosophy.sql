-- Add 'philosophy' to study_track.
--
-- The Audiobook lane (f55e2971) added it to `STUDY_TRACKS` in
-- `scripts/podcast/_listener_book.py` — the set that decides which value
-- survives the publish — without widening the CHECK the value lands against.
-- The two have disagreed since, and the disagreement is not cosmetic: a book
-- carrying `study_track: philosophy` fails its ENTIRE publish on the constraint,
-- so White Nights could not reach the Library at all. Nothing was wrong with
-- the book.
--
-- SQLite cannot ALTER a CHECK in place, so the table is rebuilt exactly as 0017
-- did it: new shape, copy across, swap in.
PRAGMA foreign_keys = OFF;

CREATE TABLE unit_detail_new (
  slug           TEXT PRIMARY KEY NOT NULL,
  title_arabic   TEXT,
  title_language TEXT
    CHECK (title_language IS NULL OR title_language IN ('ar', 'ur', 'zh')),
  study_track    TEXT
    CHECK (study_track IS NULL OR study_track IN
      ('theology', 'history', 'shariah', 'esoteric', 'reality', 'philosophy')),
  blurb_html     TEXT,
  edition_note   TEXT,
  cover_key      TEXT,
  pdf_key        TEXT,
  published_at   TEXT NOT NULL,
  source_commit  TEXT
);

INSERT INTO unit_detail_new
  (slug, title_arabic, title_language, study_track, blurb_html, edition_note,
   cover_key, pdf_key, published_at, source_commit)
SELECT
  slug, title_arabic, title_language, study_track, blurb_html, edition_note,
  cover_key, pdf_key, published_at, source_commit
FROM unit_detail;

DROP TABLE unit_detail;
ALTER TABLE unit_detail_new RENAME TO unit_detail;

PRAGMA foreign_keys = ON;
