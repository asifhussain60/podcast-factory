-- 017_atoms_add_doctrine_type.sql
-- Extend atoms.type CHECK constraint to include 'doctrine' for Kashkole corpus
-- atoms (B0 ingestion driver). SQLite does not support ALTER TABLE MODIFY
-- COLUMN, so we use the standard rename-copy-drop-rename pattern.
-- Idempotent: tracked by schema_migrations (runs exactly once).
-- Safe: DB is expected to have zero atom rows at this point (no pipeline books
-- processed yet). The INSERT…SELECT copies any existing rows just in case.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS atoms_v17 (
    id               TEXT    PRIMARY KEY,
    type             TEXT    NOT NULL
                     CHECK  (type IN ('quran', 'hadith', 'term', 'citation', 'doctrine')),
    body             TEXT    NOT NULL,
    first_seen_book  TEXT,
    first_seen_chapter TEXT,
    first_seen_date  TEXT,
    confidence       REAL    NOT NULL DEFAULT 1.0
                     CHECK  (confidence >= 0.0 AND confidence <= 1.0),
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Copy any existing rows (preserves quran/hadith atoms loaded before this migration)
INSERT OR IGNORE INTO atoms_v17 SELECT * FROM atoms;

DROP TABLE atoms;
ALTER TABLE atoms_v17 RENAME TO atoms;

CREATE INDEX IF NOT EXISTS idx_atoms_type           ON atoms (type);
CREATE INDEX IF NOT EXISTS idx_atoms_first_seen_book ON atoms (first_seen_book);

COMMIT;
