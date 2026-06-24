# Noise Audit — Per-Surface Confirmation Re-Sweep

- `noise_auditor_version`: 1.0
- date: 2026-06-23
- book: al-anwaar-al-lateefah / vol-01
- scope: AGGRESSIVE (NZ-CIRCULATION + NZ-PROVENANCE in-scope)
- baseline: commit b8e8eddf (apparatus stripped at root + noise-auditor added)
- taxonomy: scripts/podcast/_rules.py — R_NOISE_APPARATUS_CATEGORIES / _PROTECT / _PATTERNS

## Method

Pass-1: grep R_NOISE_APPARATUS_PATTERNS (plus incident-specific phrasing and NZ-EDITORIAL
soft-framing) across every file in each surface. Pass-2: read each candidate in context and
judge against the one test (claim about reality/God/soul/path/law = KEEP; claim about the
book-object's recording/authorization/circulation = STRIP) and the PROTECT-list.

## Surface 1 — NotebookLM upload sources (chapters/*.txt, 11 files)

VERDICT: CLEAN. 0 NZ findings.
- ch01a opener (L1-71) re-derived: inherited-science epistemics + five-fold architecture +
  pure-reality method + wilayah/allegiance doctrine. No ijazat/treasury/cold-iron/do-not-email.
- Pass-1 hits in ch01a/02b/03c/04a/05b/06c/07d are `compiled by` citation lines for quoted
  maxims (Nahj al-Balagha / Ghurar al-Hikam) -> source attribution, KEEP.
- ch06c:57,61 `undeserving`/`treasury` = fasting-as-concealing-knowledge + House-of-Allah =
  Imam al-Zaman doctrine -> PROTECT (imam/doctrine), KEEP.

## Surface 2 — Episode framings (episodes/*.txt, 11 files)

VERDICT: CLEAN. 0 NZ findings. 0 Pass-1 candidates.
- EP01 Beat 1 now built from the inherited-science doctrine and the spine sentence
  ("Oneness reached by two things only — loving allegiance and lawful action"); the prior
  distribution-warning spine is gone.

## Surface 3 — Slide-deck bundles (slide-decks/*deck*.txt + *framing*.md, 22 files)

VERDICT: CLEAN. 0 NZ findings.
- ch01a deck + framing carry no ijazat/treasury/do-not/cold-iron/provenance.
- 7 Pass-1 hits are `compiled by` citation lines -> KEEP (same as Surface 1).

## Surface 4 — Reading edition (book/book.md, 925 lines; + book-illustrated.md)

VERDICT: CLEAN. 0 NZ findings.
- Preface (L1-67) and ch.1 opener re-derived to PROTECT-list epistemics; the near-verbatim
  preface<->ch.1 apparatus duplication (former NZ-DUP-01) collapsed.
- book-illustrated.md: provenance chain-of-custody diagram removed; no apparatus on re-grep.
- L483 `undeserving`/`House of Allah` = fasting/khums/hajj inner-meaning doctrine -> KEEP.

## Rollup

P0=0, P1=0, P2=0 across all 45 files. Overall verdict: CLEAN.
Root cause of original defect (denoise had no NZ category) fixed at root in _rules.py +
gemini_refine + full_book_denoise. Only open item: EP01 NotebookLM audio re-generation
(user/NotebookLM action, out of identify-only scope).
