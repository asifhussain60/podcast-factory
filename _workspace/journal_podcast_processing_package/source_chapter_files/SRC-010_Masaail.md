# SRC-010 — Masāʾil (Questions / Issues) - alternate scan

## Source file

- Original archive item: `Masaail.pdf`
- Source type: PDF
- Page count: 81
- Extracted text status: Text layer present and useful
- Characters extracted from first 20 pages / whole TXT: 13044
- Recommended library placement: `library/sources/ismaili/questions_and_answers/masaail/`

## What this source is

An alternate 81-page scan of Masāʾil. It appears similar to the searchable version but has degraded text extraction. Use it as an image source for re-OCR, then compare against the searchable version to improve accuracy.

## Raw English context / translation status

Existing text extraction is not reliable. Re-OCR and compare against the searchable file.

## Podcast use guidance

Same podcast role as the searchable version: structured Q&A episodes after verified OCR. Use the two versions together for OCR confidence voting.

## Claude Code processing instructions for this source

1. Place the source in the recommended library folder.
2. Create a `source.yaml` manifest with source ID, title, author if known, language, script, page count, copyright/licensing notes, and processing status.
3. Detect whether the PDF has a usable text layer. If not, route it through Arabic OCR.
4. Preserve page anchors in the form `[[SRC-010:p0001]]` before translation.
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

