-- 002_atom_relations.sql — Cross-book provenance and translation-variant tables.
-- Depends on: 001_atoms.sql (atoms table must exist first).

CREATE TABLE IF NOT EXISTS atoms_sources (
    atom_id    TEXT NOT NULL REFERENCES atoms (id) ON DELETE CASCADE,
    book_slug  TEXT NOT NULL,              -- FK → book_metadata.slug (advisory)
    chapter_id TEXT,
    locator    TEXT,                       -- heading or para# within chapter
    PRIMARY KEY (atom_id, book_slug, chapter_id)
);

CREATE INDEX IF NOT EXISTS idx_atoms_sources_book ON atoms_sources (book_slug);

CREATE TABLE IF NOT EXISTS atoms_variants (
    atom_id    TEXT NOT NULL REFERENCES atoms (id) ON DELETE CASCADE,
    book_slug  TEXT NOT NULL,              -- which book produced this translation
    text_en    TEXT NOT NULL,              -- English rendering used in that book
    translator TEXT,                       -- named translator or "AI-generated"
    PRIMARY KEY (atom_id, book_slug)
);

CREATE INDEX IF NOT EXISTS idx_atoms_variants_book ON atoms_variants (book_slug);
