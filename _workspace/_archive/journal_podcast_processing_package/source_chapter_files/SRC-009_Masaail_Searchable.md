# SRC-009 — Masāʾil (Questions / Issues) - Searchable version

## Source file

- Original archive item: `Masaail - Searchable.pdf`
- Source type: PDF
- Page count: 81
- Extracted text status: Text layer present and useful
- Characters extracted from first 20 pages / whole TXT: 11995
- Recommended library placement: `library/sources/ismaili/questions_and_answers/masaail/`

## What this source is

An 81-page PDF with an OCR/text layer, but the extracted text is highly degraded, with Arabic characters misrecognized into Latin-like glyphs and broken sequences. The title means 'questions' or 'issues', suggesting a catechetical, doctrinal, legal, or explanatory Q&A format. Treat the file as partially searchable but not translation-ready without OCR correction.

## Raw English context / translation status

OCR layer exists but is poor. Full raw translation requires re-OCR using a better Arabic OCR engine.

## Podcast use guidance

Potentially useful for Q&A style episodes after cleanup. The podcast skill should detect question/answer boundaries and preserve them. Do not use the current OCR text as authoritative.

## Claude Code processing instructions for this source

1. Place the source in the recommended library folder.
2. Create a `source.yaml` manifest with source ID, title, author if known, language, script, page count, copyright/licensing notes, and processing status.
3. Detect whether the PDF has a usable text layer. If not, route it through Arabic OCR.
4. Preserve page anchors in the form `[[SRC-009:p0001]]` before translation.
5. Produce outputs in this order:
   - `original_ocr.md` or `original_text.md`
   - `raw_translation_en.md`
   - `translation_qc.md`
   - `podcast_source_context.md`
   - `notebooklm_audio_brief.md`
6. Never overwrite the raw OCR or raw translation during refinement. Create derived files instead.
7. Do not use this source in a podcast until the source status is at least `OCR_VERIFIED` and `TRANSLATION_DRAFTED`.

## NotebookLM packaging rule

NotebookLM should receive a clean English source bundle containing:

- raw translation,
- short source context,
- glossary and pronunciation guide,
- episode focus prompt,
- exclusions and cautions,
- citation map back to page anchors.

