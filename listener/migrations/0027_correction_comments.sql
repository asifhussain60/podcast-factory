-- Comments on a correction. Any moderator or admin may comment on ANY correction — that is how
-- moderators discuss each other's work without being able to change it. A comment is its author's
-- own: only they (or an admin) can remove it. Soft-deleted, like everything else that goes away.
--
-- SHARED between moderators exactly like `correction` itself, and for the same reason it carries
-- no per-user read filter. Plain text only — never markup — so nothing stored here is rendered as
-- HTML to a higher-privileged account.
CREATE TABLE correction_comment (
  id            TEXT PRIMARY KEY NOT NULL,
  correction_id TEXT NOT NULL,
  slug          TEXT NOT NULL,
  author        TEXT NOT NULL COLLATE NOCASE,
  body          TEXT NOT NULL,
  created_at    TEXT NOT NULL,
  deleted_at    TEXT,
  deleted_by    TEXT COLLATE NOCASE
);

CREATE INDEX idx_correction_comment_live ON correction_comment (correction_id) WHERE deleted_at IS NULL;
