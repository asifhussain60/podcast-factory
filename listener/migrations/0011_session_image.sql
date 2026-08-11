-- Illustrations that belong to a lecture, not to a book.
--
-- The Sessions collection is Asif's own delivered lectures, and their reading
-- text is the transcript he hand-marked in the KSESSIONS admin years ago. That
-- markup carries images — diagrams, scans, screenshots he put on the screen
-- while teaching — referenced as `Resources/IMAGES/<session>/<guid>.jpg`. They
-- are content, not decoration: several chapters make no sense without the thing
-- being pointed at.
--
-- WHY A NEW KIND RATHER THAN 'cover'. `media_asset.kind` is what the uploader
-- and the site both read to decide what a file IS — 'audio' is playable, 'pdf'
-- is downloadable, 'deck-page' is one leaf of a slide deck, 'cover' is the one
-- image standing for a whole work. A chapter illustration is none of those, and
-- filing it under 'cover' would mean a book with forty covers and the site
-- picking one of them arbitrarily to print on the card.
--
-- WHY THE CHECK IS WIDENED RATHER THAN DROPPED. Exactly the argument 0008 made
-- when it added 'transcript': the constraint is what stops a typo in the
-- publisher from inventing a kind that the uploader then never uploads and the
-- site never renders — a failure with no error anywhere, only a missing file. So
-- the closed list stays closed and gains one member.
--
-- WHY A TABLE REBUILD. SQLite cannot alter a CHECK in place. This is the
-- documented twelve-step ALTER in the order that keeps it safe, copied from
-- 0008 deliberately rather than improved: the two migrations do the same thing
-- to the same table and a reader comparing them should find them identical.
--
-- `uploaded_at` is carried across, and that is the whole reason this is a copy
-- rather than a DROP and re-create. It is the ONLY record that an object is
-- actually in R2. Losing it would make every page report the entire media
-- library as not-yet-uploaded, and the next uploader run would push several
-- gigabytes of unchanged audio again.
--
-- Carries no privilege bit, like every migration since 0004. Session images are
-- gated by their SLUG through `requireUnitAccess` on the media route, which is
-- the same gate the audio and the deck pages already run and is unchanged here.
CREATE TABLE media_asset_new (
  key          TEXT PRIMARY KEY NOT NULL,
  slug         TEXT NOT NULL,
  kind         TEXT NOT NULL CHECK (
    kind IN ('audio', 'transcript', 'pdf', 'cover', 'deck-page', 'session-image')
  ),
  content_type TEXT NOT NULL,
  bytes        INTEGER NOT NULL,
  sha256       TEXT NOT NULL,
  source_path  TEXT NOT NULL,
  uploaded_at  TEXT,
  -- Added by 0010. Repeated here because a rebuild re-declares the whole table,
  -- and a column omitted from this list is a column silently dropped.
  deck_id      TEXT,
  deck_title   TEXT
);

INSERT INTO media_asset_new (
  key, slug, kind, content_type, bytes, sha256, source_path, uploaded_at, deck_id, deck_title
)
  SELECT key, slug, kind, content_type, bytes, sha256, source_path, uploaded_at, deck_id, deck_title
  FROM media_asset;

DROP TABLE media_asset;
ALTER TABLE media_asset_new RENAME TO media_asset;

-- Both indexes went with the old table and have to be recreated by name: the
-- one 0004 created, and the one 0010 added for the per-chapter decks.
CREATE INDEX idx_media_asset_unit ON media_asset (slug, kind);
CREATE INDEX idx_media_asset_deck ON media_asset (slug, kind, deck_id);
