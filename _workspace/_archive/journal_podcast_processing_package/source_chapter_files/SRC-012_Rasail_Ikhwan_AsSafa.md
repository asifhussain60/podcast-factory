# SRC-012 — Rasāʾil Ikhwān al-Ṣafāʾ (Epistles of the Brethren of Purity)

## Source file

- Original archive item: `Rasail Ikhwan AsSafa.pdf`
- Source type: PDF
- Page count: 865
- Extracted text status: Text layer present and useful
- Characters extracted from first 20 pages / whole TXT: 50402
- Recommended library placement: `library/sources/islamic/philosophy/ikhwan_al_safa/`

## What this source is

A large Arabic encyclopedic corpus traditionally attributed to the Ikhwān al-Ṣafāʾ, organized as a set of treatises covering mathematics, natural philosophy, psychology, metaphysics, ethics, religion, music, logic, astronomy, animals, the soul, resurrection, and spiritual ascent. The opening table of contents states that the treatises are divided into four major divisions: mathematical and educational sciences, natural and corporeal sciences, psychic and intellectual sciences, and nomological, legal, and divine sciences. For the journal app, this belongs in the philosophical and religious-intellectual source library, not in memoir narrative. It should be processed as a multi-volume reference corpus with durable section anchors.

## Raw English context / translation status

The embedded text layer is present but Arabic shaping is imperfect. A complete raw English translation was not generated in this package because full translation of 865 pages requires OCR/translation batching. The journal app should extract each treatise into its own source file, preserve page anchors, then run literal translation in chunks.

## Podcast use guidance

Use as background context for philosophy, cosmology, soul, knowledge, ethics, and symbolic interpretation. Never compress the entire corpus into one podcast. Build episode clusters by treatise family. For NotebookLM, provide one treatise per source bundle plus a guide file defining vocabulary and cosmological schema.

## Claude Code processing instructions for this source

1. Place the source in the recommended library folder.
2. Create a `source.yaml` manifest with source ID, title, author if known, language, script, page count, copyright/licensing notes, and processing status.
3. Detect whether the PDF has a usable text layer. If not, route it through Arabic OCR.
4. Preserve page anchors in the form `[[SRC-012:p0001]]` before translation.
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

