-- 004_archetype_registry.sql — Content-as-config archetype registry.
-- Stores the rendered text of each archetype's three files so the DB can
-- serve as a self-contained snapshot. The on-disk files in
-- content/_shared/archetypes/<slug>/ are the source of truth; these columns
-- are populated by _archetypes.py when run_migrations() is called.

CREATE TABLE IF NOT EXISTS archetype_registry (
    slug             TEXT PRIMARY KEY,     -- e.g. "scholarly-deep-dive"
    spec_yml         TEXT,                 -- contents of spec.yml
    exemplar_md      TEXT,                 -- contents of exemplar.md
    anti_patterns_md TEXT,                 -- contents of anti-patterns.md
    updated_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
