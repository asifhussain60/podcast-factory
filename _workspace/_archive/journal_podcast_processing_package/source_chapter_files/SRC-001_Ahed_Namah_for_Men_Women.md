# SRC-001 — Ahed Namah for Men & Women

## Source file

- Original archive item: `Ahed Namah for Men & Women.pdf`
- Source type: PDF
- Page count: 20
- Extracted text status: No useful embedded text layer; OCR required
- Characters extracted from first 20 pages / whole TXT: 83
- Recommended library placement: `library/sources/ismaili/devotional/pledges_and_prayers/`

## What this source is

A short scanned PDF. The cover indicates it was scanned and processed by Javeed Ahmed Ziaee in Hyderabad in July 2005. The title suggests a pledge, covenant, or vow text intended for men and women. Because the OCR layer is mostly absent, the app should treat it as a devotional primary source requiring careful OCR and human validation before any podcast use.

## Raw English context / translation status

No reliable text layer was available beyond the scan note. Full raw translation requires OCR first.

## Podcast use guidance

Use only after OCR verification. This should be introduced as a devotional/covenantal text, with attention to ritual context, speaker, audience, and whether the wording is meant to be recited or explained. Do not paraphrase sacred pledge language loosely.

## Claude Code processing instructions for this source

1. Place the source in the recommended library folder.
2. Create a `source.yaml` manifest with source ID, title, author if known, language, script, page count, copyright/licensing notes, and processing status.
3. Detect whether the PDF has a usable text layer. If not, route it through Arabic OCR.
4. Preserve page anchors in the form `[[SRC-001:p0001]]` before translation.
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

