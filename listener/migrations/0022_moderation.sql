-- Moderators, and books held back while they are being corrected.
--
-- A MODERATOR is a person who may see books that are Under Moderation and (in a later
-- change) propose corrections to them. It is strictly LOWER than admin and strictly
-- ADDITIVE: admin is still `ADMIN_EMAIL` and nothing else, there is still no role column,
-- and admin always counts as a moderator without needing a row here.
--
-- Keyed on the NORMALIZED email like `access_grant`, so somebody can be made a moderator
-- before they have ever signed in. Revoked, never deleted; the audit trail is
-- `access_event`, written in the same batch as every change to this table.
CREATE TABLE moderator (
  user_email TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
  granted_by TEXT NOT NULL,
  granted_at TEXT NOT NULL,
  revoked_at TEXT
);

-- Under moderation is a FLAG, not a fourth `status` value. `status` describes the book's
-- publication and `VISIBLE_SQL` already keys on it; folding a moderation state into that
-- column would have meant relaxing the one entitlement expression for every caller. A
-- separate column lets the expression grow one explicit, testable branch instead.
--
-- Written ONLY from the admin content screen. `publish_to_listener.py` never names it, for
-- the same reason it never names `status` or `open_to_all`: it runs unattended, and a
-- privilege bit set by an unattended script is one nobody decided.
ALTER TABLE content_unit ADD COLUMN under_moderation INTEGER NOT NULL DEFAULT 0
  CHECK (under_moderation IN (0, 1));
