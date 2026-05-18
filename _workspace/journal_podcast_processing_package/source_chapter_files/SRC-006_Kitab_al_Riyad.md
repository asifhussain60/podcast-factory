# SRC-006 — Kitāb al-Riyāḍ (The Book of Gardens)

## Source file

- Original archive item: `Kitab al-Riyad.pdf`
- Source type: PDF
- Page count: 260
- Extracted text status: No useful embedded text layer; OCR required
- Characters extracted from first 20 pages / whole TXT: 0
- Recommended library placement: `library/sources/ismaili/philosophy_and_theology/kirmani_or_classical/`

## What this source is

A scanned Arabic PDF. The title indicates a classical Ismaili intellectual text, likely associated with the philosophical-theological tradition. Because no reliable text layer is present, process it as a scanned Arabic source. The app should extract page images, OCR them, identify chapter headings, then translate literally before any explanatory expansion.

## Raw English context / translation status

No embedded text layer was usable. Full raw translation requires OCR and translation batching.

## Podcast use guidance

Use for advanced episodes on Ismaili metaphysics, intellect, soul, hierarchy, cosmology, and philosophical argument. It should not be simplified into generic spirituality before a raw translation exists.

## Claude Code processing instructions for this source

1. Place the source in the recommended library folder.
2. Create a `source.yaml` manifest with source ID, title, author if known, language, script, page count, copyright/licensing notes, and processing status.
3. Detect whether the PDF has a usable text layer. If not, route it through Arabic OCR.
4. Preserve page anchors in the form `[[SRC-006:p0001]]` before translation.
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

