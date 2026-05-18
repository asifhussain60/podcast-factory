# Rule Promotion Proposal — `N3:density:kitab-al-riyad:EP01-the-lineage-of-a-lost-argument`

**Trigger (density).** 6× firings of `N3` within `kitab-al-riyad/EP01-the-lineage-of-a-lost-argument` — in-book density ≥ 3.

**Trigger.** Signature `N3:density:kitab-al-riyad:EP01-the-lineage-of-a-lost-argument` recurs across 1 book(s) and 1 episode(s); 6 total ledger records.
**Occurrences.** 6 records.
**Distinct books.** 1 — kitab-al-riyad
**Distinct episodes.** 1 — EP01-the-lineage-of-a-lost-argument
**First seen.** 2026-05-18T18:06:43Z
**Last seen.** 2026-05-18T18:06:43Z
**Severity carried.** P1
**Check id.** `N3`
**Producer:** `scripts/podcast/learn_propose.py` v1.2

## Sample excerpts

- `amal appears in chapter line 52; no Pronounce directive in framing`
- `abwab/bab appears in chapter line 139; no Pronounce directive in framing`
- `fusul/fasl appears in chapter line 139; no Pronounce directive in framing`
- `tamma/naqisa appears in chapter line 141; no Pronounce directive in framing`
- `Mu tazila appears in chapter line 64; no Pronounce directive in framing`

## Candidate rule

_Author drafts the rule text here. Suggested shape: add the offending phrase / pattern to the canonical list named in 'Target file(s)' so future runs of the challenger or audit catch it deterministically. If `N3` is empirical-only (transcript-level), consider whether a framing-side directive can prevent it at generation time._

## Target file(s)

- content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md (R-PRONUNCIATION-IMPERATIVE) + BOOK_DIR/_system/source/text/_phonetics.md

## Fixture

Add to `_learning/fixtures/N3/`:
- `input.txt` — minimal artifact exhibiting the failure (e.g., a 3-sentence framing snippet that contains the phrase)
- `expected.json` — challenger findings the new rule should emit when run against `input.txt`

## Acceptance

- `scripts/podcast/test_challenger.py` exits 0 after the rule lands.
- `_learning/findings.jsonl` shows the signature **stops appearing** (or appears only as `resolution: auto-fixed`) in subsequent runs.
- `content/podcast/.skill/ROADMAP.md` Section A gains an entry referencing this proposal with the merging commit hash.

## Verdict (human)

- [ ] **Accept** — promote rule to the normative file named in Target, move this file to `_learning/promoted/` with the merging commit hash appended below.
- [x] **Reject** — moved to `_learning/archive/` with rationale below.
- [ ] **Defer** — leave in place; revisit after N more episodes.

## Decision log

- **2026-05-18 · commit 7ab3ac3 (challenger v2.0)** — Archived (not promoted). Root cause already fixed in challenger v2.0: the v1.0 challenger that produced these 6 N3 flags blocked R-* clause insertion against a hallucinated 3,000-word framing cap. The actual `FRAMING_WORD_MAX` in `scripts/podcast/build_episode_txt.py` has been 3,500 since the Extended-tier landing. The v2.0 spec (E1) explicitly reconciles this: at the 2,983-word EP01 framing, there is ~500 words of headroom for the missing `Pronounce` directives. **Action required at the next v2.0 challenger run on `kitab-al-riyad`** — the auto-fix path will insert all 6 directives in one pass. No new rule needed; existing rule is sufficient once the cap reconciliation is in effect.
- **Recurrence guard.** If N3 density crosses ≥3 again on `kitab-al-riyad` EP01 *after* a v2.0 challenger pass has run, that would be a real regression (auto-fix path is broken). Reopen this proposal at that point.
