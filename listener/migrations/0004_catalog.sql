-- Phase 3 — what a content unit actually CONTAINS.
--
-- Everything here is written by the publish step
-- (scripts/podcast/publish_to_listener.py) and read by the reading and listening
-- surfaces. Two rules shape the whole schema:
--
--   1. NOTHING here is a privilege bit. `content_unit.status` and
--      `content_unit.open_to_all` stay the admin session's alone; the publish
--      step names its columns explicitly and never touches those two. A book can
--      be fully published into these tables and still be invisible to everyone,
--      which is the safe direction.
--
--   2. Absence is normal. Most books have no audio, most have no deck, some have
--      no PDF. Every media reference is therefore nullable and every list is
--      allowed to come back empty. A book missing three of four things is a
--      NORMAL book, not a broken one, and no query here treats it as an error.

-- ---------------------------------------------------------------------------
-- unit_detail — the presentation layer of a unit
-- ---------------------------------------------------------------------------
-- Separate from content_unit on purpose: content_unit is the ACCESS record and
-- is written by the seed and the admin screens, while this is written by the
-- publish step on every re-publish. Keeping them apart means a re-publish can
-- DELETE and rewrite its own row without ever going near a grantable column.
CREATE TABLE unit_detail (
  slug           TEXT PRIMARY KEY NOT NULL,
  title_arabic   TEXT,                  -- as it appears in meta.yml; may be absent
  -- The opening of the edition introduction, RENDERED. It is markdown on disk
  -- and carries italics, inline Arabic and scholarly transliteration, so storing
  -- the raw text put `*Kitab al-Alim*` on the page with its asterisks showing.
  -- Rendered through the same function as the chapters, which also folds the
  -- diacritics to the plain romanization the house style uses.
  blurb_html     TEXT,
  edition_note   TEXT,                  -- e.g. "translation edition", "augmented companion"
  cover_key      TEXT,                  -- media_asset.key, NULL until a cover is published
  pdf_key        TEXT,                  -- media_asset.key of the print edition, NULL if none
  published_at   TEXT NOT NULL,
  source_commit  TEXT                   -- the repo commit the publish ran from, for tracing
);

-- ---------------------------------------------------------------------------
-- chapter — the reading edition
-- ---------------------------------------------------------------------------
-- Keyed by `anchor_key`, NOT by position. That is the same key
-- `_book_edits.anchor_key` produces from a heading, and it is what lets a
-- re-publish after a re-compose land a chapter on the row it already had even
-- when a chapter was inserted above it. Position is `idx`, which is display
-- order only and is expected to change.
--
-- `html` is rendered ONCE, at publish time, by plan-dashboard's renderMarkdown —
-- the same function the print edition goes through — so the on-screen reader and
-- the PDF cannot diverge. It is stored rather than rendered per request because
-- the alternative is shipping a markdown parser into the Worker and hoping the
-- two agree.
CREATE TABLE chapter (
  slug        TEXT NOT NULL,
  anchor_key  TEXT NOT NULL,
  idx         INTEGER NOT NULL,
  title       TEXT NOT NULL,
  html        TEXT NOT NULL,
  word_count  INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (slug, anchor_key)
);

CREATE INDEX idx_chapter_order ON chapter (slug, idx);

-- ---------------------------------------------------------------------------
-- episode — the podcast
-- ---------------------------------------------------------------------------
-- Episodes are NOT chapters and do not map 1:1 to them: the reading edition and
-- the podcast are drawn along different lines from the same source. Both are
-- first-class here, and neither is derived from the other.
--
-- `audio_key` is NULL when an episode has been planned and framed but its audio
-- has not been produced — the ordinary state for most of the library. The UI
-- shows the episode and says there is no audio yet; it does not hide it, because
-- hiding it would misreport the shape of the book.
CREATE TABLE episode (
  slug        TEXT NOT NULL,
  number      INTEGER NOT NULL,
  title       TEXT NOT NULL,
  blurb       TEXT,
  style       TEXT,                     -- 'deep_dive' | 'debate' | whatever the contract declares
  audio_key   TEXT,                     -- media_asset.key, NULL until audio exists
  duration_s  INTEGER,                  -- NULL until known
  PRIMARY KEY (slug, number)
);

-- ---------------------------------------------------------------------------
-- episode_chapter — the bridge, populated only where it is KNOWN
-- ---------------------------------------------------------------------------
-- "I finished episode 3, where do I read that?" needs an answer, and a wrong
-- answer is worse than none on a religious text. The pipeline does not currently
-- record this: a chapter contract's `source_chapter_ref` points into the SOURCE
-- book's chapter numbering, which is a different segmentation again from the
-- reading edition's. So this table is filled ONLY from an explicit, hand-written
-- `_system/listener-episode-chapters.json`, and is empty for every book that has
-- no such file. The book page then shows chapters and episodes as two honest
-- views of one work and offers no cross-link it cannot stand behind.
CREATE TABLE episode_chapter (
  slug       TEXT NOT NULL,
  number     INTEGER NOT NULL,
  anchor_key TEXT NOT NULL,
  PRIMARY KEY (slug, number, anchor_key)
);

-- ---------------------------------------------------------------------------
-- media_asset — one row per object in R2
-- ---------------------------------------------------------------------------
-- The row exists as soon as the file exists ON DISK, whether or not it has been
-- uploaded; `uploaded_at` is what distinguishes the two. That ordering is
-- deliberate — R2 is not enabled on the account yet, so today every row is
-- unuploaded, and the site reports "no audio yet" rather than offering a link
-- that 404s.
--
-- `key` doubles as the R2 object key and BEGINS with the slug, so /media/:key
-- can resolve the owning unit and run the same canRead check the page did. There
-- is no signed-URL scheme and no second authorisation path.
CREATE TABLE media_asset (
  key          TEXT PRIMARY KEY NOT NULL,
  slug         TEXT NOT NULL,
  kind         TEXT NOT NULL CHECK (kind IN ('audio', 'pdf', 'cover', 'deck-page')),
  content_type TEXT NOT NULL,
  bytes        INTEGER NOT NULL,
  sha256       TEXT NOT NULL,
  source_path  TEXT NOT NULL,           -- where it came from on disk, for re-upload
  uploaded_at  TEXT                     -- NULL means the object is not in R2 yet
);

CREATE INDEX idx_media_asset_unit ON media_asset (slug, kind);
