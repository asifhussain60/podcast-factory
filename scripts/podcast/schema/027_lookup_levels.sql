-- 027_lookup_levels.sql
-- Wave N: import the Kashkole Lookup_levels table into knowledge.db.
-- Provides authoritative provenance for the CONTENT_LEVEL_LADDER in _rules.py.
-- The 6 base rungs (ids 1,4,5,6,7,11) map 1:1 to the existing ladder.
-- Combination levels (ids 8,9,10) are stored for completeness but are not
-- used by the pipeline ladder (they are derived from the base rungs).

CREATE TABLE IF NOT EXISTS lookup_levels (
    level_id    INTEGER PRIMARY KEY,  -- Kashkole LevelID
    level_name  TEXT    NOT NULL,     -- Kashkole LevelName (canonical English)
    level_urdu  TEXT,                 -- Kashkole LevelUrdu (display only)
    ordering    INTEGER,              -- Kashkole Ordering (sort key)
    code_id     TEXT,                 -- maps to CONTENT_LEVEL_LADDER code (nullable for combinations)
    color_hex   TEXT,                 -- CategoryBackColor from Kashkole
    is_base_rung INTEGER NOT NULL DEFAULT 0,  -- 1 = one of the 6 canonical rungs
    created_at  TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- 6 base rungs — these are the authoritative source for CONTENT_LEVEL_LADDER
INSERT OR IGNORE INTO lookup_levels
    (level_id, level_name, level_urdu, ordering, code_id, color_hex, is_base_rung)
VALUES
    (1,  'General',    'مضمون',          1, 'general',    '#6495ED', 1),
    (7,  'Advanced',   'اعلی مضمون',     2, 'advanced',   'purple',  1),
    (4,  'Taveel',     'تاویل',          3, 'taveel',     '#458B00', 1),
    (11, 'Mamsool',    'ممثولات',        4, 'mamsool',    '#FFD700', 1),
    (6,  'Mabda_Maad', 'مبدا و معاد',   5, 'mabda_maad', '#e845aa', 1),
    (5,  'Haqaiq',     'حقائق',          6, 'haqaiq',     '#AA0114', 1);

-- Combination levels — stored for reference, not used by the pipeline ladder
INSERT OR IGNORE INTO lookup_levels
    (level_id, level_name, level_urdu, ordering, code_id, is_base_rung)
VALUES
    (8,  'Taveel_Haqaiq',      'علم التاویل و الحقائق',      10, NULL, 0),
    (9,  'General_Taveel',     'مضمون و تاویل',               9,  NULL, 0),
    (10, 'Taveel_Mabda_Maad',  'علم التاویل و المبدأومعاد',   11, NULL, 0);
