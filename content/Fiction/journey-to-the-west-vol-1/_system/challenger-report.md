# Podcast Challenger Report

**Book:** journey-to-the-west-vol-1
**Run:** 2026-06-06 (challenger v2.4)
**Scope:** per-chapter birth-of-the-stone-monkey (EP01)
**Content profile:** fiction (detected from `_system/series-config.yaml`)
**Iterations:** 1 of 5 max
**Verdict:** SHIP-WITH-CAUTION

## Profile gating

Profile `fiction` skips Categories T (doctrinal), A (Islamic citations), C (Arabic phonetic coverage), J (Arabic name aliasing). All structural / steering / literalness categories ran.

## Auto-fixes applied

None this pass (read-only audit).

## P0 findings

None.

## P1 findings (8)

| ID | File | Issue | Suggested fix |
|---|---|---|---|
| K1 | 00-framing.md (Host dynamic) | No interruption-avoidance clause (R-NOINTERRUPT) | Append to Host dynamic: "Conversation discipline: each host completes a thought before the other speaks. No mid-sentence interjections, no talking over. Patriarch / Gibbon voicings run to natural end before the curious listener responds." |
| K2 | 00-framing.md (Host dynamic) | Filler vocabulary not named in Host dynamic | Add: "Host B never opens a turn with bare affirmations (yeah, right, exactly); she pauses, thinks, or rephrases before asking." |
| I1 | 00-framing.md (Anti-noise) | No anti-repetition clause (R-NOREPEAT) | Add: "Do not restate the same thesis more than twice. Quote source verbatim once per turn; paraphrase on second mention." |
| I2 | 00-framing.md | No-irrelevant-background clause missing (R-NOBACKGROUND) | Add to Anti-noise: "Stay on main content. Biographical / historical context (Ming dynasty, Wu Cheng'en's life, Buddhist-Daoist syncretism) admitted at most once and only when a specific passage requires it." |
| R1 | 00-framing.md (Host dynamic) | Plant-surprise / separate-prep illusion clause missing (R-SURPRISE-MOVE) | Add: "Plant at least one moment where Host B introduces a passage Host A has not led toward — e.g., she raises *In the mountains there is no calendar* before he gestures at it." |
| R2 | 00-framing.md (Three-part focus / Pacing) | Reset clause missing for the 9-movement walk (R-RESET) | Add: "Around the banquet-tears moment, Host A takes a single sentence to reset where we are: 'So we've had cosmology, then the stone, then the cave-kingdom, and now — three hundred years in — the king weeps.'" |
| R3 | 00-framing.md (Tone constraints) | Cadence directive missing (R-CADENCE) | Add: "Cadence is short to medium. The storyteller runs longer sentences in source verbatim passages; the curious listener stays in short, thinking-out-loud sentences." |
| R4 | 00-framing.md (Do not) | Formal-essay transitions not in DENY block (R-NOFORMAL) | Add bullet: "Formal-essay transitions: Firstly, Secondly, Furthermore, In conclusion, Moving on to, To summarize, Lastly. The hosts speak, they do not write essays." |

All eight P1s are deterministic framing-side insertions per Section 3 auto-fix policy (parent sections all exist). A subsequent challenger pass with write access can clear them in one iteration; this pass surfaces only.

## P2 advisories (2)

| ID | File | Issue |
|---|---|---|
| V1 / V3 | ch01-birth-of-the-stone-monkey.txt | Faithful-narrative adaptation of pre-modern source carries no rhetorical-question opening hook and no explicit modern-relevance signal. Profile-conscious soften: contract `angle: faithful_narrative` makes this by-design. The framing's closing reflective question (line 55) carries the listener-engagement work instead. No edit recommended. |
| E4 / U1 | ch01-birth-of-the-stone-monkey.txt:342 | The word "exactly" appears in verbatim Patriarch Subodhi dialogue ("which fits exactly the root meaning of the newborn babe"). Source-rhetoric preservation rule applies (contract tone_constraints). Not a host-filler hit. |

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
| H — welcome / landing | clean (H1 line 5; H3 line 55) | 0 | 0 | 0 |
| I — anti-repetition / background | I1, I2 | 0 | 2 | 0 |
| J — Arabic name aliasing | skipped (fiction) | 0 | 0 | 0 |
| K — interruption / filler | K1, K2 | 0 | 2 | 0 |
| M — modernize / surprise DENY | clean (lines 59–60) | 0 | 0 | 0 |
| N — phonetic-as-content | clean (chapter 0 inline parens; framing imperative bullet form; N4 guard line 65) | 0 | 0 | 0 |
| O — honorifics / abbreviation | n/a (no Islamic honorifics; no abbreviated work titles) | 0 | 0 | 0 |
| P — debate format | n/a (episode_format=narrative) | 0 | 0 | 0 |
| Q — host role parity | clean (storyteller / curious_listener pair; voice gender declared line 9) | 0 | 0 | 0 |
| R — conversation choreography | R1, R2, R3, R4 | 0 | 4 | 0 |
| S — safety / boundary | clean (no concurrent orchestrator interfering with this read-only pass; no journal-library write paths in chapter or framing) | 0 | 0 | 0 |
| T — doctrinal | skipped (no Islamic pack for fiction — T-NO-PACK info) | 0 | 0 | 0 |
| U — scholarly-conversation rubric | clean (no AI-cliché, no faux-profundity, no premature-closure, no deep-dive self-ref) | 0 | 0 | 0 |
| V — interest / engagement | softened for faithful-narrative | 0 | 0 | 1 |
| W — augmentation | n/a (no augmentation ledger for this episode) | 0 | 0 | 0 |
| CS — chapter-set | deferred (per-chapter scope; CS is book-scope) | 0 | 0 | 0 |
| **Total** | | **0** | **8** | **2** |

## Health metrics

| File | Words | Lines |
|---|---|---|
| ch01-birth-of-the-stone-monkey.txt | 7,704 | 360 |
| 00-framing.md | 662 | 66 |
| EP01-birth-of-the-stone-monkey.txt | 662 | 66 |

- **Chapter word band:** within hard [500, 12000] and soft [1000, 11000] for extended-tier. No E1 violation.
- **Framing word band:** within [150, 3700]. No E1 violation.
- **Em-dashes in chapter:** 43. **B5 not enforced for narrative fiction** because em-dashes sit inside source-verbatim rhapsodies, Patriarch dialogue, and the closing couplet. Per contract `tone_constraints` ("Source-rhetoric must survive verbatim"), replacing em-dashes would damage source voice. Recorded for telemetry; not flagged.
- **Inline phonetic parens in chapter:** 0 (N1 clean).
- **Cross-episode references:** 0 (B2 clean).
- **Meta-prose tells:** 0 (B1 clean).
- **Modernization-DENY hits in either file:** 0.
- **Surprise-noise-DENY hits in either file:** 0.
- **HTML comments in chapter:** 0.

## Caller next step

Two paths:

1. **Ship now at SHIP-WITH-CAUTION.** None of the eight P1s introduce a doctrinal, citation, or factual defect; they harden NotebookLM steering. The first-pass long-form fiction episode will work; transcripts will likely reveal which clauses NotebookLM most needed.
2. **Apply the eight deterministic P1 insertions to `00-framing.md`, then re-run `python3 scripts/podcast/build_episode_txt.py` to refresh `episodes/EP01-birth-of-the-stone-monkey.txt`.** A subsequent challenger pass with write access closes the loop in one iteration.

Either path is reasonable. For a first-of-series episode that anchors the protagonist for 33 chapters, option 2 captures more value at minimal cost.
