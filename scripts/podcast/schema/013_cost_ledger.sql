-- 013_cost_ledger.sql — Itemised LLM and Azure spend per pipeline operation.
-- Complements run_telemetry (which tracks phase-level totals) with per-call
-- line items for the cost-ledger JSONL → DB migration path.
-- Depends on: 003_book_metadata.sql, 005_run_telemetry.sql.

CREATE TABLE IF NOT EXISTS cost_ledger (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       TEXT,                          -- FK → run_telemetry.run_id (advisory)
    book_slug    TEXT    NOT NULL,
    chapter_id   TEXT,
    operation    TEXT    NOT NULL,             -- e.g. "0b_refine", "extract_chapter", "framing"
    provider     TEXT    NOT NULL DEFAULT 'anthropic'
                 CHECK (provider IN ('anthropic', 'azure', 'gemini', 'other')),
    model        TEXT,                         -- e.g. "claude-opus-4-7", "gpt-4o"
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd     REAL    NOT NULL DEFAULT 0.0,
    recorded_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_cost_ledger_book      ON cost_ledger (book_slug);
CREATE INDEX IF NOT EXISTS idx_cost_ledger_run       ON cost_ledger (run_id);
CREATE INDEX IF NOT EXISTS idx_cost_ledger_operation ON cost_ledger (operation);
