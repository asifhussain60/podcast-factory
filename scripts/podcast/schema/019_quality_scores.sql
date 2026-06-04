-- 019_quality_scores.sql — Per-chapter PEQ quality score log.
-- Enables trend analysis, regression detection, and the /quality dashboard page.
-- Depends on: 003_book_metadata.sql, 007_chapters.sql.

CREATE TABLE IF NOT EXISTS quality_scores (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    book_slug    TEXT    NOT NULL,          -- FK → book_metadata.slug (advisory)
    chapter_id   TEXT    NOT NULL,
    pipeline     TEXT    NOT NULL           -- 'podcast' | 'wisdom'
                 CHECK (pipeline IN ('podcast', 'wisdom')),
    fidelity     REAL    NOT NULL,          -- 0–100
    voice        REAL    NOT NULL,          -- 0–100
    structure    REAL    NOT NULL,          -- 0–100
    enrichment   REAL    NOT NULL,          -- 0–100
    total        REAL    NOT NULL,          -- 0–100  weighted sum
    verdict      TEXT    NOT NULL           -- PASS | WARN | FAIL
                 CHECK (verdict IN ('PASS', 'WARN', 'FAIL')),
    iteration    INTEGER NOT NULL DEFAULT 1, -- convergence loop iteration
    notes        TEXT,                      -- JSON array of scoring notes
    scored_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_qs_book     ON quality_scores (book_slug, chapter_id);
CREATE INDEX IF NOT EXISTS idx_qs_pipeline ON quality_scores (pipeline);
CREATE INDEX IF NOT EXISTS idx_qs_verdict  ON quality_scores (verdict);
CREATE INDEX IF NOT EXISTS idx_qs_scored   ON quality_scores (scored_at);
