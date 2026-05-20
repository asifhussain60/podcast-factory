# SRC-003 — Ayyuhā al-Walad / My Dear Beloved Son or Daughter

## Source file

- Original archive item: `Ayyuhal Walad.pdf`
- Source type: PDF
- Page count: 30
- Extracted text status: Text layer present and useful
- Characters extracted from first 20 pages / whole TXT: 59484
- Recommended library placement: `library/sources/islamic/ethics_and_spiritual_counsel/ghazali/`

## What this source is

An English translation of Imam Abu Hamid al-Ghazali's Ayyuhā al-Walad. The table of contents includes the introduction, Ghazali's response to a student's letter, benefits narrated by Hatim ibn Ism, qualities of a spiritual guide, obedience and etiquette toward a guide, reality of knowledge, and supplications. It is already in English and can be processed directly for NotebookLM after cleanup and sectioning.

## Raw English context / translation status

This file is already an English translation. The journal app should preserve the existing translation as raw source text and create a separate enhanced podcast layer.

## Podcast use guidance

Good source for ethical counsel episodes: knowledge versus action, spiritual discipline, teacher-student relationship, sincerity, and the practical limits of learning without practice. It should be processed as advice literature, not polemic or history.

## Claude Code processing instructions for this source

1. Place the source in the recommended library folder.
2. Create a `source.yaml` manifest with source ID, title, author if known, language, script, page count, copyright/licensing notes, and processing status.
3. Detect whether the PDF has a usable text layer. If not, route it through Arabic OCR.
4. Preserve page anchors in the form `[[SRC-003:p0001]]` before translation.
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

