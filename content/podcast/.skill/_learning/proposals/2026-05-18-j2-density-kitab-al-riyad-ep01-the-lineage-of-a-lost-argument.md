# Rule Promotion Proposal — `J2:density:kitab-al-riyad:EP01-the-lineage-of-a-lost-argument`

**Trigger (density).** 3× firings of `J2` within `kitab-al-riyad/EP01-the-lineage-of-a-lost-argument` — in-book density ≥ 3.

**Trigger.** Signature `J2:density:kitab-al-riyad:EP01-the-lineage-of-a-lost-argument` recurs across 1 book(s) and 1 episode(s); 3 total ledger records.
**Occurrences.** 3 records.
**Distinct books.** 1 — kitab-al-riyad
**Distinct episodes.** 1 — EP01-the-lineage-of-a-lost-argument
**First seen.** 2026-05-18T18:06:43Z
**Last seen.** 2026-05-18T18:06:43Z
**Severity carried.** P1
**Check id.** `J2`
**Producer:** `scripts/podcast/learn_propose.py` v1.2

## Sample excerpts

- `Abu Hatim Ahmad ibn Hamdan al-Razi as section sub-header after first mention`
- `Abu Ya qub Ishaq al-Sijistani as section sub-header after first mention`
- `Hamid al-Din Ahmad ibn Abdullah al-Kirmani as section sub-header after first mention`

## Candidate rule

_Author drafts the rule text here. Suggested shape: add the offending phrase / pattern to the canonical list named in 'Target file(s)' so future runs of the challenger or audit catch it deterministically. If `J2` is empirical-only (transcript-level), consider whether a framing-side directive can prevent it at generation time._

## Target file(s)

- content/podcast/.skill/handbook/notebooklm-source-chapter-rules.md (R-NAMES) + content/_shared/arabic/05-name-alias-policy.md

## Fixture

Add to `_learning/fixtures/J2/`:
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
