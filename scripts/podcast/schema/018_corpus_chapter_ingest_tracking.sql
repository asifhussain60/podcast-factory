-- 018_corpus_chapter_ingest_tracking.sql
-- Add ingestion-tracking columns to corpus_chapters for the Kashkole B0
-- ingestion driver. Uses ALTER TABLE ADD COLUMN (safe in SQLite; each column
-- has a DEFAULT or allows NULL so the extension is backward-compatible).
-- Idempotent: tracked by schema_migrations (runs exactly once).

ALTER TABLE corpus_chapters ADD COLUMN ingestion_status TEXT DEFAULT 'pending';
ALTER TABLE corpus_chapters ADD COLUMN verdict          TEXT;
ALTER TABLE corpus_chapters ADD COLUMN binder_id        INTEGER;
ALTER TABLE corpus_chapters ADD COLUMN chapter_id_num   INTEGER;
ALTER TABLE corpus_chapters ADD COLUMN binder_slug      TEXT;
ALTER TABLE corpus_chapters ADD COLUMN chapter_slug     TEXT;
ALTER TABLE corpus_chapters ADD COLUMN needs_review     INTEGER DEFAULT 0;
ALTER TABLE corpus_chapters ADD COLUMN correction_count INTEGER DEFAULT 0;
ALTER TABLE corpus_chapters ADD COLUMN last_ingested_at TEXT;
ALTER TABLE corpus_chapters ADD COLUMN correction_notes TEXT;

CREATE INDEX IF NOT EXISTS idx_cc_ingestion_status ON corpus_chapters (ingestion_status);
CREATE INDEX IF NOT EXISTS idx_cc_binder_id        ON corpus_chapters (binder_id);
