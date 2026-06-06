# Podcast Challenger Report

**Book:** journey-to-the-west-vol-1
**Run:** 2026-06-06 (re-run, challenger v2.4)
**Scope:** per-chapter four-seas-bow-in-submission (EP03)
**Content profile:** fiction (detected from `_system/series-config.yaml`)
**Iterations:** 1 of 5 max (intelligent break — no auto-fixes applied; flag-only findings; identical to prior pass)
**Verdict:** SHIP-WITH-CAUTION

## Profile gating

Profile `fiction` skips Categories T (doctrinal), A (Islamic citations), C (Arabic phonetic coverage), J (Arabic name aliasing), O (Islamic honorifics). All structural / steering / literalness / interest / scholarly-conversation categories ran.

## Convergence summary

Iteration 1: read chapter (7,798 words), framing source (714 words / 4,510 raw chars), contract (`episode_format: narrative`, `length_target: extended`, `angle: faithful_narrative`), and the rendered `episodes/EP03-...txt` (706 words / 4,456 chars — built clean, binding gate is the cleaned form against `FRAMING_CHAR_MAX = 4500`). 44 chars of headroom on the gate; framing source has drifted up 18 chars from the prior 4,492 measurement.

Deterministic scans ran clean for the high-severity gates:

- No cross-episode refs, EP\d\d patterns, "previous/next/earlier episode".
- No `[VERIFY CITATION]` / `[CONTEXT NEEDED]` / TKTK markers.
- No legacy `Pronounce "X" as "Y"` (R-PRONUNCIATION-DOUBLE).
- No inline phonetic parens (R-PHONETICS-OUT).
- No banned modernization vocabulary, no surprise-noise vocabulary, no formal-essay transitions in narrative bodies (matches inside the framing's own `## Do not` block are rule statements, not violations).
- No AI-cliché openings, no faux-profundity rhetorical-question opener, no "deep dive" self-reference.
- No Arabic honorifics (correct for fiction).
- No invented dialogue / fictionalized scenes — narrative is faithful Anthony Yu / W.J.F. Jenner-school rendering of Wu Cheng'en chapter 3.
- Welcome clause present (H1), reflective closing question present (H3), no-read-aloud guard present (N4), Name discipline block present (J1 equivalent for fiction with character-label rules), three governing analogies + verbatim-source list (Anti-noise R1/R3 equivalents).
- 15 movement headings with clear arc (arming → cudgel/armor → registers/amnesty), one-sentence summarizable (E2/E3 PASS).

Two P1 findings remain — both are architectural ceiling issues, not content issues. Convergence loop short-circuits on the intelligent-break rule: zero auto-fixes applied, all findings are flag-only authoring decisions.

## Auto-fixes applied

None this pass. All findings below are author/architect decisions that the challenger does not mechanically resolve.

## P0 findings

None.

## P1 findings (2)

| ID | File | Issue | Suggested fix |
|---|---|---|---|
| CHAR-CEILING | `episodes/EP03-four-seas-bow-in-submission.txt` | Framing builds to **4,456 chars** (cleaned form) against the binding `FRAMING_CHAR_MAX = 4500` (NotebookLM Customize-box hard ceiling). Only 44 chars of headroom on the gate; the framing source itself is 4,510 raw chars (grew 18 chars from prior 4,492 measurement). NotebookLM silently truncates at ~5,000 chars, discarding name-discipline and `## Do not` tail content. The no-read-aloud guard at the bottom sits near the truncation risk zone. | Trim ~150–300 chars from the framing. The audience-detail in the contract `audience:` field already carries the listener orientation; the framing's Opening directive can compress the welcome sentence (drop "the sixteenth-century Chinese novel —" since the source is uploaded as the SOURCE) and Three-part focus item 2 can drop the second mention of "land the spine verbatim a second time" / item 3 "third time" by stating the rule once at the head of Three-part focus. Target ~4,200 chars for safe headroom. |
| HOST-DISCIPLINE-LITE | `_system/episode-drafts/EP03-four-seas-bow-in-submission/00-framing.md` | Host dynamic block names roles cleanly (storyteller + curious_listener, John/Hannah) and forbids bare affirmations, but does not name the canonical R-NOINTERRUPT vocabulary ("yeah", "right", "exactly") nor the cadence directive (R-CADENCE: short-to-medium sentence rhythm). Fiction-narrative profile is more permissive than Islamic-scholarly here, but Loop K2 + R3 still apply. | Add one line to Host dynamic: "No bare affirmations: never open a turn with 'yeah', 'right', or 'exactly'." And one line to Tone: "Sentence cadence is short-to-medium — thinking out loud, not reading an essay." Both lines together add ~120 chars — combined with the CHAR-CEILING trim above, the net stays under 4,400. |

## P2 advisory findings (2)

| ID | File | Issue | Note |
|---|---|---|---|
| B5-NARRATIVE-EMDASH | `chapters/ch03-four-seas-bow-in-submission.txt` | Chapter prose uses em-dashes pervasively (~30+ occurrences) for classical-narrative cadence and parenthetical asides (e.g., "the rod the Great Yu used in taming the floods — a black-iron pillar bound in gold that shrinks and grows at his thought, the As-You-Will Gold-Banded Cudgel"). | Carried, not auto-fixed. B5 was authored for Arabic-scholarly chapters where em-dashes disrupt NotebookLM prosody. Faithful-narrative fiction with `content_profile: fiction` reads em-dashes as legitimate rhetorical pacing — the same dashes appear in the published English translations of *Xī Yóu Jì*. Wholesale comma-substitution would damage source-faithful cadence. Carry until a fiction-profile B5 relaxation is formally landed in `_rules.py`. |
| V1-FAITHFUL-NARRATIVE-NO-HOOK | `chapters/ch03-four-seas-bow-in-submission.txt` | Category V V1 (curiosity-building opening hook — rhetorical question or "Imagine that…" within first 20%). Chapter opens with the contract-mandated italic chapter-summary block, then "Now, the Handsome Monkey King had returned in glory to his native mountain." — classical narrative omniscient-third opener, no rhetorical question. | Carried by-design per `contract.angle: faithful_narrative` + Category U U2 anti-faux-profundity (rhetorical-question openings are explicitly forbidden in this profile). The framing's reflective close (line 52) carries the curiosity payload at the end instead of the head, which is appropriate for narrative shape. |

## Health metrics

| File | Words | Chars | Notes |
|---|---|---|---|
| `chapters/ch03-four-seas-bow-in-submission.txt` | 7,798 | — | Inside hard band (500–12,000) and inside soft band (1,000–11,000). 15 movement headings. Episode-density ceiling for narrative is 9,500 — episode is comfortably below. |
| `_system/episode-drafts/EP03-.../00-framing.md` | 714 | 4,510 raw | Word count fine (150–3,700); raw source 10 chars over the 4,500 ceiling but build script measures the cleaned form. |
| `episodes/EP03-four-seas-bow-in-submission.txt` | 706 | 4,456 | Built clean from `00-framing.md`. **44 chars under the 4,500 NotebookLM hard ceiling** — see CHAR-CEILING finding. |

## Contract integrity (Category G)

| Check | Status | Note |
|---|---|---|
| G1 (contract exists, slug parity) | PASS | `chapter-contracts/four-seas-bow-in-submission.yml` present; slug matches chapter. |
| G2 (contract validates) | PASS (inferred) | Required fields present: `chapter_ref`, `slug`, `source_type`, `source_chapter_ref`, `title`, `audience`, `angle: faithful_narrative`, `episode_format: narrative`, `essential: core`, `length_target: extended`, `host_dynamic`, `key_tensions` (6), `tone_constraints` (5), `anchor_passages` (12), `show_notes`. Build script unavailable to run directly in this sandbox. |
| G3 (contract meta-prose lint) | PASS | No EP\d\d references, no "next/previous episode", no Phase 0a–e leaks. Title field clean. |
| G4 (derived_from lineage) | N/A | Not a derivative contract. |

## Convergence loop trace

| Iter | P0 | P1 | P2 | Auto-fixes | Action |
|---|---|---|---|---|---|
| 1 | 0 | 2 | 2 | 0 | Re-read three files, ran 26 in-scope check categories deterministically, no fixes applied (all findings require author judgment or architectural decisions). Intelligent break: zero auto-fixes + identical findings vs prior pass → halt. |

