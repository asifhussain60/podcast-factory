-- Corrections: what a moderator says is wrong with a book, awaiting an admin's decision.
--
-- The Library CAPTURES corrections; it never applies them. Chapter prose is rendered ONCE,
-- at publish time, from `book/book.md`, and the Book Composer is the only path by which that
-- prose changes — so a correction that is accepted here is applied later, in the repo,
-- through that path, and comes back to the Library on the next publish. Writing corrected
-- text into `chapter` directly would let the web reader and the printed PDF disagree, and
-- the next publish would overwrite it without a word.
--
-- A CORRECTION IS SHARED, NOT PRIVATE. This is the ONE table in the reader schema that is
-- deliberately not keyed on the person: `bookmark` and `annotation` filter every read and
-- every write on `user_email` (a live hole until 2026-08-04, pinned by marks-isolation), and
-- a correction is the opposite — every moderator and admin sees every correction on a book.
-- Do NOT "fix" the missing per-user filter; test/corrections.test.ts pins it.
-- Who may CHANGE one is a separate question, answered in corrections.server.ts `authority`.
CREATE TABLE correction (
  id             TEXT PRIMARY KEY NOT NULL,
  slug           TEXT NOT NULL,
  anchor_key     TEXT NOT NULL,
  block_index    INTEGER NOT NULL,
  start_offset   INTEGER NOT NULL,
  end_offset     INTEGER NOT NULL CHECK (end_offset > start_offset),
  quote          TEXT NOT NULL,
  prefix         TEXT NOT NULL DEFAULT '',
  proposed_text  TEXT NOT NULL,
  -- Sanitised on WRITE by the same seven-tag allowlist a reader's note uses. It is rendered
  -- to an admin, so stored markup from a lower-privileged account is never trusted.
  rationale_html TEXT NOT NULL DEFAULT '',
  kind           TEXT NOT NULL CHECK (kind IN
                   ('typo', 'arabic', 'meaning', 'citation', 'formatting', 'other')),
  status         TEXT NOT NULL DEFAULT 'open' CHECK (status IN
                   ('open', 'accepted', 'applied', 'dismissed')),
  raised_by      TEXT NOT NULL COLLATE NOCASE,
  raised_at      TEXT NOT NULL,
  -- The optimistic-concurrency token. An admin's accept carries the value they SAW; if the
  -- proposal changed in between, the accept is refused, so what ships is what was read.
  updated_at     TEXT NOT NULL,
  decided_by     TEXT COLLATE NOCASE,
  decided_at     TEXT,
  decision_note  TEXT,
  applied_at     TEXT,
  -- Soft delete, like every other removal in this database.
  deleted_at     TEXT,
  deleted_by     TEXT COLLATE NOCASE
);

CREATE INDEX idx_correction_book ON correction (slug, status) WHERE deleted_at IS NULL;
