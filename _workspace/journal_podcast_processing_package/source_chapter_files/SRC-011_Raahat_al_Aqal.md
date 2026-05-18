# SRC-011 — Rāḥat al-ʿAql / The Comfort of the Intellect

## Source file

- Original archive item: `Raahat al-Aqal.pdf`
- Source type: PDF
- Page count: 591
- Extracted text status: No useful embedded text layer; OCR required
- Characters extracted from first 20 pages / whole TXT: 0
- Recommended library placement: `library/sources/ismaili/philosophy_and_theology/rahat_al_aql/`

## What this source is

A 591-page scanned Arabic PDF. The title identifies a major classical Ismaili philosophical text often associated with the intellectual tradition of Hamid al-Din al-Kirmani. It belongs in the advanced Ismaili philosophy section. The file lacks a usable embedded text layer, so OCR and careful translation are required before any podcast use.

## Raw English context / translation status

No usable embedded text layer. Full translation requires OCR and batching.

## Podcast use guidance

Use for advanced philosophy/theology podcasts: intellect, soul, cosmology, hierarchy, prophecy, imamate, and metaphysical order. It must be broken into small sections. NotebookLM should receive one chapter or argument unit at a time.

## Claude Code processing instructions for this source

1. Place the source in the recommended library folder.
2. Create a `source.yaml` manifest with source ID, title, author if known, language, script, page count, copyright/licensing notes, and processing status.
3. Detect whether the PDF has a usable text layer. If not, route it through Arabic OCR.
4. Preserve page anchors in the form `[[SRC-011:p0001]]` before translation.
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

