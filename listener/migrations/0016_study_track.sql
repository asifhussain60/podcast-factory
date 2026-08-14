-- Classifies a book's doctrinal advancement level for the library ribbon —
-- theology (foundational), esoterics (intermediate), history (advanced).
ALTER TABLE unit_detail ADD COLUMN study_track TEXT
  CHECK (study_track IS NULL OR study_track IN ('theology', 'esoterics', 'history'));
