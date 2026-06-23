# Noise Audit — al-Anwaar al-Lateefah, Volume 1 (rollup)

- `noise_auditor_version`: 1.0
- date: 2026-06-23
- scope: **AGGRESSIVE** — NZ-CIRCULATION + NZ-PROVENANCE both in-scope (book owner direction 2026-06-23)
- surfaces swept: `chapters/*.txt` (11), `episodes/*.txt` (11), `slide-decks/*deck*.txt` + `*framing*.md` (22), `book/book.md` (971 lines)
- taxonomy: `scripts/podcast/_rules.py` Wave-N (`R_NOISE_APPARATUS_CATEGORIES` / `_PROTECT` / `_PATTERNS`)

## Verdict: **NOISE-FOUND** — localized, not systemic

Authorial-apparatus noise (the recorder's distribution warning + ijazat/treasury chain-of-custody) leaked from the **opening chapter only** into **all four deliverable surfaces**. Chapters/episodes/decks 2–11 and book.md lines 69–971 are **CLEAN** — every apparatus-shaped grep hit there is either a bibliographic citation of a quoted source (`Nahj al-Balagha`, compiled by al-Sharif al-Radi) or a PROTECT-list teaching use ("set down", "distribution of justice", "undeserving" in the zakat/fasting sense).

## Root findings (cross-surface dedup)

Three root defects. The same passage leaked to multiple surfaces — counted once, with all `surface_hits`.

| Root | Category | Sev | Surfaces hit | Locations |
|---|---|---|---|---|
| **NZ-CIRCULATION-01** — distribution/copyright warning: do-not-email/store-on-computer/share-online, copy-is-a-sin, accountability disclaimer, punishment of cold iron | NZ-CIRCULATION | **P0** | book, chapters, episodes, slides | `book/book.md` preface L21–25 + ch.1 L53–57 · `chapters/ch01a…txt` :7,:25,:33,:35 · `episodes/EP01…txt` :29 (Beat 1) · `slide-decks/ch01a-deck…txt` :65–106 |
| **NZ-PROVENANCE-01** — chain-of-custody: ijazat-to-record, recorded-first-for-family, treasury deposit, twofold authority-of-this-recording | NZ-PROVENANCE | **P0** | book, chapters, episodes, slides | `book/book.md` preface L13–19 + ch.1 L45–51 · `chapters/ch01a…txt` :19,:21 · `episodes/EP01…txt` :4,:11,:30 · `slide-decks/ch01a-deck…txt` :40–57 + `ch01a-framing…md` :10 |
| **NZ-DUP-01** — preface ≈ ch.1: the same five-paragraph apparatus block is rewritten near-verbatim in two adjacent sections (reader meets the cold-iron warning twice in ~40 lines) | NZ-EDITORIAL | **P1** | book | `book/book.md` preface L3–35 vs ch.1 L37–67 |

## Root cause

The denoise/refine step (`full_book_denoise.py`, `gemini_refine.py`) strips OCR artefacts, translator footnotes, page numbers, and editor brackets — it has **no category** for clean *authorial* prose that is non-teaching meta about the book-object. The opener's front-matter therefore survived denoise, survived segmentation (carried into BOTH the preface and ch.1), and fanned into every downstream surface. Two aggravators: (1) `full_book_denoise.py`'s prompts are hardcoded to a different book ("Ayyuhal Walad / al-Ghazali"); (2) a book-specific `split_synthesis_al_anwaar.py` suggests this book took a bespoke path that may have bypassed normal denoise.

## PROTECT-list held correctly

The aggressive scope did **not** over-strip. The doctrine of allegiance to the Imams / Friends of Allah (wilayah), the inherited-from-prophets/saints epistemics, and the soul-return-to-the-homeland spine were all kept (they live in the paragraph *before* the apparatus at preface L11 / ch.1 L43, and recur intact at ch01a:87). The braided openers get `split` recommendations, never wholesale deletion.

## Remediation (recommend — Tier-2, owner authorizes)

1. **Root fix (do once):** give the denoise prompts the Wave-N NZ category (book-agnostic), so apparatus is stripped at ingest for every future book. Verify `split_synthesis_al_anwaar.py` routes through it.
2. **Re-derive the opener:** strip NZ-CIRCULATION-01 + NZ-PROVENANCE-01 from the source, re-segment, and collapse the preface↔ch.1 duplication, keeping only the PROTECT-list epistemics/wilayah paragraph.
3. **Regenerate affected surfaces (opener only):** ch01a chapter source → re-author EP01 framing (lead with doctrine) → regenerate EP01 deck + (Tier-2, NotebookLM) EP01 audio → recompose book.md → re-render book.pdf.

Surfaces 2–11 need no work.

## Remediation applied (2026-06-23)

- **Root fix (B):** `R_NOISE_APPARATUS_*` + `R_NOISE_APPARATUS_DIRECTIVE` added to `_rules.py`; injected into `gemini_refine.DENOISE_SYS` and `full_book_denoise.build_system_prompts` (the latter de-hardcoded from "Ayyuhal Walad" → book-agnostic). `split_synthesis_al_anwaar.py` confirmed a pure splitter (no denoise) — apparatus predated the split; root fix covers future books.
- **Opener re-derived (C):** apparatus stripped from `book/book.md`, `book/book-illustrated.md` (incl. the provenance chain-of-custody DIAGRAM), `chapters/ch01a…txt`, `episodes/EP01…txt`, `slide-decks/ch01a-deck…txt` + `…framing…md`. Preface↔ch.1 duplication collapsed. `book.pdf` re-rendered (1888 KB, down from 1964 KB). All wilayah/allegiance doctrine preserved.
- **Outstanding (user, NotebookLM):** EP01 **audio** must be regenerated — re-upload the cleaned `chapters/ch01a…txt` + `episodes/EP01…txt` to NotebookLM and replace the `m4a/` for EP01.
- **Agent wired (D):** `noise-auditor` installed; docs swept (framework.md, podcast-challenger.md I5, SKILL.md 0b).
