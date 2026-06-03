-- 025_atoms_add_content_level.sql — Add content_level column to atoms (Wave L, L-1).
--
-- Enables content-level-aware augmentation for ISLAMIC scholarly books only.
-- A book declaring `content_level` in meta.yml draws doctrine atoms ONLY at or
-- below its own level (cumulative downward), never above:
--
--     history (1) < shariah (2) < esoteric (3) < realities (4)
--     universal — outside the ladder; always eligible
--
-- The 'universal' value is the eligible-at-every-level marker for atoms.
-- NULL = uncategorized: passes the gate during the categorization transition
-- (Wave L-3) so there is no atom cliff, and is also the permanent value for
-- non-doctrine atoms (Quran/Hadith/Term/Etymology are universal resources,
-- never level-gated).
--
-- SIMPLE ADD COLUMN pattern (like 020_atoms_add_tradition.sql) — does NOT use
-- rename-copy-drop, so it does NOT trigger the atom_topic_tags CASCADE wipe
-- documented in migration 024. Default NULL satisfies the CHECK (CHECK passes
-- on NULL in SQLite). Zero regression on all existing atoms.

ALTER TABLE atoms ADD COLUMN content_level TEXT
    CHECK (content_level IN ('history', 'shariah', 'esoteric', 'realities', 'universal'));

CREATE INDEX IF NOT EXISTS idx_atoms_content_level ON atoms (content_level);
