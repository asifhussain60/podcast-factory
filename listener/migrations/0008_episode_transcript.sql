-- The timed transcript of an episode.
--
-- A COLUMN on `episode`, not a table of its own, and the contrast with
-- `companion_note` in 0007 is the reason worth writing down. That one is a table
-- because it must never be readable by the wrong person, so it is kept out of
-- reach of any query that was not written for it. A transcript is the opposite:
-- it is the episode's own words, readable by exactly whoever may play the
-- episode, and it travels with the episode row on every read. Nothing is gained
-- by making it a second query, and a nullable key beside `audio_key` says the
-- true thing — that an episode may have audio and no transcript, or neither.
--
-- It holds a `media_asset.key`, exactly as `audio_key` does, which means:
--
--   * the file is served by /media/:key and therefore runs the SAME access check
--     the audio and the page ran — no new authorisation path, and none possible;
--   * a row here means the transcript exists on the author's disk, and only
--     `media_asset.uploaded_at` says it is in R2. The site offers the transcript
--     only on the second, the same rule the audio, the deck and the PDF follow.
--
-- The file itself is WebVTT — one cue per phrase, with the speaker where
-- diarization identified one. It is written by scripts/podcast/ensure_transcripts.py,
-- which runs inside the deploy so that a shipped episode without a transcript
-- cannot happen by forgetting.
ALTER TABLE episode ADD COLUMN transcript_key TEXT;

-- `media_asset.kind` is a CLOSED list, and a transcript is a new member of it.
--
-- The CHECK is worth keeping rather than dropping: it is what stops a typo in
-- the publisher from inventing a kind that the uploader and the site then
-- disagree about. But SQLite cannot alter a CHECK in place, so widening the list
-- means rebuilding the table — the documented twelve-step ALTER, in the order
-- that keeps it safe.
--
-- The copy carries `uploaded_at` across, which is the whole reason this is done
-- carefully rather than with a DROP: that column is the only record that an
-- object is actually in R2, and losing it would make the site report the entire
-- media library as missing and the uploader push several gigabytes again.
CREATE TABLE media_asset_new (
  key          TEXT PRIMARY KEY NOT NULL,
  slug         TEXT NOT NULL,
  kind         TEXT NOT NULL CHECK (kind IN ('audio', 'transcript', 'pdf', 'cover', 'deck-page')),
  content_type TEXT NOT NULL,
  bytes        INTEGER NOT NULL,
  sha256       TEXT NOT NULL,
  source_path  TEXT NOT NULL,
  uploaded_at  TEXT
);

INSERT INTO media_asset_new (key, slug, kind, content_type, bytes, sha256, source_path, uploaded_at)
  SELECT key, slug, kind, content_type, bytes, sha256, source_path, uploaded_at FROM media_asset;

DROP TABLE media_asset;
ALTER TABLE media_asset_new RENAME TO media_asset;

-- The index went with the old table and has to be recreated by name.
CREATE INDEX idx_media_asset_unit ON media_asset (slug, kind);
