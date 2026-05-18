# Promoted — `TX-SURPRISE:density:ayyuhal-walad:EP02-hatim-eight-benefits`

**Status.** Accepted and merged on 2026-05-18.

**What changed.**
- Added a "Required POSITIVE companion" subsection to `R-NOSURPRISE` in `content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md`. The DENY list alone was empirically not enough — surprise vocabulary kept reappearing (5 distinct phrases × 1 transcript = 11 ledger firings on `ayyuhal-walad/EP02`). The positive companion paragraph instructs hosts to "name what is new in ONE short clause that advances the argument" instead of padding with reaction interjections.
- Updated R-NOSURPRISE Auto-fix to insert the DENY clause AND the positive companion together when the `## Do not` section exists.
- Applied to `content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP01-the-lineage-of-a-lost-argument/00-framing.md` (~140-word add; final 3,123 words, well within the 3,500-word hard cap).
- New regression fixture under `_learning/fixtures/surprise_positive_companion/` (presence check; expected 0 hits = positive companion present).

**Why the original proposal triggered.** 5× firings of distinct TX-SURPRISE vocabulary (`wow / Wow / right? / exactly / Exactly`) in a single transcript despite the framing carrying the canonical DENY clause. The rule was necessary-but-not-sufficient; the positive companion closes the loop by redirecting host prosody into substance.

**Acceptance check.** `python3 scripts/podcast/test_challenger.py` exits 0 with the new fixture; the kitab-al-riyad EP01 framing now carries both clauses and re-renders clean.

**Source proposal.** Deleted from `_learning/proposals/` per workflow ("delete on promotion"). This file is the audit trail.
