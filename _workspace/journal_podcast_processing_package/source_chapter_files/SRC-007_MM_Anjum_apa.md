# SRC-007 — MM - Anjum apa

## Source file

- Original archive item: `MM - Anjum apa.pdf`
- Source type: PDF
- Page count: 17
- Extracted text status: Text layer present and useful
- Characters extracted from first 20 pages / whole TXT: 49974
- Recommended library placement: `library/sources/ismaili/notes_and_lessons/creation_cosmology/`

## What this source is

A short 17-page PDF with a noisy English OCR layer. The visible content discusses Ahle Haq views of creation, the universe, divine revelation, the Prophet, Maula Ali, the chain of Imams, and primary creation in the world of spirits or 'Aalam al-Ibda'. The OCR is noisy, but enough text is present to classify it as explanatory notes on creation and cosmology.

## Raw English context / translation status

English OCR exists but is noisy. The app should repair OCR before using it for podcasts.

## Podcast use guidance

Useful as a teaching-note source after cleanup. It should be normalized carefully, preserving theological terms such as Aalam al-Anwar, Aalam al-Ibda, Maula Ali, and Imam terminology.

## Claude Code processing instructions for this source

1. Place the source in the recommended library folder.
2. Create a `source.yaml` manifest with source ID, title, author if known, language, script, page count, copyright/licensing notes, and processing status.
3. Detect whether the PDF has a usable text layer. If not, route it through Arabic OCR.
4. Preserve page anchors in the form `[[SRC-007:p0001]]` before translation.
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

