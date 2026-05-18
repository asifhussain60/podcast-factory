# SRC-005 — Kitāb Maqbas al-Akhbār al-Jāriyah fī Akhyār wa Ashrār, attributed in filename to Sayyidnā Ali bin Sayyidnā Sulaiman

## Source file

- Original archive item: `Kitab Maqbas al Akhbar al Jariyah fi Akhyar wa Ashrar - Sayedna Ali bin Sayedna Sulaiman PDF (2).pdf`
- Source type: PDF
- Page count: 392
- Extracted text status: No useful embedded text layer; OCR required
- Characters extracted from first 20 pages / whole TXT: 0
- Recommended library placement: `library/sources/ismaili/history_and_adab/maqbas_al_akhbar/`

## What this source is

A very large scanned Arabic PDF. The title suggests a collection of reports, accounts, or narratives concerning good and evil people or deeds. The file is 392 pages and 247 MB, so it is image-heavy. It should be treated as a major scanned source requiring a robust OCR pipeline, page splitting, and long-running batch processing. Because of the size, it is not suitable for direct NotebookLM upload without preprocessing.

## Raw English context / translation status

No reliable text layer was available. Full raw translation requires high-accuracy Arabic OCR and batching.

## Podcast use guidance

Use only after OCR segmentation. Likely useful for moral narrative, historical exempla, warnings, virtues, vices, and character-driven religious instruction. Build episodes around narrative units, not arbitrary page chunks.

## Claude Code processing instructions for this source

1. Place the source in the recommended library folder.
2. Create a `source.yaml` manifest with source ID, title, author if known, language, script, page count, copyright/licensing notes, and processing status.
3. Detect whether the PDF has a usable text layer. If not, route it through Arabic OCR.
4. Preserve page anchors in the form `[[SRC-005:p0001]]` before translation.
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

