-- Widen study_track to the five real categories (theology, history, shariah,
-- esoteric, reality) and rename 'esoterics' -> 'esoteric', the only value
-- 0016 ever allowed anyone to write. SQLite cannot ALTER a CHECK constraint
-- in place, so the table is rebuilt: new shape, copy across, swap in.
PRAGMA foreign_keys = OFF;

CREATE TABLE unit_detail_new (
  slug           TEXT PRIMARY KEY NOT NULL,
  title_arabic   TEXT,
  title_language TEXT
    CHECK (title_language IS NULL OR title_language IN ('ar', 'ur', 'zh')),
  study_track    TEXT
    CHECK (study_track IS NULL OR study_track IN
      ('theology', 'history', 'shariah', 'esoteric', 'reality')),
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
  slug, title_arabic, title_language,
  CASE WHEN study_track = 'esoterics' THEN 'esoteric' ELSE study_track END,
  blurb_html, edition_note, cover_key, pdf_key, published_at, source_commit
FROM unit_detail;

DROP TABLE unit_detail;
ALTER TABLE unit_detail_new RENAME TO unit_detail;

PRAGMA foreign_keys = ON;
