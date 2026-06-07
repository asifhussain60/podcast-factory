# Podcast Challenger Report

**Book:** journey-to-the-west-vol-1
**Run:** 2026-06-06 (challenger v2.4)
**Scope:** per-chapter the-secret-word-at-the-third-watch (EP02)
**Content profile:** fiction (detected from `_system/series-config.yaml`)
**Iterations:** 1 of 5 max (intelligent break — zero auto-fixes; flag-only findings identical to sibling EP01/EP03/EP04/EP05 patterns)
**Verdict:** SHIP-WITH-CAUTION

## Profile gating

Profile `fiction` skips Categories T (doctrinal), A (Islamic citations), C (Arabic phonetic coverage), J (Arabic name aliasing), O (Islamic honorifics). All structural / steering / literalness / interest / scholarly-conversation categories ran.

## Convergence summary

Iteration 1: read chapter (`ch02-the-secret-word-at-the-third-watch.txt`, 7,621 words), framing source (521 words / 3,343 raw chars), contract (`episode_format: narrative`, `length_target: extended`, `angle: faithful_narrative`, `adaptation_mode: faithful`), and the rendered `episodes/EP02-...txt` (3,343 chars — built clean from framing). 1,157 chars of headroom against `FRAMING_CHAR_MAX = 4500` (NotebookLM Customize-box hard ceiling).

S1 async-safety: no concurrent orchestrator / build / extract / claude-p processes detected on this book.

Deterministic scans ran clean for the high-severity gates:

- No cross-episode refs, `EP\d\d` patterns, or "previous/earlier episode" tells in the chapter body.
- No `[VERIFY CITATION]` / `[CONTEXT NEEDED]` / TKTK markers.
- No legacy `Pronounce "X" as "Y"` form (R-PRONUNCIATION-DOUBLE) — framing uses canonical `- term: phonetic` bullet form with the anti-doubling instruction at line 21.
- No inline phonetic parens in chapter (R-PHONETICS-OUT).
- No banned modernization vocabulary, no surprise-noise vocabulary, no formal-essay transitions in the chapter body (matches in the framing's `## Do not` block are rule statements, not violations).
- No AI-cliché openings, no faux-profundity rhetorical-question opener, no "deep dive" self-reference.
- No Arabic honorifics (correct for fiction).
- No invented dialogue / fabricated scenes — narrative is faithful Anthony Yu / W.J.F. Jenner-school rendering of Wu Cheng'en chapter 2.
- Welcome clause present (H1 — line 5 opens "Welcome. We're with Wu Cheng'en's *Journey to the West*..."), Name discipline block present (J1-equivalent for fiction at lines 12–17), Pronunciation block in bullet form (lines 19–32), no-read-aloud guard present at line 51 (N4), formal-essay-transition DENY block at line 46 (R4), DENY-modernize + DENY-surprise blocks at lines 44–45 (M1/M2).
- 13 movement headings in the chapter with clear three-act arc (refusal of the four gates → secret formula + cosmology + arsenal → expulsion + first combat back home), one-sentence summarizable (E2/E3 PASS).
- Sibling-parity (Q3): four other EP framings (EP01, EP03, EP04, EP05) declare Host A = scholar/storyteller-male and Host B = seeker/curious-listener-female. EP02's "Host A (male) = scholar/teacher. Host B (female) = seeker/questioner. Roles do not rotate." is consistent with the established book-wide pair.

Two P1 findings remain — both are recurring patterns carried by every sibling chapter in this book, not content issues unique to EP02. Convergence loop short-circuits on the intelligent-break rule: zero auto-fixes applied, all findings are flag-only authoring decisions.

## Auto-fixes applied

None this pass. All findings below are author/architect decisions that the challenger does not mechanically resolve.

## P0 findings

None.

## P1 findings (2)

| ID | File | Issue | Suggested fix |
|---|---|---|---|
| B5-NARRATIVE-EMDASH | `chapters/ch02-the-secret-word-at-the-third-watch.txt` | Chapter prose uses em-dashes pervasively (46 occurrences) for classical-narrative cadence, parenthetical asides, and rhetorical pauses inside the Patriarch's dialogue (e.g., line 175 "the yin-fire. It kindles up from the Bubbling Spring point beneath the soles of your own feet, drives straight up to the Niwan Palace in the crown of the head — reduces the five viscera to ashes...", line 213 "give your body a shake, and leap up — and with one somersault you'll cover a hundred and eight thousand miles"). | Carried, not auto-fixed. B5 was authored for Arabic-scholarly chapters where em-dashes disrupt NotebookLM prosody. Faithful-narrative fiction with `content_profile: fiction` and `adaptation_mode: faithful` reads em-dashes as legitimate rhetorical pacing — the same dashes appear in the published English translations of *Xī Yóu Jì*. Wholesale comma-substitution would damage source-faithful cadence. Carry until a fiction-profile B5 relaxation is formally landed in `_rules.py`. Identical pattern shipped on sibling EP01/EP03/EP04/EP05. |
| HOST-DISCIPLINE-LITE | `_system/episode-drafts/EP02-the-secret-word-at-the-third-watch/00-framing.md` | Host dynamic block (line 10) names roles cleanly ("Host A (male) = scholar/teacher. Host B (female) = seeker/questioner. Roles do not rotate.") but does not name the canonical R-NOINTERRUPT vocabulary ("yeah", "right", "exactly") inside the Host dynamic section, nor a cadence directive (R-CADENCE: short-to-medium sentence rhythm). The DENY-vocabulary appears only inside `## Do not` at line 45. Fiction-narrative profile is more permissive than Islamic-scholarly here, but Loop K2 + R3 still apply. | Add one line to Host dynamic: "No bare affirmations: never open a turn with 'yeah', 'right', or 'exactly'." And one line to a `## Tone` section (or appended to Host dynamic): "Sentence cadence is short-to-medium — thinking out loud, not reading an essay." Both lines add ~120 chars; framing has 1,157 chars of headroom against `FRAMING_CHAR_MAX = 4500`. No CHAR-CEILING risk on EP02 (unlike EP03's ~44-char headroom). |

## P2 advisory findings (2)

| ID | File | Issue | Note |
|---|---|---|---|
| B2-CANONICAL-CHAPTER-CLOSER | `chapters/ch02-the-secret-word-at-the-third-watch.txt:376` | Final line is "But after all, there is no knowing how it will all turn out, nor how his sojourn in this realm will end from first to last. Listen to the explanation in the next chapter." The phrase "in the next chapter" normally trips B2 cross-episode-reference detection. | Carried by-design. This is a verbatim translation of the canonical Ming-dynasty chapter-closer formula (且聽下回分解 / "listen to the explanation in the next round"), which closes every chapter of *Xī Yóu Jì* and is preserved in every published English translation. NotebookLM treats the source as a sealed text; the closer is internal to the source's voice, not a meta-reference to the podcast pipeline. Identical pattern on every sibling chapter; consistent with `adaptation_mode: faithful`. |
| E1-NARRATIVE-LENGTH-OVER-DEFAULT-BAND | `chapters/ch02-the-secret-word-at-the-third-watch.txt` | Chapter is 7,621 words, above the default 1,500–4,500 word band declared in this agent's E1 check but matching the contract's `length_target: extended`. | Carried by-design. All five chapters of this book run 7,184–7,798 words (variance 7.9%, well under CS5's 30% threshold). The `extended` length_target authorizes the broader band; the contract's `essential: core` and the chapter's three-act structure (gate-refusal → formula+cosmology+arsenal → expulsion+first-combat) justify a single episode rather than a two-part split. Identical pattern on every sibling chapter. |

## Health metrics

| File | Words | Chars | Notes |
|---|---|---|---|
| `chapters/ch02-the-secret-word-at-the-third-watch.txt` | 7,621 | — | Inside hard band (500–12,000) and inside `length_target: extended` band. 13 movement headings. |
| `_system/episode-drafts/EP02-.../00-framing.md` | 521 | 3,343 raw | Word count fine (150–3,700); raw source **1,157 chars under** the 4,500 NotebookLM ceiling — comfortable headroom for the two HOST-DISCIPLINE-LITE inserts (~120 chars). |
| `episodes/EP02-the-secret-word-at-the-third-watch.txt` | — | 3,343 | Built clean from `00-framing.md`. Comfortable headroom against `FRAMING_CHAR_MAX = 4500` — no CHAR-CEILING risk on this episode. |

## Chapter-set design (Category CS — book-scope)

| Check | Status | Note |
|---|---|---|
| CS1 (titles unique) | PASS | All five chapter titles distinct: birth-of-the-stone-monkey, the-secret-word-at-the-third-watch, four-seas-bow-in-submission, the-heavenly-stable-and-the-great-sage, the-great-sage-plunders-the-peaches. |
| CS2 (title concise) | PASS | "The Secret Word at the Third Watch" = 35 chars / 7 words (one over the 6-word soft target; advisory only). |
| CS3 (title not generic) | PASS | Title is content-specific, not "Chapter N" / "Untitled". |
| CS4 (length band fit) | PASS | 7,621 words inside `length_target: extended` band; the default-band overflow is captured separately as E1-NARRATIVE-LENGTH-OVER-DEFAULT-BAND advisory. |
| CS5 (set balance) | PASS | Chapter words: 7,704 / 7,621 / 7,798 / 7,314 / 7,184. Variance = (7,798−7,184)/7,798 = 7.9%, well under the 30% threshold. |
| CS6 (no cross-book bleed) | PASS | No canonical names from other books detected. |

## Contract integrity (Category G)

| Check | Status | Note |
|---|---|---|
| G1 (contract exists, slug parity) | PASS | `chapter-contracts/the-secret-word-at-the-third-watch.yml` present; slug matches chapter file slug. |
| G2 (contract validates) | PASS (inferred) | All required fields present: `chapter_ref`, `slug`, `source_type`, `book_slug`, `source_chapter_ref`, `episode_number`, `title`, `audience`, `angle: faithful_narrative`, `episode_format: narrative`, `essential: core`, `length_target: extended`, `host_dynamic`, six `key_tensions`, five `tone_constraints`, twelve `anchor_passages`, `adaptation_mode: faithful`, `thesis_relevance`, `show_notes`. Build script not invoked from this sandbox. |
| G3 (contract meta-prose lint) | PASS | No `EP\d\d` references in YAML payload fields, no "next/previous episode" leak, no Phase 0a–e leaks, no translator-apparatus prefixes. |
| G4 (derived_from lineage) | N/A | Not a derivative contract. |

## Host-role parity (Category Q)

| Check | Status | Note |
|---|---|---|
| Q1 (Host A in scholar pool) | PASS | "scholar/teacher" ∈ HOST_A_ROLES_SCHOLAR. |
| Q2 (Host B in seeker pool) | PASS | "seeker/questioner" ∈ HOST_B_ROLES_SEEKER. |
| Q3 (book-wide parity) | PASS | All five EP framings declare male-scholar / female-seeker; EP02 consistent with EP01, EP03, EP04, EP05. |
| Q4 (voice/gender pairing) | PASS | "Host A (male)" + "Host B (female)" declared explicitly inline. |
| Q5 (transcript empirical) | N/A | No transcript yet — `BOOK_DIR/transcripts/` does not exist (post-NotebookLM-generation step). |

## Convergence loop trace

| Iter | P0 | P1 | P2 | Auto-fixes | Action |
|---|---|---|---|---|---|
| 1 | 0 | 2 | 2 | 0 | Read chapter + framing source + episode txt + contract, ran 26 in-scope check categories deterministically, no fixes applied (all findings require author judgment or carry by-design). Intelligent break: zero auto-fixes + flag-only findings identical to sibling-chapter pattern → halt. |

## PEQ score (estimated)

| Axis | Weight | Score | Notes |
|---|---|---|---|
| Fidelity | 30% (+20% Voice redistribution) | 95 | Faithful translation-tier prose; verbatim source rhetoric preserved per `tone_constraints[1]` (the lecture-platform rhapsody, the four gate-images, the third-watch verse, the Golden-Elixir formula, the Three Calamities catalogue, the Somersault Cloud spell, the homecoming verse, the closing couplet — all intact). |
| Structure | 18% | 92 | Three-act arc; 13 movement headings; one-sentence summarizable. |
| Enrichment | 17% | 88 | Daoist-Buddhist technical vocabulary translated, not glossed away (Three Vehicles, Niwan Palace, Bubbling Spring, Five Phases, jade hare and crow, Heavenly Ladle / Earthly Fiends, Somersault Cloud, Body-Outside-the-Body). |
| Interest | 15% | 82 | Curiosity-building hook present in the opening italic blurb (the riddle-and-secret-summons setup); challenge-defeat arc explicit (four gates refused, then secret formula granted, then first combat won); modern-relevance signal absent (by-design — `adaptation_mode: faithful` forbids modernization per U5); no strawman; rhetorical-question cadence present in the Patriarch's catechetical dialogue. |
| **Total (estimated)** | — | **~91** | **PASS** (≥85). |

## Fixer pass notes (2026-06-06)

- HOST-DISCIPLINE-LITE: ADDRESSED — appended bare-affirmation guard + short-to-medium cadence directive to the Host dynamic block in `00-framing.md`. `build_episode_txt.py` rebuild pending operator approval (bash gated).
- B5-NARRATIVE-EMDASH: CARRIED — author-judgment carry per report; em-dashes preserve faithful-narrative cadence of *Xī Yóu Jì* and match sibling EP01/EP03/EP04/EP05. No edit applied; requires a fiction-profile B5 relaxation in `_rules.py` before any mechanical fix is appropriate.

