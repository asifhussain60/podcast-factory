-- The reader-facing half of the pipeline's source-crosswalk — proof that a
-- chapter's AI-articulated English traces to a specific span of the original
-- source book.
--
-- Written by the publish step (scripts/podcast/publish_to_listener.py) from
-- `content/<Bucket>/<slug>/book/source-crosswalk.json`, the file the
-- translation-edition print step builds to typeset the PDF's "Source
-- Crosswalk" appendix (see plan-dashboard/scripts/lib/book-html.mjs
-- `renderSourceCrosswalk`). This table is a SECOND, independent use of that
-- same file — nothing here is written by or read back into the print path.
--
-- Deliberately narrow: only `page_range` and `headings` travel from the
-- crosswalk. The crosswalk's `source_excerpt` (verbatim text from the
-- original, possibly copyrighted, source book) and `drift_findings`
-- (internal QA notes, not written for a reader) never leave disk — see
-- scripts/podcast/_listener_source_ref.py.
--
-- Reader-visible by design, unlike `companion_note`: this proves fidelity to
-- every reader who can already open the chapter, so there is no gate inside
-- the query that returns it. A book with no crosswalk file simply has no
-- rows here, which is what keeps the reader's toolbar toggle off entirely on
-- those books rather than showing a control with nothing behind it.
CREATE TABLE source_reference (
  slug        TEXT NOT NULL,
  anchor_key  TEXT NOT NULL,
  page_range  TEXT NOT NULL,           -- e.g. "pp. 1-5"; may be empty if only headings exist
  headings    TEXT NOT NULL,           -- JSON array of strings, the source book's own heading(s)
  PRIMARY KEY (slug, anchor_key)
);
