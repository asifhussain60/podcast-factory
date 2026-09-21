-- The source a chapter was made from, for moderators checking a correction against it.
--
-- READ BY MODERATORS AND ADMINS ONLY, through `sourceOcr.server.ts`, which returns nothing
-- WITHOUT QUERYING THIS TABLE unless the viewer is one. This is the same precedent as
-- `companion_note`, and for the same reason: a per-row gate that lives in the caller is a gate
-- somebody forgets. It must never be joined to `source_reference`, which is reader-visible by
-- design and carries only a page range and headings — the verbatim source text is copyrighted
-- prose that no reader-facing surface reproduces.
--
-- One row per PAGE, not per chapter. D1 rejects a single statement past ~100KB and a scanned
-- chapter runs long; a page is always small, and it is the unit the source's own page markers
-- and the crosswalk already speak in.
--
-- `kind` says WHAT the text is, because the difference matters to whoever is judging a fix:
--   'scan'      the OCR of the scanned page — the original letters, and possibly an OCR error;
--   'extracted' the pipeline's own English extraction — already an interpretation.
CREATE TABLE source_page (
  slug   TEXT NOT NULL,
  kind   TEXT NOT NULL CHECK (kind IN ('scan', 'extracted')),
  page   INTEGER NOT NULL,
  text   TEXT NOT NULL,
  PRIMARY KEY (slug, kind, page)
);

-- Which pages belong to which chapter, and how far to trust the text. Paired to chapters by
-- `anchor_key` (never by index — every book gets a pipeline-written introduction that shifts
-- positions by one; see _listener_source_ref.py).
CREATE TABLE source_span (
  slug       TEXT NOT NULL,
  anchor_key TEXT NOT NULL,
  kind       TEXT NOT NULL CHECK (kind IN ('scan', 'extracted')),
  first_page INTEGER NOT NULL,
  last_page  INTEGER NOT NULL,
  -- 'clean' | 'noisy' | 'unreliable' — a heuristic over the OCR text, shown as a badge so a
  -- handwritten scan is never presented with the confidence of a clean one.
  quality    TEXT NOT NULL DEFAULT 'clean' CHECK (quality IN ('clean', 'noisy', 'unreliable')),
  PRIMARY KEY (slug, anchor_key, kind)
);
