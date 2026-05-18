# Rule Promotion Proposal — `TX-SURPRISE:density:ayyuhal-walad:EP02-hatim-eight-benefits`

**Trigger (density).** 5× firings of `TX-SURPRISE` within `ayyuhal-walad/EP02-hatim-eight-benefits` — in-book density ≥ 3.

**Trigger.** Signature `TX-SURPRISE:density:ayyuhal-walad:EP02-hatim-eight-benefits` recurs across 1 book(s) and 1 episode(s); 5 total ledger records.
**Occurrences.** 5 records.
**Distinct books.** 1 — ayyuhal-walad
**Distinct episodes.** 1 — EP02-hatim-eight-benefits
**First seen.** 2026-05-18T18:02:22Z
**Last seen.** 2026-05-18T18:02:22Z
**Severity carried.** P1
**Check id.** `TX-SURPRISE`
**Producer:** `scripts/podcast/learn_propose.py` v1.2

## Sample excerpts

- `wow`
- `Wow`
- `right?`
- `exactly`
- `Exactly`

## Candidate rule

_Author drafts the rule text here. Suggested shape: add the offending phrase / pattern to the canonical list named in 'Target file(s)' so future runs of the challenger or audit catch it deterministically. If `TX-SURPRISE` is empirical-only (transcript-level), consider whether a framing-side directive can prevent it at generation time._

## Target file(s)

- content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md (R-NOSURPRISE) + scripts/podcast/_rules.py (SURPRISE_DENY)

## Fixture

Add to `_learning/fixtures/TX-SURPRISE/`:
- `input.txt` — minimal artifact exhibiting the failure (e.g., a 3-sentence framing snippet that contains the phrase)
- `expected.json` — challenger findings the new rule should emit when run against `input.txt`

## Acceptance

- `scripts/podcast/test_challenger.py` exits 0 after the rule lands.
- `_learning/findings.jsonl` shows the signature **stops appearing** (or appears only as `resolution: auto-fixed`) in subsequent runs.
- `content/podcast/.skill/ROADMAP.md` Section A gains an entry referencing this proposal with the merging commit hash.

## Verdict (human)

- [ ] **Accept** — promote rule to the normative file named in Target, move this file to `_learning/promoted/` with the merging commit hash appended below.
- [ ] **Reject** — move this file to `_learning/archive/` with a `Rejected because…` line appended below.
- [ ] **Defer** — leave in place; revisit after N more episodes.

## Decision log

_(append commit hash + one-line rationale when promoted/rejected)_
