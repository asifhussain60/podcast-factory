-- 011_external_corpora.sql — External reference corpora (e.g. Quran text, hadith collections).
-- These are read-only reference tables populated at DB init time, not pipeline time.
-- Depends on: nothing (standalone).

CREATE TABLE IF NOT EXISTS external_corpora (
    id           TEXT    PRIMARY KEY,   -- e.g. "quran", "bukhari", "muslim", "tirmidhi"
    display_name TEXT    NOT NULL,
    corpus_type  TEXT    NOT NULL       -- "quran" | "hadith" | "scholarly"
                 CHECK (corpus_type IN ('quran', 'hadith', 'scholarly')),
    atom_count   INTEGER NOT NULL DEFAULT 0,
    last_synced  TEXT                   -- ISO-8601 datetime of last import
);

CREATE TABLE IF NOT EXISTS corpus_chapters (
    id              TEXT    PRIMARY KEY,   -- e.g. "quran:2", "bukhari:book1"
    corpus_id       TEXT    NOT NULL REFERENCES external_corpora (id) ON DELETE CASCADE,
    number          INTEGER,              -- surah/book/chapter number
    title_en        TEXT,
    title_ar        TEXT,
    verse_count     INTEGER               -- null for hadith collections
);

CREATE INDEX IF NOT EXISTS idx_corpus_chapters_corpus ON corpus_chapters (corpus_id);
