-- Better Auth core schema.
--
-- NOT hand-authored: derived from `getAuthTables()` in the INSTALLED
-- @better-auth/core (better-auth 1.6.25), with the options this app actually
-- uses (Google social provider, email/password disabled). The `@better-auth/cli`
-- generator was not used because its latest stable is 1.4.21 — two minor
-- versions behind the library — and a generator that lags the adapter produces a
-- schema the adapter then fails against at runtime.
--
-- To regenerate after a better-auth upgrade, walk getAuthTables() again rather
-- than editing this by hand. Column names are camelCase because that is what the
-- adapter emits; do not "tidy" them to snake_case.

CREATE TABLE user (
  id            TEXT PRIMARY KEY NOT NULL,
  name          TEXT NOT NULL,
  email         TEXT NOT NULL UNIQUE,
  emailVerified INTEGER NOT NULL,
  image         TEXT,
  createdAt     TEXT NOT NULL,
  updatedAt     TEXT NOT NULL
);

CREATE TABLE session (
  id        TEXT PRIMARY KEY NOT NULL,
  expiresAt TEXT NOT NULL,
  token     TEXT NOT NULL UNIQUE,
  createdAt TEXT NOT NULL,
  updatedAt TEXT NOT NULL,
  ipAddress TEXT,
  userAgent TEXT,
  userId    TEXT NOT NULL,
  FOREIGN KEY (userId) REFERENCES user(id) ON DELETE CASCADE
);

CREATE TABLE account (
  id                    TEXT PRIMARY KEY NOT NULL,
  accountId             TEXT NOT NULL,
  providerId            TEXT NOT NULL,
  userId                TEXT NOT NULL,
  accessToken           TEXT,
  refreshToken          TEXT,
  idToken               TEXT,
  accessTokenExpiresAt  TEXT,
  refreshTokenExpiresAt TEXT,
  scope                 TEXT,
  password              TEXT,
  createdAt             TEXT NOT NULL,
  updatedAt             TEXT NOT NULL,
  FOREIGN KEY (userId) REFERENCES user(id) ON DELETE CASCADE
);

CREATE TABLE verification (
  id         TEXT PRIMARY KEY NOT NULL,
  identifier TEXT NOT NULL,
  value      TEXT NOT NULL,
  expiresAt  TEXT NOT NULL,
  createdAt  TEXT NOT NULL,
  updatedAt  TEXT NOT NULL
);

-- Every request resolves a session by token, and revoking an invite deletes a
-- user's sessions by userId. Both are hot enough to index.
CREATE INDEX idx_session_userId ON session (userId);
CREATE INDEX idx_account_userId ON account (userId);
CREATE INDEX idx_verification_identifier ON verification (identifier);
