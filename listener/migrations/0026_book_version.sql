-- A fingerprint of each book's published prose, so a device that saved a chapter can tell it has
-- gone stale. Without it a reader who downloaded a book keeps the wording they downloaded forever
-- — a correction ships and some readers never see it.
--
-- Written by `publish_to_listener.py` (a hash of every chapter's rendered HTML, so it changes when
-- and only when the prose does), read by `/offline/allowed` and `/book/:slug/text`. It names no
-- privilege bit and decides nothing about who may read.
CREATE TABLE book_version (
  slug       TEXT PRIMARY KEY NOT NULL,
  version    TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
