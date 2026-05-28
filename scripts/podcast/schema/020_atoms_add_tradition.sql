-- 020_atoms_add_tradition.sql — Add tradition column to atoms table (Wave I, I3).
-- Enables tradition-aware KB filtering: augmenter only injects atoms whose
-- tradition matches the book's tradition_affinity (or is 'universal').
-- Default 'universal' ensures zero regression on all existing atoms.

ALTER TABLE atoms ADD COLUMN tradition TEXT NOT NULL DEFAULT 'universal';

-- Backfill ismaili atoms: wisdom corpus atoms carry {"tradition":"ismaili"} in
-- their JSON body. Extract and set the column so queries work without JSON parse.
UPDATE atoms
SET tradition = 'ismaili'
WHERE type = 'doctrine'
  AND json_extract(body, '$.tradition') = 'ismaili';

CREATE INDEX IF NOT EXISTS idx_atoms_tradition ON atoms (tradition);
