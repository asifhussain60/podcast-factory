# Podcast Challenger Report

**Book:** kitab-al-riyad
**Run:** 2026-05-21 12:16 UTC (challenger v2.0)
**Scope:** per-chapter motion-stillness-hyle-and-form
**Iterations:** 1 (of 5 max; intelligent-break at iteration 1 — no auto-fixes applied, P1/P2 findings are non-deterministic authoring decisions)
**Verdict:** SHIP-WITH-CAUTION

---

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| — | — | — | No auto-fixes applied this run. All auto-fixable patterns were absent from chapter and framing; no deterministic fixes needed. |

---

## Findings requiring author resolution

### P0 (blocks ship)

None.

---

### P1 (ship-with-caution)

#### F5: Discussion spine unfilled — all 8 beats are `[LLM-FILL]` placeholders

- **File:** content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP10-motion-stillness-hyle-and-form/04-discussion-spine.md
- **Context:** The `04-discussion-spine.md` scaffold (8 beats) is entirely populated with `[LLM-FILL]` markers. No beat has a substantive key question, tension, anchor passage, or landing note. Per F5, the discussion spine must be well-shaped; a template-only spine signals the hidden steering layer is absent. The framing's Three-part focus covers the territory, but the spine exists as a separate authoring artifact that supports long-form episode coherence.
- **Suggested fix:** Author fills the 8 beats using the 5 `key_tensions` and 10 `anchor_passages` from `chapter-contracts/motion-stillness-hyle-and-form.yml`. Each beat should name: the key question, the tension it surfaces, the anchor passage it anchors to, and a one-sentence landing note. This is an authoring decision; the challenger does not fill discussion spines.

#### N3: `hyle` / `hayle` appear in chapter without a `Pronounce "hyle"` directive in the framing

- **File:** content/podcast/library/books/kitab-al-riyad/chapters/ch10-motion-stillness-hyle-and-form.txt (lines 17, 31, 33, 85, 87, and summary sections)
- **Context:** The English/Greek scholarly transliteration `hyle` (and variant `hayle`) appears multiple times in the chapter, including in verbatim quotations used as key steering passages ("*form and hyle: their existence together is such that neither is separable from the other*"). The framing carries `Pronounce "al-hayula"` and `Pronounce "hayula"` directives but no `Pronounce "hyle"` line. NotebookLM may render `hyle` as "HY-lee" (correct) or as a variant TTS reading. Neither `hyle` nor `hayle` is present in the shared manifest (`content/_shared/arabic/03-arabic-english-manifest.md`) or the book lexicon (`_system/source/text/_phonetics.md`), so auto-fix is not permitted; the author must propose the phonetic.
- **Suggested fix:** (a) Add `Pronounce "hyle" as "HY-lee". Say it as one syllable.` and `Pronounce "hayle" as "HY-lee". Say it as one syllable.` to the framing's `## Pronunciation` block. (b) Optionally add both terms to `_system/source/text/_phonetics.md` for future reuse.

---

### P2 (advisory)

#### C4: `al-nafs` and `al-ruh` retained in Arabic — exemption applies but is undocumented in framing

- **File:** content/podcast/library/books/kitab-al-riyad/chapters/ch10-motion-stillness-hyle-and-form.txt (lines 51, 57, 61, 181 and throughout sub-chapter three)
- **Context:** `al-nafs` and `al-ruh` appear throughout the chapter as the central Arabic technical terms whose synonymy the chapter argues. Per C4, terms in the substitution policy §2 must either be substituted with English or have a documented justification in the framing's pronunciation hooks. The exemption clearly applies (Exception 2: the terms are explicitly contrasted and the chapter's central argument is the synonymy doctrine — substituting "soul" and "spirit" would collapse the terminological precision the chapter is built to settle). The framing's `Pronounce` lines are present but no justification note appears.
- **Suggested fix:** Add one note to the `## Pronunciation` section: "The Arabic terms *al-nafs* and *al-ruh* are retained in Arabic throughout: sub-chapter three's argument IS the synonymy doctrine — substituting 'soul' or 'spirit' would erase the terminological distinction the chapter is settling. Exception 2 of the substitution policy applies."

#### F6: No canonical NotebookLM steering phrases from two-host-framing.md

- **File:** content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP10-motion-stillness-hyle-and-form/00-framing.md
- **Context:** The framing does not use the canonical steering vocabulary from `two-host-framing.md` ("Slow down on...", "Treat X as the central tension...", "End on a question..."). The framing's Three-part focus and Landing sections carry equivalent prose-form steering with strong specificity. Advisory only.
- **Agent note:** No action required; the framing is well-steered. One canonical phrase at the sub-chapter seven hinge ("Treat *al-Islah's* pre-creative creativity as the chapter's P0 hinge — the *tawhid*-refusal lands here or not at all") would benefit future re-runs if steer drift is observed in transcript audits.

---

## Previous-run resolution log

- **A6 (P0, previous run)**: RESOLVED. The chapter at line 141 explicitly marks the cross-tradition parallel: "The same protection is named in a parallel tradition, not as a single shared chain, but as two lineages converging on one tawhid." This is a clear tradition-difference annotation; A6 passes.
- **N3 (P1, previous run)**: RESOLVED. Arabic transliteration lines removed from bilingual blockquotes; English translations with full citations retained. Chapter word count reduced from 8,644 to 8,626 words.
- **F5 (P1, previous run)**: UNRESOLVED. Discussion spine still all `[LLM-FILL]`. Authoring decision required.

---

## Health metrics

| Chapter | Words | Tier diversity | Blockquotes | Phonetic gaps | Em-dashes | Framing words | Verdict |
|---|---|---|---|---|---|---|---|
| ch10-motion-stillness-hyle-and-form | 8,626 | 3 tiers (Quran/Sunni/Ismaili) | 6 | 1 (hyle/hayle) | 0 | 3,351 | SHIP-WITH-CAUTION |

**Chapter tier breakdown:**
- Tier 1 (Quran): 4 verses cited (36:82, 16:40, 112:1–4, 42:11) — Surah name + verse number format; Pickthall named on first citation (line 99)
- Tier 3 (Sunni hadith): 1 hadith (Sahih al-Bukhari, Book 59, Hadith 3191; narrated by Imran ibn Husayn) — correctly cited
- Tier 4 (Ismaili/Shia): 1 (Nahj al-Balagha, Sermon 1) — correctly cited; cross-tradition annotation at line 141

**Enrichment ratio:** ~3% (approx. 300 words in blockquotes out of 8,626 chapter words — well within 60% cap)

**Framing word count:** 3,351 of 3,500 hard cap (95.7% capacity — within band, approaching ceiling)

**Chapter word band:** 8,626 words in Extended tier range (5,500–9,500) per `length_target: extended`; hard cap [500, 10,000]. PASSES.

**Checks that passed cleanly:** A1 (citation discipline — all Quran/hadith/Nahj citations correctly formatted), A2 (no VERIFY CITATION markers, no fabricated numbers), A3 (Pickthall named on first Quranic citation at line 99), A4 (verbatim quote integrity — blockquotes are not paraphrased), A5 (no source-shifting), A6 (cross-tradition annotation at line 141 — RESOLVED), B1 (no HTML comments), B2 (no cross-episode refs), B3 (no file-length self-refs), B4 (no translator-apparatus prefixes), B5 (zero em-dashes), B6 (no invented dialogue), C1 (phonetic coverage — all key chapter Arabic terms have framing Pronounce directives), C2 (lexicon parity), C3 (honorific discipline — each form once per figure), C4 (al-nafs/al-ruh exemption applies; P2 advisory), D1 (enrichment multi-tier — 3 distinct tiers), D2 (enrichment ratio ~3%, well under 60% cap), D3 (citations bound to chapter tensions), D4 (no quote-stacking — no 3+ consecutive blockquotes), D5 (no CONTEXT NEEDED markers), E1 (8,626 words in Extended tier band), E2 (one-sentence summarizability confirmed), E3 (beginning/middle/end arc — hook open at Where this chapter picks up; pressure-build through 9 sub-chapters; settled formula close), E4 (no verbal filler), E5 (no translation-residue awkward phrasings), F1 (framing exists), F2 (four-part structure: opening directive/background/three-part focus/host dynamic/tone/pronunciation/anti-noise/do-not), F3 (audience named concretely at line 30–31 of framing), F4 (5 specific tensions named in framing), H1 (welcome clause present — "Open the episode with a brief welcome"), H2 (summary clause present — "two-to-three sentence summary naming the source"), H3 (closing-landing clause — "Close on the unresolved tension, a question, or a single sharp line. Do not recap"), I1 (anti-repetition clause — "Do not restate the central thesis more than twice"), I2 (no-irrelevant-background clause — "Stay on the source's main content"), I3 (no adjacent-movement thesis repetition in chapter), I4 (biographical material bounded — minimal, only when argument-bearing), J1 (name discipline block in framing with 6 aliases), J2 (alias applied after first mention), J3 (alias spellings match manifest phonetics), K1 (interruption-avoidance — Conversation discipline block), K2 (filler vocabulary named: yeah/right/exactly), M1 (DENY-modernize block with full platform list), M2 (DENY-surprise block plus positive companion), N1 (zero inline phonetic parens in chapter), N2 (Pronunciation block fully in imperative form — 45 Pronounce lines), N4 (no-read-aloud guard at framing lines 141 and 169), O1 (honorific count: one each), O2 (no abbreviated work titles — framing explicitly bans "the Nahj"), R1 (conversation choreography — planted-passage example present), R2 (reset clause present; spine 8 beats > 5 threshold), R3 (cadence directive in Tone section), R4 (formal-transition DENY in Do not section), R5 (analogy-permission paragraph alongside DENY list), S1 (async-safety: ts_updated 51 min old at review time, no live process), S2 (no memoir/shared write paths in chapter or framing), G1 (contract present), G3 (contract passes meta-prose lint; no EP## refs, no Phase-leak tells)

**Checks skipped (no transcript):** M3, M4, N5, O3, R6, R7

**Category P:** `episode_format: deep_dive` — debate checks skipped.

**Category Q:** Book-scope only; not run in per-chapter invocation.

---

## S1 async-safety note

`orchestrator-state.json` shows `phase_status: "running"` for the `per-chapter` phase, `ts_updated: 2026-05-21T11:24:27Z`. No live orchestrator process found via `pgrep`. Stale running state is consistent with the known orchestrator resume bug (documented in the state file's `reset_note`). Delta from `ts_updated` to review time is ~51 minutes — outside the 5-minute S1 halt window. Challenger proceeded.

---

## Score

**P0:** 0 | **P1:** 2 | **P2:** 2 | **Chapters in scope:** 1 | **Auto-fixes:** 0

`penalty = (0×1.0 + 2×0.2 + 2×0.05) / 1 = 0.50`
`score = max(0.0, 1.0 − 0.50) = 0.50 (Drifting)`

