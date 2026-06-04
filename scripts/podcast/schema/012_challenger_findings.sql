-- 012_challenger_findings.sql — Per-chapter challenger audit findings log.
-- Enables trend analysis, regression detection, and the podcast-trainer's
-- pattern-learning input.
-- Depends on: 003_book_metadata.sql.

CREATE TABLE IF NOT EXISTS challenger_findings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    book_slug    TEXT    NOT NULL,          -- FK → book_metadata.slug (advisory)
    chapter_id   TEXT    NOT NULL,
    episode_id   TEXT,                      -- FK → episodes.id (advisory)
    finding_id   TEXT,                      -- e.g. "P0-001", "PR-003"
    severity     TEXT    NOT NULL
                 CHECK (severity IN ('P0', 'P1', 'P2', 'P3')),
    category     TEXT,                      -- challenger category code (A, C, J, ...)
    description  TEXT    NOT NULL,
    auto_fixed   INTEGER NOT NULL DEFAULT 0 -- 1 if the fixer resolved this automatically
                 CHECK (auto_fixed IN (0, 1)),
    iteration    INTEGER NOT NULL DEFAULT 1, -- convergence loop iteration number
    run_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_cf_book     ON challenger_findings (book_slug, chapter_id);
CREATE INDEX IF NOT EXISTS idx_cf_severity ON challenger_findings (severity);
CREATE INDEX IF NOT EXISTS idx_cf_run_at   ON challenger_findings (run_at);
