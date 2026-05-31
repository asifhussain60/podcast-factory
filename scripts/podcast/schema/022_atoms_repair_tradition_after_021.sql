-- 022_atoms_repair_tradition_after_021.sql
--
-- One-time repair: migration 021 used `INSERT OR IGNORE INTO atoms_v21 SELECT * FROM atoms`
-- without an explicit column list. The pre-021 column order (post-020 ALTER ADD) was
--   (id, type, body, first_seen_book, first_seen_chapter, first_seen_date,
--    confidence, created_at, updated_at, tradition)
-- but atoms_v21 was created with
--   (id, type, body, first_seen_book, first_seen_chapter, first_seen_date,
--    confidence, tradition, created_at, updated_at).
-- The positional SELECT shifted created_at INTO the tradition column on every
-- row present at 021-time. Result: doctrine atoms now have a timestamp string
-- in the tradition column, which breaks tradition-filtered augmenter injection
-- (augmenter.py line 153 — `WHERE (a.tradition = ? OR a.tradition = 'universal')`).
--
-- Fix: rebuild tradition from the body JSON (which DOES carry the correct
-- "tradition" key for every wisdom-ingest atom and every MCP-ingest atom).
-- For atoms whose body has no tradition key, fall back to 'universal' (the
-- column default and the safe value for cross-tradition material).
--
-- Idempotent: the WHERE clause only touches rows that look broken (tradition
-- starts with '20', the timestamp shape) and leaves correctly-stamped rows alone.
-- Re-running this migration on a clean DB is a no-op.

UPDATE atoms
   SET tradition = COALESCE(json_extract(body, '$.tradition'), 'universal')
 WHERE tradition LIKE '20__-__-__T%';
