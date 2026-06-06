# Podcast Challenger Report

**Book:** journey-to-the-west-vol-1
**Run:** 2026-06-06 (challenger v2.4)
**Scope:** per-chapter birth-of-the-stone-monkey (EP01)
**Content profile:** fiction (detected from `_system/series-config.yaml`)
**Iterations:** 1 of 5 max (intelligent break — see Convergence summary)
**Verdict:** SHIP-WITH-CAUTION

## Profile gating

Profile `fiction` skips Categories T (doctrinal), A (Islamic citations), C (Arabic phonetic coverage), J (Arabic name aliasing). All structural / steering / literalness categories ran.

## Convergence summary

Iteration 1 found that all eight P1 findings from the prior pass have already been applied to `00-framing.md` (lines 11–19, 31, 63–64, 74). Word count grew from 662 → 889 words. No new P0/P1 issues surfaced on re-scan. Convergence loop short-circuits on the intelligent-break rule (Section 4 step 6b): zero auto-fixes applied this pass AND zero new framing-side findings vs. iteration 0.

One downstream artifact remains stale: `episodes/EP01-birth-of-the-stone-monkey.txt` is still 662 words (pre-fix) and needs `build_episode_txt.py` re-run to pick up the new clauses. This is the only remaining open item and is recorded as P1 finding **REBUILD-EP01** below.

## Auto-fixes applied

None this pass (read-only audit; framing edits were applied prior to invocation and are now reflected on disk).

## P0 findings

None.

## P1 findings (1)

| ID | File | Issue | Suggested fix |
|---|---|---|---|
| REBUILD-EP01 | episodes/EP01-birth-of-the-stone-monkey.txt | Stale customize-prompt artifact — current file (662 words) does not reflect the eight P1 clauses now in `00-framing.md` (889 words). NotebookLM will receive the old framing without R-NOINTERRUPT, R-NOREPEAT, R-NOBACKGROUND, R-SURPRISE-MOVE, R-RESET, R-CADENCE, R-NOFORMAL, and the named filler-vocabulary clause. | Run `python3 scripts/podcast/build_episode_txt.py content/Fiction/journey-to-the-west-vol-1 EP01-birth-of-the-stone-monkey` to regenerate. Deterministic; no LLM spend. (Sandbox blocked the agent from running this in-pass.) |

## P2 advisories (2 — carried, unchanged from prior pass)

| ID | File | Issue |
|---|---|---|
| V1 / V3 | ch01-birth-of-the-stone-monkey.txt | Faithful-narrative adaptation of pre-modern source carries no rhetorical-question opening hook and no explicit modern-relevance signal. Profile-conscious soften: contract `angle: faithful_narrative` makes this by-design. The framing's closing reflective question (line 67) carries the listener-engagement work instead. No edit recommended. |
| E4 / U1 | ch01-birth-of-the-stone-monkey.txt:342 | The word "exactly" appears in verbatim Patriarch Subodhi dialogue ("which fits exactly the root meaning of the newborn babe"). Source-rhetoric preservation rule applies (contract `tone_constraints`). Not a host-filler hit. |

## Category sweep

| Category | Status | P0 | P1 | P2 |
|---|---|---|---|---|
| A — Islamic citations | skipped (fiction) | 0 | 0 | 0 |
| B — meta-prose tells | clean | 0 | 0 | 0 |
| C — Arabic phonetics | skipped (fiction) | 0 | 0 | 0 |
| D — enrichment depth | clean (faithful narrative; single source) | 0 | 0 | 0 |
| E — articulation/shape | clean | 0 | 0 | 1 (source dialogue) |
| F — framing structure | clean (Opening / Three-part focus / Pronunciation / Host dynamic / Anti-noise / Do not all present) | 0 | 0 | 0 |
| G — Extract Mode contracts | clean | 0 | 0 | 0 |
| H — welcome / landing | clean (H1 line 5; H3 line 67) | 0 | 0 | 0 |
| I — anti-repetition / background | clean (lines 63–64 carry R-NOREPEAT, R-NOBACKGROUND) | 0 | 0 | 0 |
| J — Arabic name aliasing | skipped (fiction) | 0 | 0 | 0 |
| K — interruption / filler | clean (lines 11, 13 carry R-NOINTERRUPT + filler vocabulary) | 0 | 0 | 0 |
| M — modernize / surprise DENY | clean (lines 71–72 carry both blocks) | 0 | 0 | 0 |
| N — phonetic-as-content | clean (0 inline parens in chapter; framing in imperative `- term: phonetic` form per locked rule; N4 guard line 78) | 0 | 0 | 0 |
| O — honorifics / abbreviation | n/a (no Islamic honorifics; no abbreviated work titles) | 0 | 0 | 0 |
| P — debate format | n/a (`episode_format=narrative`) | 0 | 0 | 0 |
| Q — host role parity | clean (storyteller / curious_listener pair; voice gender declared line 9) | 0 | 0 | 0 |
| R — conversation choreography | clean (line 15 R-SURPRISE-MOVE; line 17 R-RESET; line 19 R-CADENCE; line 74 R-NOFORMAL) | 0 | 0 | 0 |
| S — safety / boundary | clean (no concurrent orchestrator; no journal-library write paths) | 0 | 0 | 0 |
| T — doctrinal | skipped (no Islamic pack for fiction — T-NO-PACK info) | 0 | 0 | 0 |
| U — scholarly-conversation rubric | clean (no AI-cliché, no faux-profundity, no premature-closure, no deep-dive self-ref) | 0 | 0 | 0 |
| V — interest / engagement | softened for faithful-narrative | 0 | 0 | 1 |
| W — augmentation | n/a (no augmentation ledger for this episode) | 0 | 0 | 0 |
| CS — chapter-set | deferred (per-chapter scope) | 0 | 0 | 0 |
| Downstream artifact sync | **stale episode.txt** | 0 | 1 | 0 |
| **Total** | | **0** | **1** | **2** |

## Health metrics

| File | Words | Lines |
|---|---|---|
| ch01-birth-of-the-stone-monkey.txt | 7,704 | 360 |
| 00-framing.md (current) | 889 | 79 |
| EP01-birth-of-the-stone-monkey.txt (stale) | 662 | 66 |

- **Chapter word band:** within hard [500, 12000] and soft [1000, 11000] for extended-tier. No E1 violation.
- **Framing word band:** within [150, 3700]. No E1 violation.
- **Em-dashes in chapter:** 43. **B5 not enforced for narrative fiction** — em-dashes sit inside source-verbatim rhapsodies and Patriarch dialogue. Per contract `tone_constraints` ("Source-rhetoric must survive verbatim"), replacing em-dashes would damage source voice. Recorded for telemetry; not flagged.
- **Inline phonetic parens in chapter:** 0 (N1 clean).
- **`Pronounce "X" as "Y"` violations in framing:** 0 (R-PRONUNCIATION-DOUBLE clean — uses `- term: phonetic` with say-ONCE instruction).
- **Cross-episode references:** 0 (B2 clean).
- **Meta-prose tells:** 0 (B1 clean).
- **Modernization-DENY hits outside Do-not block:** 0.
- **Surprise-noise-DENY hits outside Do-not block:** 0.
- **HTML comments in chapter:** 0.

## Caller next step

Run the deterministic rebuild to clear the only remaining P1:

```
python3 scripts/podcast/build_episode_txt.py content/Fiction/journey-to-the-west-vol-1 EP01-birth-of-the-stone-monkey
```

After that single command, verdict promotes to SHIP-READY. No further LLM spend, no authoring judgment required.
