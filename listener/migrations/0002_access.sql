-- Who may sign in, what content exists, and who may see which of it.
--
-- Every email column stores the NORMALIZED form produced by
-- app/server/email.server.ts. Nothing writes a raw address to a key column.

-- ---------------------------------------------------------------------------
-- invite — the gate on signing in at all
-- ---------------------------------------------------------------------------
-- Soft revocation, because re-inviting someone must restore what they had.
-- Revoking sets revoked_at AND deletes that user's session rows AND deliberately
-- LEAVES their grants alone.
CREATE TABLE invite (
  email       TEXT PRIMARY KEY NOT NULL COLLATE NOCASE
              CHECK (email = lower(email) AND email LIKE '%_@_%._%'),
  email_raw   TEXT NOT NULL,          -- as typed, for display only. Never compared.
  invited_by  TEXT NOT NULL,
  invited_at  TEXT NOT NULL,
  redeemed_at TEXT,
  revoked_at  TEXT,
  note        TEXT
);

CREATE INDEX idx_invite_live ON invite (email) WHERE revoked_at IS NULL;

-- ---------------------------------------------------------------------------
-- content_unit — what there is to grant
-- ---------------------------------------------------------------------------
-- `slug` is the same collision-free key the pipeline already produces: flat for
-- a standalone book, composite `<work_slug>-vol-NN` for a volume. A six-volume
-- work has SEVEN rows — one per volume plus one `kind='work'` parent — so a
-- grant on the parent covers volumes added later without revisiting anybody's
-- permissions.
--
-- `open_to_all` and `status` are PRIVILEGE BITS. Only an admin session writes
-- them. The phase-3 publish endpoint names its columns explicitly and must never
-- include either — there is a test that greps for exactly that.
CREATE TABLE content_unit (
  slug        TEXT PRIMARY KEY NOT NULL,
  bucket      TEXT NOT NULL,
  title       TEXT NOT NULL,
  kind        TEXT NOT NULL CHECK (kind IN ('book', 'work')),
  work_slug   TEXT,                   -- set on volumes; NULL on standalone books and work parents
  sort_order  INTEGER NOT NULL DEFAULT 0,
  status      TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
  open_to_all INTEGER NOT NULL DEFAULT 0 CHECK (open_to_all IN (0, 1))
);

CREATE INDEX idx_content_unit_work ON content_unit (work_slug);
CREATE INDEX idx_content_unit_visible ON content_unit (status, open_to_all);

-- ---------------------------------------------------------------------------
-- access_grant — current state only
-- ---------------------------------------------------------------------------
-- Keyed on EMAIL, not user id, so access can be provisioned before someone has
-- ever signed in — at which point no user row exists to point at.
--
-- scope_id is NOT NULL and 'library' is spelled '*' rather than NULL for a
-- specific reason: SQLite does not enforce NOT NULL on PRIMARY KEY columns on a
-- rowid table, and its unique index treats NULLs as distinct. A nullable
-- scope_id would let two ('x@y.com','library',NULL) rows coexist, so revoking
-- one would silently leave the other live.
--
-- Re-granting is always an UPSERT clearing revoked_at — a plain INSERT on a
-- previously revoked row violates the primary key. History lives in
-- access_event; this table is never asked to be both current state and audit log.
CREATE TABLE access_grant (
  user_email TEXT NOT NULL COLLATE NOCASE,
  scope_type TEXT NOT NULL CHECK (scope_type IN ('unit', 'work', 'library')),
  scope_id   TEXT NOT NULL CHECK (scope_type <> 'library' OR scope_id = '*'),
  granted_by TEXT NOT NULL,
  granted_at TEXT NOT NULL,
  revoked_at TEXT,
  PRIMARY KEY (user_email, scope_type, scope_id)
);

CREATE INDEX idx_access_grant_live ON access_grant (user_email) WHERE revoked_at IS NULL;

-- ---------------------------------------------------------------------------
-- access_event — append-only audit
-- ---------------------------------------------------------------------------
CREATE TABLE access_event (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  at         TEXT NOT NULL,
  actor      TEXT NOT NULL,
  action     TEXT NOT NULL,
  subject    TEXT NOT NULL,           -- the email or slug acted upon
  scope_type TEXT,
  scope_id   TEXT,
  detail     TEXT
);

CREATE INDEX idx_access_event_subject ON access_event (subject, at);

-- ---------------------------------------------------------------------------
-- The admin address cannot be squatted
-- ---------------------------------------------------------------------------
-- Admin is `normalizeEmail(session.user.email) === normalizeEmail(ADMIN_EMAIL)`
-- and there is no role column, so no row write grants admin. But that makes
-- `user.email` itself the privilege bit, and it is a mutable column. Better Auth's
-- changeEmail is disabled in app/server/auth.server.ts and a test asserts it —
-- these triggers make the claim structural rather than merely configured.
--
-- The address is inlined because SQLite triggers cannot read Worker vars. It must
-- match ADMIN_EMAIL in wrangler.jsonc; the seed migration asserts the pairing.
CREATE TRIGGER no_admin_email_squat_update
BEFORE UPDATE OF email ON user
WHEN NEW.email = 'asifhussain60@gmail.com' AND OLD.email <> 'asifhussain60@gmail.com'
BEGIN
  SELECT RAISE(ABORT, 'refusing to move an existing account onto the admin address');
END;

-- Also guard emailVerified, which the admin check reads: flipping it on a row
-- that already holds the admin address would be the same escalation by another
-- route.
CREATE TRIGGER no_admin_verify_flip
BEFORE UPDATE OF emailVerified ON user
WHEN NEW.email = 'asifhussain60@gmail.com' AND OLD.emailVerified = 0 AND NEW.emailVerified = 1
     AND OLD.email <> NEW.email
BEGIN
  SELECT RAISE(ABORT, 'refusing to verify the admin address on a renamed row');
END;
