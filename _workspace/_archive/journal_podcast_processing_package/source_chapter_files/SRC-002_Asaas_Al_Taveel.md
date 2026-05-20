# SRC-002 — Asās al-Taʾwīl / Asaas Al-Taveel (Foundation of Esoteric Interpretation)

## Source file

- Original archive item: `Asaas Al-Taveel.pdf`
- Source type: PDF
- Page count: 416
- Extracted text status: No useful embedded text layer; OCR required
- Characters extracted from first 20 pages / whole TXT: 0
- Recommended library placement: `library/sources/ismaili/ta_wil_and_esotericism/`

## What this source is

A scanned Arabic PDF likely related to Ismaili taʾwīl, the discipline of esoteric interpretation. The title points to the classic Ismaili mode of interpreting scripture, prophetic narratives, ritual, and cosmology through inner meanings. The PDF has no usable embedded text layer, so it should enter the library as a scanned source requiring OCR, structural segmentation, and strict source anchoring before translation.

## Raw English context / translation status

Full raw translation was not generated because the PDF is scanned. It requires Arabic OCR and page-level validation.

## Podcast use guidance

Use as a foundational text for explaining taʾwīl and how exoteric narrative is paired with inner meaning. Episodes should separate raw translation from commentary. Do not allow the podcast skill to invent symbolic correspondences not present in the text.

## Claude Code processing instructions for this source

1. Place the source in the recommended library folder.
2. Create a `source.yaml` manifest with source ID, title, author if known, language, script, page count, copyright/licensing notes, and processing status.
3. Detect whether the PDF has a usable text layer. If not, route it through Arabic OCR.
4. Preserve page anchors in the form `[[SRC-002:p0001]]` before translation.
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

