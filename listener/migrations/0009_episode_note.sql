-- episode_note — a moment in a recording, and what the listener wanted to say
-- ---------------------------------------------------------------------------
-- A TABLE OF ITS OWN rather than nullable columns on `annotation`, and the
-- reason is the one `annotation` is built around: every field it has locates
-- TEXT — the paragraph, the character offsets, the quote that lets a highlight
-- survive a re-compose. An audio mark locates a moment. Bolting a second, unused
-- anchor onto that table would mean every read which paints a chapter has to
-- remember to exclude these rows, and the first read that forgets paints a
-- listening note into the middle of a chapter.
--
-- Same discipline as the marks in 0006, deliberately repeated rather than
-- inherited:
--
--   * `id` is CLIENT-GENERATED, so a note made with no signal has an identity
--     before the server has seen it. It is validated for shape, and every
--     mutation is scoped to `user_email` — including the upsert, which is where
--     that guard was missing on `bookmark` and `annotation` and let one reader
--     rewrite another's note. It is present here from the first line.
--   * writes are UPSERT or soft-delete, never a bare INSERT and never a DELETE,
--     because the client replays its outbox and may replay it twice.
--   * `(slug, number)` is the episode's identity — the same key the listening
--     position and the audio asset use — so a note survives a recording being
--     re-exported under a new filename.
--
-- `seconds` is stored as TAPPED, not as played back. The reader always taps
-- LATE — the thing strikes them, then they reach for the phone — so the site
-- plays from a few seconds earlier. Storing the adjusted value would bake one
-- reading of that into the record and make it un-revisable; the fact is when the
-- button was pressed, and the pre-roll is an interpretation applied at the edge.
--
-- `note` is nullable because the one-tap case is the point: mark the moment now,
-- say why later. A row with no words is a bookmark in time and is complete.
CREATE TABLE episode_note (
  id         TEXT PRIMARY KEY NOT NULL,
  user_email TEXT NOT NULL COLLATE NOCASE,
  slug       TEXT NOT NULL,
  number     INTEGER NOT NULL,
  seconds    INTEGER NOT NULL CHECK (seconds >= 0),
  note       TEXT,
  -- The transcript line as it read when the note was made, when the note was
  -- made against one. A copy, on purpose: it is what the listener saw, and a
  -- re-transcription changes the words in the file. The same argument the
  -- annotation's `quote` is stored under.
  quote      TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deleted_at TEXT
);

-- Every read is "this person, this book", and the partial index matches the
-- WHERE those reads carry rather than being a general index that mostly scans
-- deleted rows — the same shape as idx_annotation_live.
CREATE INDEX idx_episode_note_live ON episode_note (user_email, slug) WHERE deleted_at IS NULL;
