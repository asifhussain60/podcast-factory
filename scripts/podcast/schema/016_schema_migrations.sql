-- 016_schema_migrations.sql — Migration tracking table.
-- Recorded after each SQL file is applied so run_migrations() is idempotent:
-- already-applied files are skipped on subsequent calls.
-- Depends on: nothing (must be applied last so all other tables exist first).

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    TEXT    PRIMARY KEY,               -- e.g. "001_atoms.sql"
    applied_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
