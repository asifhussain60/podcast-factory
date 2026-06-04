-- 014_knowledge_base_meta.sql — Knowledge-base health and sync metadata.
-- Tracks import runs, dedup stats, and the current state of each JSONL source
-- file so incremental sync knows what has already been imported.
-- Depends on: nothing (standalone).

CREATE TABLE IF NOT EXISTS knowledge_base_meta (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT    NOT NULL UNIQUE,   -- e.g. "hadith.jsonl", "quran.jsonl"
    atom_type   TEXT    NOT NULL           -- "quran" | "hadith" | "doctrine"
                CHECK (atom_type IN ('quran', 'hadith', 'doctrine')),
    last_import TEXT,                      -- ISO-8601 datetime
    atoms_imported INTEGER NOT NULL DEFAULT 0,
    atoms_skipped  INTEGER NOT NULL DEFAULT 0,  -- duplicates / conflicts skipped
    checksum    TEXT                       -- SHA-256 of source file at last import
);

CREATE TABLE IF NOT EXISTS knowledge_base_conflicts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    atom_id     TEXT    NOT NULL,          -- conflicting atom ID
    source_file TEXT    NOT NULL,
    existing_body TEXT  NOT NULL,          -- JSON1 of the existing atom body
    incoming_body TEXT  NOT NULL,          -- JSON1 of the new candidate body
    detected_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    resolved_at TEXT,
    resolution  TEXT                       -- "kept_existing" | "replaced" | "merged"
);

CREATE INDEX IF NOT EXISTS idx_kb_conflicts_atom ON knowledge_base_conflicts (atom_id);
