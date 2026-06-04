-- 015_series_plans.sql — Series-plan artifacts generated at phase 0f.
-- Stores the episode arc, structural units, and audience profile decided at
-- the human-review gate so they can be queried without parsing YAML files.
-- Depends on: 003_book_metadata.sql.

CREATE TABLE IF NOT EXISTS series_plans (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    book_slug        TEXT    NOT NULL UNIQUE,  -- FK → book_metadata.slug (advisory)
    archetype_id     TEXT,                     -- resolved archetype slug
    audience_profile TEXT,                     -- e.g. "educated_general", "seminary"
    source_tradition TEXT,                     -- e.g. "ismaili_orthodox"
    episode_count    INTEGER,
    planning_mode    TEXT,                     -- "tribunal_arc" | "chronological" | ...
    series_plan_yaml TEXT,                     -- full YAML text of series-plan.md
    approved_at      TEXT,                     -- ISO-8601 datetime of human approval
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_series_plans_archetype ON series_plans (archetype_id);
