-- 030_section_tags.sql
-- Option A: add section_tags column to section_depths.
-- Stores multi-select editorial tags (JSON array of tag IDs, e.g. '["esoteric","improve"]').
-- Same vocabulary as paragraph-level TAGS in StudioPoc.tsx.
-- Default empty array; NULL-safe: coalesce to '[]' in reads.

ALTER TABLE section_depths ADD COLUMN section_tags TEXT NOT NULL DEFAULT '[]';
