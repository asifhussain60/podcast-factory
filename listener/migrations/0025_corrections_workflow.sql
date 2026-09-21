-- The rest of the corrections workflow: suggestions, AI review, chapter review, and the record
-- that lets a reader's marks survive a correction being applied.

-- ---------------------------------------------------------------------------
-- 1. `correction` gains a `suggested` status and where a row came from.
--
-- SQLite cannot alter a CHECK constraint, so the table is rebuilt. Safe here: 0023 has run on no
-- database but a developer's local one, and every existing row is copied across.
--
-- A SUGGESTION is a correction the pipeline found before any person looked (an unresolved
-- flag from an audit). A moderator confirms it (-> 'open') or dismisses it, so people confirm
-- errors instead of hunting for them. `origin` says which kind a row is; `certainty` carries
-- the audit's own confidence so the queue can be sorted by it.
-- ---------------------------------------------------------------------------
CREATE TABLE correction_new (
  id             TEXT PRIMARY KEY NOT NULL,
  slug           TEXT NOT NULL,
  anchor_key     TEXT NOT NULL,
  block_index    INTEGER NOT NULL,
  start_offset   INTEGER NOT NULL,
  end_offset     INTEGER NOT NULL CHECK (end_offset > start_offset),
  quote          TEXT NOT NULL,
  prefix         TEXT NOT NULL DEFAULT '',
  proposed_text  TEXT NOT NULL,
  rationale_html TEXT NOT NULL DEFAULT '',
  kind           TEXT NOT NULL CHECK (kind IN
                   ('typo', 'arabic', 'meaning', 'citation', 'formatting', 'other')),
  status         TEXT NOT NULL DEFAULT 'open' CHECK (status IN
                   ('suggested', 'open', 'accepted', 'applied', 'dismissed')),
  origin         TEXT NOT NULL DEFAULT 'moderator' CHECK (origin IN ('moderator', 'sweep')),
  certainty      INTEGER,
  -- One id shared by every correction raised together by "fix everywhere", so they are
  -- reviewed and decided as a batch.
  batch_id       TEXT,
  raised_by      TEXT NOT NULL COLLATE NOCASE,
  raised_at      TEXT NOT NULL,
  updated_at     TEXT NOT NULL,
  decided_by     TEXT COLLATE NOCASE,
  decided_at     TEXT,
  decision_note  TEXT,
  applied_at     TEXT,
  deleted_at     TEXT,
  deleted_by     TEXT COLLATE NOCASE
);

INSERT INTO correction_new
  (id, slug, anchor_key, block_index, start_offset, end_offset, quote, prefix, proposed_text,
   rationale_html, kind, status, raised_by, raised_at, updated_at, decided_by, decided_at,
   decision_note, applied_at, deleted_at, deleted_by)
SELECT id, slug, anchor_key, block_index, start_offset, end_offset, quote, prefix, proposed_text,
       rationale_html, kind, status, raised_by, raised_at, updated_at, decided_by, decided_at,
       decision_note, applied_at, deleted_at, deleted_by
  FROM correction;

DROP TABLE correction;
ALTER TABLE correction_new RENAME TO correction;
CREATE INDEX idx_correction_book ON correction (slug, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_correction_batch ON correction (batch_id) WHERE batch_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 2. AI review. WRITTEN ONLY by the repo-side reviewer over `wrangler d1 execute`; no HTTP route
-- writes it, so no account — admin included — can forge an AI opinion from a browser.
--
-- Keyed on the correction's `updated_at` AT REVIEW TIME. The panel reads a row only when it
-- matches the correction's current `updated_at`, so a proposal edited after review shows NO
-- stale verdict. History is kept.
-- ---------------------------------------------------------------------------
CREATE TABLE correction_review (
  correction_id      TEXT NOT NULL,
  correction_updated TEXT NOT NULL,
  verdict            TEXT NOT NULL CHECK (verdict IN ('supports', 'revise', 'reject', 'needs_human')),
  confidence         TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
  summary            TEXT NOT NULL,
  suggested_text     TEXT,
  -- Evidence, ripples and the individual checks, as JSON. Rendered by the client through
  -- React (escaped), never as HTML.
  detail_json        TEXT NOT NULL DEFAULT '{}',
  source_kind        TEXT NOT NULL DEFAULT 'none' CHECK (source_kind IN ('scan', 'extracted', 'none')),
  model              TEXT NOT NULL,
  reviewed_at        TEXT NOT NULL,
  PRIMARY KEY (correction_id, correction_updated)
);

-- ---------------------------------------------------------------------------
-- 3. Chapter review: "I have read this chapter against the source". Without it a book with no
-- corrections is indistinguishable from a book nobody read, and there is no honest way to say
-- a book is ready to come out of moderation.
-- ---------------------------------------------------------------------------
CREATE TABLE chapter_review (
  slug        TEXT NOT NULL,
  anchor_key  TEXT NOT NULL,
  claimed_by  TEXT COLLATE NOCASE,
  claimed_at  TEXT,
  reviewed_by TEXT COLLATE NOCASE,
  reviewed_at TEXT,
  PRIMARY KEY (slug, anchor_key)
);

-- ---------------------------------------------------------------------------
-- 4. What an APPLIED correction changed, so a reader's own highlights and a Companion card
-- that quoted the OLD wording still find the passage. The reader locates a mark by its quote;
-- fix the sentence and every mark on it would otherwise fall into the "orphaned" list. Only an
-- EXACT recorded substitution is ever followed — never a guess.
--
-- Written by the repo-side apply step; read (never written) by the Worker.
-- ---------------------------------------------------------------------------
CREATE TABLE correction_applied (
  slug       TEXT NOT NULL,
  anchor_key TEXT NOT NULL,
  old_text   TEXT NOT NULL,
  new_text   TEXT NOT NULL,
  applied_at TEXT NOT NULL,
  PRIMARY KEY (slug, anchor_key, old_text)
);
