# SRC-008 — Majālis al-Muʾayyadiyya / Majalis Moyyada

## Source file

- Original archive item: `Majalis Moyyada.pdf`
- Source type: PDF
- Page count: 139
- Extracted text status: No useful embedded text layer; OCR required
- Characters extracted from first 20 pages / whole TXT: 0
- Recommended library placement: `library/sources/ismaili/majalis/muayyad/`

## What this source is

A scanned Arabic PDF likely containing the majālis or discourses associated with al-Muʾayyad fi'l-Dīn al-Shīrāzī or the Muʾayyadi tradition. Majālis material is usually structured as religious teaching, doctrinal exposition, Qur'anic interpretation, ethical guidance, and community instruction. The PDF has no usable text layer and requires OCR.

## Raw English context / translation status

No reliable embedded text layer. Requires OCR and translation.

## Podcast use guidance

Excellent candidate for episodic teaching podcasts once OCR is complete. Each majlis should become its own NotebookLM source bundle with raw translation, glossary, speaker context, and doctrinal map.

## Claude Code processing instructions for this source

1. Place the source in the recommended library folder.
2. Create a `source.yaml` manifest with source ID, title, author if known, language, script, page count, copyright/licensing notes, and processing status.
3. Detect whether the PDF has a usable text layer. If not, route it through Arabic OCR.
4. Preserve page anchors in the form `[[SRC-008:p0001]]` before translation.
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

