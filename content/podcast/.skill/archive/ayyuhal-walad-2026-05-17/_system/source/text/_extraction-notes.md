# Extraction Notes — Ayyuhal Walad

Audit trail for the source-text folder. Every uncertainty, every correction, every smoothing decision is logged here.

## Source

- File: `Ayyuhal-Walad.pdf` (146 KB, 30 pages, PDF v1.4)
- Origin: provided by Asif; English translation by Irfan Hasan from an Urdu rendering of the Arabic original.
- Original archive: `/Users/asifhussain/PROJECTS/journal/_workspace/podcast/ayyuhal-walad/00-source/Ayyuhal-Walad.pdf`.

## Extraction method

- The PDF has a text layer (digitally typeset, not scanned), so no OCR was required. Text was extracted by direct text-layer copy.
- Pages 1–28 carry running body text; pages 29–30 are end matter with no podcast-relevant content.

## Corrections applied to normalized.md

  - Rejoined hyphenated line breaks (e.g., `know-\nledge` → `knowledge`).
  - Removed repeated running headers and footers (page numbers, the source title repeated on every page).
  - Restored paragraph reflow where line breaks were purely typographic.
  - Preserved translator italics on transliterated Arabic terms.
  - Preserved square brackets and parentheses where they carry the translator's explanatory glosses; nothing was paraphrased.

## Uncertainties and flags

  - The TOC on page 1 lists "Pages" but the printed page numbers in the body are offset by one (TOC says page 3 for the response; body page 1 shows the start of the response). Inventory and segments use the body-relative spans, not the TOC numbers, to avoid ambiguity.
  - In two places the translator's parenthetical gloss runs to multiple sentences; the bundle treats those as translator commentary, not Ghazali's voice, and they are NOT quoted in `02-key-passages.md`.
  - The transliterated forms of Quranic verses occasionally differ slightly from standard scholarly transliteration schemes (e.g., `Famaey` instead of `Faman`). The translator's spellings are preserved verbatim in source files; the lexicon documents the agreed phonetic guide separately so the canonical bundle reads cleanly.

## Section detection

  - The TOC was used as a hypothesis. Each row was verified against the body before being promoted into `inventory.yml`. Two TOC entries that turned out to be a single paragraph inside another section were collapsed: this is recorded in `segmentation-rationale.md`.

## What was NOT done

  - No paraphrasing.
  - No "improving" the translator's English.
  - No silent reordering.
  - No insertion of explanatory bridging text.

If a future pass requires re-correction, write `normalized.v2.md` rather than overwriting `normalized.md`, and update this file with the reason.
