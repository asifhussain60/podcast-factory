-- 026_atoms_update_content_level_ladder.sql — Update content_level CHECK to 6-level
-- Kashkole ladder (Wave M).
--
-- Migration 025 added content_level with a 4-level CHECK constraint:
--   ('history', 'shariah', 'esoteric', 'realities', 'universal')
--
-- Wave M expands the ladder to 6 levels sourced from Kashkole dbo.Lookup_levels:
--   general → advanced → taveel → mamsool → mabda_maad → haqaiq
--   plus 'universal' (always outside the ladder, eligible at every level)
--
-- SQLite does not support ALTER COLUMN to change a CHECK constraint in place.
-- This migration uses the rename-copy-drop pattern with foreign_keys OFF to
-- prevent the atom_topic_tags CASCADE from wiping child rows (see migration 024).
--
-- PATTERN (mandatory per migration 024 guard note):
--   PRAGMA foreign_keys = OFF  before BEGIN
--   PRAGMA foreign_keys = ON   after COMMIT

PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

CREATE TABLE atoms_new (
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
    updated_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    content_level    TEXT
                     CHECK  (content_level IN (
                         'general', 'advanced', 'taveel', 'mamsool',
                         'mabda_maad', 'haqaiq', 'universal'
                     ))
);

-- Defensive data migration: map any atoms still carrying old 4-level values to
-- their nearest new-ladder equivalents before copying into the constrained table.
-- These are no-ops on the production DB (no such rows exist there) but prevent
-- a constraint-violation failure if this migration is ever run on a DB that was
-- migrated through 025 before atoms were recategorised.
UPDATE atoms SET content_level = 'general'  WHERE content_level = 'history';
UPDATE atoms SET content_level = 'advanced' WHERE content_level = 'shariah';
UPDATE atoms SET content_level = 'taveel'   WHERE content_level = 'esoteric';
UPDATE atoms SET content_level = 'haqaiq'   WHERE content_level = 'realities';

INSERT INTO atoms_new SELECT * FROM atoms;

DROP TABLE atoms;

ALTER TABLE atoms_new RENAME TO atoms;

-- Recreate indexes dropped with the old atoms table.
CREATE INDEX IF NOT EXISTS idx_atoms_type           ON atoms (type);
CREATE INDEX IF NOT EXISTS idx_atoms_tradition      ON atoms (tradition);
CREATE INDEX IF NOT EXISTS idx_atoms_first_seen_book ON atoms (first_seen_book);
CREATE INDEX IF NOT EXISTS idx_atoms_content_level  ON atoms (content_level);

COMMIT;

PRAGMA foreign_keys = ON;
