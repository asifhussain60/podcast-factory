-- 023_atoms_add_quote_type.sql
-- Extend atoms.type CHECK constraint to include 'quote' for Wave K.
--   quote — attributed saying from a named speaker (scholar, imam, companion, prophet)
--           extracted from book chapters or Kashkole doctrine atoms.
-- Uses the rename-copy-drop pattern (SQLite cannot ALTER a CHECK constraint).
-- Idempotent: tracked by schema_migrations (runs exactly once).

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS atoms_v23 (
    id               TEXT    PRIMARY KEY,
    type             TEXT    NOT NULL
                     CHECK  (type IN (
                         'quran', 'hadith', 'term', 'citation',
                         'doctrine', 'etymology', 'poetry', 'quote'
                     )),
    body             TEXT    NOT NULL,
    first_seen_book  TEXT,
    first_seen_chapter TEXT,
    first_seen_date  TEXT,
    confidence       REAL    NOT NULL DEFAULT 1.0
                     CHECK  (confidence >= 0.0 AND confidence <= 1.0),
    tradition        TEXT    NOT NULL DEFAULT 'universal',
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

INSERT OR IGNORE INTO atoms_v23
    (id, type, body, first_seen_book, first_seen_chapter, first_seen_date,
     confidence, tradition, created_at, updated_at)
SELECT
    id, type, body, first_seen_book, first_seen_chapter, first_seen_date,
    confidence, tradition, created_at, updated_at
FROM atoms;

DROP TABLE atoms;
ALTER TABLE atoms_v23 RENAME TO atoms;

CREATE INDEX IF NOT EXISTS idx_atoms_type            ON atoms (type);
CREATE INDEX IF NOT EXISTS idx_atoms_first_seen_book ON atoms (first_seen_book);
CREATE INDEX IF NOT EXISTS idx_atoms_tradition       ON atoms (tradition);

COMMIT;
