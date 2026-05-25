# Pipeline debt — framework gaps observed in flight, queued for fix

Tracks framework-level gaps in the podcast pipeline that today's per-book operator runs have surfaced. Each entry is a fix that lives in the pipeline code/prompts/rules — NOT in any single book's content. When a fix lands, it benefits every future book the pipeline processes (Raahat al-Aqal, Kitab Maqbas, Rasail Ikhwan AsSafa, etc.) automatically.

Both Air and Studio sessions write to this file (multi-writer, per `operators/coordination-protocol.md §14`). Add new items at the bottom of the relevant section. Use F-prefix IDs (F1, F2, ...) for framework debt items so they don't collide with X-prefix runtime fixes that are already-shipped code patches.

---

## Refactored synthesis view — as of 2026-05-23

**Reconciliation 2026-05-23 (Air):** F27 paste and v4-revised propagation actually LANDED in commits
`3631bc0` (F27 7-of-8 validators) and `23009eb` (v4-revised doctrine in `_authoring.py` Phase 0e + 0g
prompts). The synthesis view below was last refreshed pre-landing; closing items updated accordingly.
Genuine remaining P0 framework work is now narrower than the older view suggested.

---

## Refactored synthesis view — as of 2026-05-22

**Holistic snapshot** of F1-F29 after KaR's 3-round audio audit (v1/v3/v4-revised). The original table at the bottom of this file is preserved chronologically; this top section is the canonical operational view going forward.

### Doctrine status — what's empirically locked

| Doctrine | F-items | Audio audits validating | Status |
|---|---|---|---|
| **F20** — zero Arabic person/book/concept names in audio | F14, F18, F19, F20 | v3, v4, v4-revised | 🟢 **LOCKED** (3 audits, 0 mangling) |
| **F21** — book-wrap convention ("the book *X*") | F21 | v3, v4, v4-revised | 🟢 **LOCKED** (3 audits) |
| **F16** — Episode-number announcement (Episode N, not Chapter N) | F16 | v3, v4, v4-revised | 🟢 **LOCKED** |
| **R-RECURRING-THESIS** — verbatim 3x | F15 (partial) | v3, v4, v4-revised | 🟢 **LOCKED** |
| **R-DRAMATIC-ARC** — 6-beat structure | F15 (partial) | v3, v4, v4-revised | 🟢 **LOCKED** |
| **R-CHALLENGER-FRICTION** — 4 literal pushback patterns | F15 (partial) | v3, v4, v4-revised | 🟢 **LOCKED** |
| **Stable role-labels** (one per figure, proper names where needed) | new in v4-revised | v4-revised | 🟢 **LOCKED** |
| **Mirror-as-source-aligned Beat 2** + source-image carve-out | new in v4-revised | v4-revised | 🟢 **LOCKED** |
| **F22** — 45-60 min length target | F22 | v3=42, v4=42, v4-revised=39 | 🟡 **NOT REACHED** — structural NotebookLM pacing limit; accept ~40-45 as reality |
| **F24** — Alqaab functional-paraphrase | F24 | not yet tested (KaR Ch07 has no novel alqaab) | ⏸ **UNTESTED** — doctrine drafted, awaits empirical test |
| **F29** — Surah names in English meaning | F29 | v4-revised audio caught "Qaf → cough" | 🔴 **DOCTRINE NEW; CHAPTER REWRITES PENDING** |

### Open items grouped by pipeline location (replaces flat F1-F29 list)

| Location | Open item | Priority | Notes |
|---|---|---|---|
| **Phase 0d** | F4 — editorial-intro chapters reach the pipeline | P2 | KaR ch01a dropped manually; F23 is broader fix |
| **Phase 0d** | F23 — no book-thesis coherence check | P1 | NEW from Q1 finding; ~half-day implementation |
| **Phase 0d** | F26 — name-aliases.yml schema v2 | P1 | enables F23/F25 auto-emit per-book |
| **Phase 0e** | F13 — inline phonetic parens leak | P1 | observed only in some chapters; prompt strengthening needed |
| **Phase 0e** | F24 — alqaab functional-paraphrase | P0 | doctrine drafted; prompt patch pending |
| **Phase 0e** | F29 — Arabic surah names in chapter prose | P0 | doctrine drafted; chapter rewrite needed for KaR + Phase 0e prompt patch |
| **Phase 0g** | F17 — R-ANALOGY-CAP under-enforced | P0 | M1 confirmed 3x; needs validator-twin (F27) |
| **Phase 0g + handbook** | v4-revised propagation | P0 | stable-role labels + source-image carve-out + bounded honorifics + literal pushback patterns + 6 prompt updates pending in `_authoring.py:author_framing()` |
| **build_episode_txt.py** | F27 — Tier 2.5 validator burst (8 functions) | P0 | drafts ready in `f27-validator-drafts.md`; paste pending |
| **build_episode_txt.py** | F25 — show-notes apparatus-table schema | P0 | validator + Phase 0g format change |
| **Orchestrator** | F11 — iter-1-ships + iter-2-timeout = false-failure | P1 | observed 4+ times in KaR; needs heartbeat-age check |
| **Orchestrator** | F12 — episode IDs from filename digits | P1 | gaps after chapter drops; KaR has missing EP01, EP02 (ch01a/ch02b dropped) |
| **Orchestrator** | F7 — no cost projection | P2 | low impact; nice-to-have |
| **Validator regex** | F9 — R-PHONETICS-OUT remaining patterns audit | P2 | pattern #1 fixed; rest untested |
| **Ops** | F28 — backward-compat decision | DECIDED | Asif: re-emit all KaR episodes under v4-revised doctrine |

### Closed / validated (lessons that are now framework default)

| Item | What's now framework | When closed |
|---|---|---|
| F1 — word caps | X10 prompt self-check | 2026-05-21 |
| F3 — manuscript-meta | X14 R-NO-MANUSCRIPT-META | 2026-05-21 (validated empirically in v3+v4 transcripts) |
| F5 — honorific dedup | X14 strengthened Phase 0e | 2026-05-21 |
| F6 — datetime.UTC | X13 datetime.timezone.utc | 2026-05-21 |
| F8 — orphan episode-drafts | X13 _sweep_orphan_episode_drafts | 2026-05-21 |
| F10 — word-band tolerance | X6 + X13 ceilings raised | 2026-05-21 |
| F14, F18, F19 | SUPERSEDED by F20 (total removal works) | 2026-05-21 |
| F15 | X16 (R-DRAMATIC-ARC + R-CHALLENGER-FRICTION + R-ANALOGY-CAP + R-RECURRING-THESIS) — validated in v4-revised | 2026-05-21 |
| F2 | X10 grep-first prompt — low-impact validation pending | 2026-05-21 |

### Priority order — what to land next (operational sequence)

This sequence is what unlocks shipping new books under v4-revised doctrine.
**2026-05-23 update**: items 1, 2, 5-prompt, 6-validator, 7, 16 have all landed in code; remaining ladder is shorter than originally drafted.

1. ~~**F27** (8 validators in `build_episode_txt.py`) — P0; the M1 fix; drafts ready~~ → **7-of-8 LANDED 2026-05-22** (commit `3631bc0`). #8 apparatus-table validator pending F25 (no show-notes target to validate yet).
2. ~~**v4-revised propagation** to `_authoring.py` + handbook — P0; 6 prompt updates; drafts ready~~ → **LANDED 2026-05-22** (commit `23009eb`). Verified: R-HONORIFIC-ONCE bounded (L1055/1352), R-SURAH-ENGLISH-ONLY (L1095/1363), R-STABLE-ROLE-LABELS (L1260), R-CHALLENGER-FRICTION-LITERAL (L1310). Handbook canonical updates verified separately.
3. **F25** (apparatus-table schema + show-notes generation in Phase 0g + Validator #8 wiring) — P0; **multi-part feature**, not a single paste. Requires: schema definition (Original/Transliteration, Category, Written Form, Audio Label, First Audio Use columns), Phase 0g sub-step to emit `99-show-notes.md`, then the validator. ~1-day implementation.
4. **F26** (name-aliases.yml schema v2) — P1; enables F23/F25 auto-emit
5. **F29** (Phase 0e surah-name English-meaning rule + chapter rewrite) — **Phase 0e prompt LANDED** (in 23009eb). KaR ch07-ch15 chapter rewrites still pending; deferred since KaR is shipped (low ROI to re-author shipped content). New books inherit clean.
6. **F24** (Phase 0e alqaab functional-paraphrase rule) — **Validator #7 LANDED** (in 3631bc0). Phase 0e prompt patch still pending (currently soft-flag only; not prompt-enforced).
7. ~~**F17** (analogy-cap validator-twin) — covered by F27~~ → **CLOSED** by F27 #3 (commit `3631bc0`).
8. **F23** (Phase 0d.5 book-coherence check) — P1; ~half-day
9. **F11** (iter-1-ship + iter-2-timeout retry semantics) — P1
10. **F12** (episode-id from contract.episode_number) — P1
11. **F13** (Phase 0e inline-phonetics audit) — P1
12. **F4** (editorial-intro chapter detection) — P2; F23 covers this broader
13. **F22** length target — accept as structural limit; framing notes "aspirational"
14. **F9** (remaining R-PHONETICS-OUT patterns) — P2; needs regex audit
15. **F7** (cost projection at resume) — P2
16. ~~**F28** (re-emit KaR under new doctrine) — execution task; in flight~~ → **CLOSED 2026-05-23** by archetype-driven manual finish; KaR shipped ship-with-caution per state.json.

### True remaining P0 framework debt (after 2026-05-23 reconciliation)

| Item | Scope | Effort | Notes |
|---|---|---|---|
| **F25 generation** | Phase 0g show-notes auto-generation (apparatus-table rows from `name-aliases.yml v2`) | ~half-day | Schema landed ([f25-apparatus-table-schema.md](f25-apparatus-table-schema.md)). Validator #8 landed in [build_episode_txt.py](../../scripts/podcast/build_episode_txt.py) — defensive (silent skip when file absent). Generation depends on F26. |
| **F26** | `name-aliases.yml v2` schema (figure → category / written form / audio label / first-use anchor) | ~half-day | Unblocks F25 generation + F23 book-thesis coherence checks. |
| ~~**F24 prompt**~~ | ~~Phase 0e alqaab functional-paraphrase prompt patch~~ | ~~~30 min~~ | **LANDED 2026-05-22** in commit `23009eb` (v4-revised propagation). Verified 2026-05-23 in [_authoring.py:1103-1107](../../scripts/podcast/_authoring.py#L1103-L1107) (Phase 0e) and [_authoring.py:1375-1382](../../scripts/podcast/_authoring.py#L1375-L1382) (Phase 0g). Both sites carry the established-alqaab whitelist + functional-paraphrase patterns + "the Striker/Returner sound like sports nicknames" anti-pattern callout. |

Everything else on the F-list is P1/P2 quality-of-life. The framework can ship the next book under v4-revised doctrine right now; F25 generation + F26 are the remaining compounding investments.

### Cohesion-audit fixes landed 2026-05-23

| Item | Source | Landed in |
|---|---|---|
| **G2** Chapter-set advisory in orchestrator (Phase 0d.5) | [cohesion-audit-2026-05-23.md](cohesion-audit-2026-05-23.md) | `c0ab860` |
| **G3** Async-safety lockfile (`~/.podcast-locks/<slug>.lock`) | Same | `c0ab860` |
| **F25 validator + schema** | [f25-apparatus-table-schema.md](f25-apparatus-table-schema.md) | This commit |

G1 (transcript audit) accepted as honest human-gate; G4 (Category G re-validation) verified as write-once / no real gap; G5 (word-count bands) closed as misreport.

### Meta-pattern status (M1-M7 from original synthesis)

| Meta-pattern | Status |
|---|---|
| M1 — LLM ignores caps without validator | 🔴 **CONFIRMED 5+ times**; F27 is the fix; until landed, this recurs on every chapter |
| M2 — Phase 0e under-disciplined | 🟡 **PARTIAL** — F3/F5 closed; F13/F24/F29 still open |
| M3 — Phase 0d classification weak | 🔴 **OPEN** — F4 + F23 |
| M4 — Orchestrator state-machine rough edges | 🟡 **PARTIAL** — F8 closed; F11/F12 open |
| M5 — Empirical thresholds vs "~" prose | 🟡 **PARTIAL** — F10 fixed for chapter/framing; TOLERANCE_PCT generalization pending |
| M6 — Cost tracking gaps | 🟡 **PARTIAL** — F6 closed; F7 open |
| M7 — Rule-set drift (prose vs regex) | 🔴 **OPEN** — F9 audit pending; F17 + F27 directly tackle |

### Validator coverage gap matrix (the M1 fix surface) — **updated 2026-05-23**

For every R-rule in the handbook, mark whether prompt-side enforcement AND validator-side enforcement exist:

| R-rule | Prompt enforcement | Validator enforcement | Gap |
|---|---|---|---|
| R-NO-ARABIC-NAMES (F20) | X14, X15 ✅ | F27 #1 ✅ (3631bc0) | 🟢 |
| R-BOOK-WRAP (F21) | X14 ✅ | F27 #1 regex ✅ (3631bc0) | 🟢 |
| R-DRAMATIC-ARC | X16 ✅ | Tier 2 validator ✅ | 🟢 |
| R-CHALLENGER-FRICTION | X16 ✅ | Tier 2 validator ✅ | 🟢 |
| R-ANALOGY-CAP | X16 ✅ | F27 #3 ✅ (3631bc0) | 🟢 (was M1 source; now closed) |
| R-RECURRING-THESIS | X16 ✅ | Tier 2 validator ✅ | 🟢 |
| R-STABLE-ROLE-LABELS (replaces R-NAMEDISCIPLINE) | v4-revised ✅ (23009eb, L1260) | partial (F26 schema needed for full coverage) | 🟡 |
| R-NOMODERNIZE | X16 ✅ | F27 #4 ✅ (3631bc0) | 🟢 |
| R-HONORIFIC-ONCE (bounded both sides) | v4-revised ✅ (23009eb, L1055/1352) | F27 #5 ✅ (3631bc0) | 🟢 |
| R-SURAH-ENGLISH-ONLY (F29) | v4-revised ✅ (23009eb, L1095/1363) | F27 #6 ✅ (3631bc0) | 🟢 (prompt + validator both landed; KaR rewrites deferred) |
| R-ALQAAB-FUNCTIONAL-PARAPHRASE (F24) | Phase 0e prompt patch pending | F27 #7 ✅ (3631bc0) | 🟡 |
| R-NO-MANUSCRIPT-META | X14 ✅ | Tier 2 validator ✅ | 🟢 |
| R-PHONETICS-OUT | handbook ✅ | regex partial (F9) | 🟡 |
| R-WELCOME (opening sentence) | X16 ✅ | partial | 🟡 |

**Net**: 11 of 14 R-rules have full validator-side coverage (was 7 before F27/v4-revised landed). M1 risk surface reduced to 3 partials: R-STABLE-ROLE-LABELS (awaits F26 name-aliases v2), R-ALQAAB (awaits F24 Phase 0e prompt), R-PHONETICS-OUT (awaits F9 regex audit). **M1 is no longer the dominant risk pattern.**

---

## Lessons learned — meta-patterns across F1–F15

First-read map for new operators. The 15 individual debt items collapse into 7 recurring meta-patterns. Each pattern is what to WATCH FOR in the next book. When a defect surfaces, ask "which Mn does this look like?" — if it matches, the proposed fix shape is already in this file; if it doesn't, you've found M8.

### M1 — LLM ignores explicit caps without self-check OR downstream validator

**Items:** F1 (framing word caps), F2 (unused pronunciation entries), F5 (honorific dedup), F14 (Arabic name repetition), F15 (analogy proliferation + dramatic tension).

**The deeper truth:** The framing-gen / enrichment LLM reads rules but doesn't enforce them. Every cap needs prompt-self-check AND ideally a post-hoc validator gate. Today's X-fixes added self-checks (X10/X14/X15/X16); validator gates remain missing for most rules.

**Triage status:** All 5 items Triaged via prompt-self-check additions. Validator coverage gap is the next framework session priority.

**Watch for:** any new "the LLM produced X over the explicit cap" pattern. Default response: add prompt self-check AND a validator rule simultaneously.

### M2 — Phase 0e enrichment under-disciplined

**Items:** F3 (manuscript-meta), F5 (honorifics in source prose), F13 (inline phonetics in chapter txt), F14 (Arabic name repetition in chapter prose).

**The deeper truth:** Phase 0e emits the chapter source — the file NotebookLM uploads as SOURCE. Every R-rule violation here cascades directly to spoken audio. The Phase 0e prompt is the most leveraged enrichment guard in the entire pipeline.

**Triage status:** Triaged via X14 (R-NO-MANUSCRIPT-META, R-HONORIFIC-ONCE strengthened) + X15 (R-NAMEDISCIPLINE). Empirical verification awaits next book (KaR's chapters were authored before these patches landed).

**Watch for:** any chapter that ships with rule violations only Phase 0e could have introduced (e.g., manuscript-meta paragraphs, repeated honorifics in prose, Arabic-name density). Audit Phase 0e output of the FIRST chapter of the next book carefully.

### M3 — Phase 0d classification heuristics weak

**Items:** F4 (editorial-intro chapters scheduled as episodes), Ch07 host_dynamic mis-assignment (noted under F15's "Related root cause" section).

**The deeper truth:** Phase 0d picks `episode_format` and `host_dynamic` from chapter content without enough empirical structure. Adjudicative chapters get curious_mind+scholar_companion (supportive); editorial intros get full episode contracts. The heuristic needs sharper classification rules.

**Triage status:** Open (F4); Ch07 case documented under F15 but not separately patched.

**Watch for:** any chapter that ships with the WRONG host_dynamic for its rhetorical structure (debate-content with non-debate pairing) OR an editorial intro/foreword that wasn't manually dropped.

### M4 — Orchestrator state-machine has rough edges

**Items:** F8 (stale episode-draft directories), F11 (iter-1 ship + iter-2 timeout treated as chapter failure), F12 (episode IDs from filename digits vs `contract.episode_number`).

**The deeper truth:** Several spots where orchestrator semantics surprise the operator — "tree not clean" blocks after partial writes; "FAILED" verdicts when episodes actually shipped; episode IDs encoding non-listener-facing data. Each individually small; together a fluent-resume gap.

**Triage status:** F8 Triaged (X13 sweep in pre-flight + per-chapter entry). F11 + F12 still Open.

**Watch for:** any resume cycle that requires manual state patching. Each manual patch is a sign this meta-pattern needs another fix.

### M5 — Empirical thresholds vs handbook "~" prose use exact thresholds in code

**Items:** F10 (chapter word band + framing word band).

**The deeper truth:** Handbook says "episodes over ~10,000 words risk…"; code enforced exactly 10,000. Pattern recurs across all soft-with-tolerance limits. Single `TOLERANCE_PCT` constant would generalize the alignment.

**Triage status:** Triaged via X6 (chapter ceiling 10000→10500) + X13 (framing ceiling 3500→3700). Generalization to TOLERANCE_PCT not yet done.

**Watch for:** other "~X" in handbook prose that the code still enforces exactly. Audit on next framework-debt session.

### M6 — Cost tracking + visibility gaps

**Items:** F6 (datetime.UTC silent fail), F7 (no cost projection before multi-task runs).

**The deeper truth:** Operator runs blindly on spend. Cost-ledger was silently failing on Python 3.9 (F6); orchestrator never warned about projected total spend before starting (F7).

**Triage status:** F6 Triaged (X13 datetime.timezone.utc replacement). F7 Open.

**Watch for:** any multi-hour orchestrator run that completes without surfacing a spend tally. F7's fix is to compute `remaining_episodes × per-episode-cost` and surface at resume time.

### M7 — Rule-set drift between prose intent and regex implementation

**Items:** F9 (R-PHONETICS-OUT pattern audit), F13 (other R-rules not yet audited — partially under same heading).

**The deeper truth:** The R-rules are written in English prose (in handbook) AND in regex (in build_episode_txt.py). The two drift apart over time. R-PHONETICS-OUT pattern #1 was over-broad until X5; other patterns may have similar drift.

**Triage status:** F9 Triaged (X5 fixed pattern #1). Full audit of remaining R-rules + unit tests pending.

**Watch for:** any validator false-positive on legitimate content (a sign of over-broad regex) OR a known defect that the validator missed (a sign of under-broad regex).

### How to use this synthesis going forward

When you encounter a NEW defect in a future book, ask first: "which of M1–M7 does this look like?"

- If it matches one of M1–M7: the proposed fix SHAPE is already in this file. Apply the corresponding pattern's fix template; close the new F-item against the existing M.
- If it doesn't match: you've found M8 (or M9, etc.). Add it to this section. Document the meta-truth and the watch-for signal.

When you commit an X-class fix, update the corresponding Mn entry's triage status. When all items under an Mn are Triaged or Closed, mark the meta-pattern **Resolved** with a closing date.

When you author a new R-rule (handbook addition), CHECK whether it can be enforced both prompt-side AND validator-side. Single-enforcement-point rules are exactly the M1 root cause; double-enforcement closes the loop. The next framework session's first task is auditing existing R-rules for validator coverage gaps.

## Active framework debt

| ID | Title | Discovered | Severity | Status | Owner |
|---|---|---|---|---|---|
| F1 | Phase 0g framing-gen LLM ignores hard word-count caps | 2026-05-21 (KaR EP14) | High | Triaged ([X10](https://github.com/asifhussain60/podcast-factory/commit/HEAD) added per-section caps + self-check in author_framing prompt) | — |
| F2 | Phase 0g framing-gen produces unused pronunciation entries | 2026-05-21 (KaR EP14) | Medium | Triaged ([X10](https://github.com/asifhussain60/podcast-factory/commit/HEAD) prompt now requires grep chapter for terms before generating entries) | — |
| F3 | Phase 0e enrichment emits manuscript-history meta-commentary that NotebookLM hosts then vocalize | 2026-05-21 (KaR ch03a et al.) | High | Triaged (X14 added R-NO-MANUSCRIPT-META instruction to Phase 0e prompt with explicit forbidden patterns) | — |
| F4 | Phase 0d chapter design includes editorial-intro chapters that aren't substantive book content | 2026-05-21 (KaR ch01a) | Medium | Open | — |
| F5 | Phase 0e enrichment emits repeated honorifics (glyph + text forms) per chapter; R-HONORIFIC-ONCE flags downstream | 2026-05-21 (KaR ch08/ch09/ch12/ch14b + X8 text forms) | Medium | Triaged (X14 strengthened Phase 0e prompt: enumerates glyph + 5 text forms + requires self-count before return) | — |
| F6 | Cost-ledger silently fails on Python 3.9 due to `datetime.UTC` (3.11+ feature) | 2026-05-21 (KaR Phase 0g) | Medium | Triaged (X13 replaced `datetime.UTC` with `datetime.timezone.utc` in `_cost_ledger._now_iso`) | — |
| F7 | Orchestrator doesn't surface multi-task cost projection before starting long runs | 2026-05-21 (KaR Phase 0g) | Low | Open | — |
| F8 | Stale `episode-drafts/EP*` directories accumulate across X-class fix cycles; no auto-clean on resume | 2026-05-21 (KaR EP14b/EP12/EP04) | Low | Triaged (X13 added _sweep_orphan_episode_drafts() in preflight_resume + _drive_per_chapter_and_after; idempotent removal) | — |
| F9 | R-PHONETICS-OUT pattern #1 was over-broad; suggests rule-set audit for intent/implementation alignment | 2026-05-21 (KaR EP14 first attempt) | Low | Triaged ([X5](https://github.com/asifhussain60/podcast-factory/commit/c9424dd) fixed pattern #1; audit remaining patterns) | — |
| F10 | Word-band rules with "~" prose use exact thresholds in code (no tolerance) | 2026-05-21 (KaR ch12/ch14b at 10180/10112) | Low | Triaged (X6 bumped chapter ceiling 10000→10500; X13 bumped framing ceiling 3500→3700) | — |
| F11 | Iter-1 SHIP verdict + iter-2 challenger timeout treated as chapter failure even though episode already shipped | 2026-05-21 (KaR EP04/EP07/EP08 — all shipped at iter 1, all marked FAILED on iter-2 timeout) | Medium | Open | — |
| F12 | Episode IDs derived from chapter filename digits, not from `contract.episode_number`; gaps in listener-facing numbering after chapter drops | 2026-05-21 (KaR EP04/EP07/EP10/EP12/EP14 with missing EP01-EP02 after ch01a/ch02b drops) | Medium | Open | — |
| F13 | Phase 0e enrichment leaks inline `(pho-net-ic — gloss)` parens into chapter txt despite R-PHONETICS-OUT; observed only in some chapters (ch15) while siblings are clean | 2026-05-21 (KaR ch15 — 18 inline phonetics on terms + 1 on people-name `Abu Hatim al-Razi`) | Medium | Open | — |
| F14 | Chapter prose + framing repeat Arabic names many times per episode; NotebookLM TTS mangles each occurrence into multiple inconsistent garbled forms (one chapter = 8+ variants of `al-Kirmani`); listeners hear pronunciation noise instead of substance | 2026-05-21 (KaR Ch07 audio transcript review) | **High** | Triaged (X15 added per-figure rotation-set discipline to Phase 0g framing-gen prompt + KaR name-aliases.yml; takes effect on next orchestrator launch for remaining 5 chapters) | — |
| F15 | Phase 0g framing-gen produces "two hosts unpacking" dynamic instead of "explainer vs genuine challenger"; over-explanation, premature resolution of central tension, analogy proliferation (14+ analogies in one Ch07 episode) | 2026-05-21 (independent GPT review of KaR Ch07 transcript) | **High** | Triaged (X16 added R-DRAMATIC-ARC + R-CHALLENGER-FRICTION + R-ANALOGY-CAP + R-RECURRING-THESIS to Phase 0g framing-gen prompt; takes effect on next orchestrator launch) | — |
| F16 | Framing's `## Opening directive` announces source-book chapter number ("Chapter Three") but not the podcast episode number ("Episode 7"); listener loses series-position context | 2026-05-21 (KaR Ch07 v2 audio review — listener heard "Chapter 3" and asked why episode 7 was labeled chapter 3) | Medium | Open | — |
| F17 | R-ANALOGY-CAP under-enforced — hosts respected the 3 governing analogies in `## Tone constraints` but ALSO introduced 5+ new analogies mid-episode (cosmic ruler, pitcher+silver cup, Venn diagram, signet ring, radio tower) despite explicit instruction | 2026-05-21 (KaR Ch07 v2 audio review) | Medium | Open | — |
| F18 | Single-Arabic-occurrence per chapter still results in TTS mangling — even one occurrence of `al-Kirmani` per chapter generates 8+ mangled variants in audio (Quraymani, Alcure Mane, al-Khir MNA, etc.). Reduction discipline (F14) is insufficient | 2026-05-21 (KaR Ch07 v2 audio review) | **High** | Open (superseded by F20 — total removal) | — |
| F19 | TTS-induced phonetic collisions create theological errors — "al-Qur'an Mayni" (al-Kirmani name colliding with the Quran), "Sahih al-Sajidiyya" (conflating Sahih al-Bukhari hadith collection with al-Sahifa al-Sajjadiyya supplication) | 2026-05-21 (KaR Ch07 v2 audio review) | **High** | Open (superseded by F20 — total removal eliminates this class) | — |
| F20 | Arabic names (person, book, author) in chapter prose AND framing leak into spoken audio; NotebookLM TTS cannot reliably pronounce them; editorial principle shift: knowledge is the key, not the references | 2026-05-21 (Asif's editorial doctrine after Ch07 v2 review) | **High** | Open | — |
| F21 | Book-title references in spoken audio need natural-language wrapping ("the book *The Harvest*") rather than bare English title ("The Harvest") to disambiguate from poems/metaphors/ideas | 2026-05-21 (Asif refinement to F20) | Medium | Open | — |
| F22 | Extended-tier length target needs to be 45-60 min (not 30-45) for dense scholarly content; bumped via X18 in Phase 0g framing-gen prompt; testing on Ch07 v3 upload | 2026-05-21 (Asif directive after Ch07 v2 audio review) | Medium | Triaged (X18 patch in `_authoring.py:author_framing()` Opening-directive line; Ch07 v3 lab carries the new directive as the empirical test) | — |
| F23 | Pipeline has no chapter-relevance check vs book-thesis; editorial-intro chapters and off-topic appendices reach Phase 0d/0e/0f without being flagged; only caught by manual review (cost KaR ~2 hr + a mid-pipeline drop of ch01a) | 2026-05-21 (Asif Q1 — surfaced during synthesis on forward-prevention) | Medium | Open | — |
| F24 | Alqaab/honorific titles need functional-paraphrase discipline; literal translation of obscure alqaab into English damages register ("the Striker"); only established renderings (Commander of the Faithful, Lion of God) are spoken; novel alqaab become functional paraphrases ("one of his martial honorifics") | 2026-05-21 (Asif recommendation doc — TTS-Safe Arabic Name/Title/Honorific Handling) | **High** | Open | — |
| F25 | Show-notes (`99-show-notes.md`) lack a structured apparatus-table; freeform paragraphs make scholarly traceability inconsistent; need per-term row schema (Original / Transliteration / Category / Audio Label / First Use / Later Use / Speak? / Reason) so written layer formally carries what audio layer drops | 2026-05-21 (Asif recommendation doc — written-apparatus formalization) | **High** | Open | — |
| F26 | `name-aliases.yml` schema is too thin — only `canonical` + `first_mention` + `aliases[]`; needs to absorb `original_arabic`, `transliteration`, `written_display`, `role_in_argument`, `forbidden_spoken_forms[]` per figure; Phase 0d should auto-emit the richer schema (Tier 3 backlog) | 2026-05-21 (Asif recommendation doc — F23 schema integration) | Medium | Open | — |
| F27 | TTS-safe audit is currently a manual checklist (audit-checklist.md); must become a code-side validator suite in `build_episode_txt.py` to satisfy M1 (LLM ignores prompt-only rules); validators needed: `assert_no_arabic_transliteration_in_chapter_or_framing`, `assert_alqaab_only_established_or_paraphrased`, `assert_show_notes_has_apparatus_table`, `assert_framing_no_modern_artifacts`, `assert_framing_analogy_cap_strict`, `assert_framing_honorific_bounded_both_sides` | 2026-05-21 (synthesis of v3 audit + recommendation doc) | **High** | Open (this is the Tier 2.5 validator burst, now formalized) | — |
| F28 | Backward-compat decision needed for already-shipped episodes (EP04, 06, 07, 08, 09, 10, 12, 14, 15) once F20+F21+F24+F25 doctrine is locked; options: (a) re-emit all under new doctrine (~6.5 hrs), (b) grandfather them as v1-quality (cost: inconsistency across series); KaR-specific but template-setting for all future books | 2026-05-21 (synthesis of recommendation doc adoption sequence) | Medium | Open (decision needed) | — |
| F29 | Arabic surah names still spoken in audio because chapter prose contains them; TTS mangles them ("Qaf" → "cough" in v4-revised audio; "al-Shams" and "al-Ahzab" also surfaced); same root cause as F20 (Arabic vocabulary in chapter prose leaks to audio); fix: chapter rewrite step replaces surah names with English meanings ("the chapter on the sun," "the chapter on the confederates") OR drops surah name entirely in favor of leading with content | 2026-05-21 (KaR Ch07 v4-revised audio audit) | **High** | Open | — |
| F30 | Bundle-level NotebookLM-readiness audit has no operational path; Gemini-Gem auditor design exists ([prompts/gemini-bundle-auditor.md](../../prompts/gemini-bundle-auditor.md)) and the consolidation packer ([scripts/podcast/pack_bundle_for_gemini.py](../../scripts/podcast/pack_bundle_for_gemini.py)) and the Claude-native mirror ([scripts/podcast/audit_bundle.py](../../scripts/podcast/audit_bundle.py)) are built and verified, BUT the actual Gemini Gem has not yet been created in the Gemini UI — any operator workflow that targets the Gem must first prompt for Gem creation (paste the BEGIN/END block from the prompt file into the Gem's Instructions box) before invoking the consolidate-and-upload path. Also: this audit is currently a manual operator gate, not an orchestrator phase; intended future slot is optional phase 0g audit between enrich and the review halt | 2026-05-25 (Asif Gem-design session — Gemini rejected the original zip approach due to 10-file / 100 MB / no-audio-video limits) | Medium | Open (Gem creation pending in Gemini UI; orchestrator integration pending) | — |
| F32 | Framing re-runs from scratch on every per_chapter_pass() restart — even when prior framing was already good. Code-confirmed: `per_chapter_pass()` always calls `extract → author_framing → build → converge` top-to-bottom. When the watchdog restarts after a crash, convergence failure, or iter-cap halt, framing re-runs regardless of whether it was the cause of failure. Empirical cost: `father-revealed-and-the-faces-of-seeking` had 7 framing calls × avg $3.12 = ~$22 in redundant framings for one chapter. Fix: write a `framing_done` flag to per-chapter state after first successful framing. On resume, if flag exists and `00-framing.md` is non-empty and the prior failure was not a framing-structural P0, skip re-framing and enter the convergence loop directly at the prior checkpoint. | 2026-05-25 (cost ledger analysis — 17 framings for 6 chapters; father-revealed=7, the-greater-shaykh=5, will-command=2) | **High** | Open | — |
| F33 | Book halts on first per-chapter failure, blocking all subsequent independent chapters. Code-confirmed: `orchestrate_book.py:1394-1401` — when `outcome.final_verdict == "FAILED"`, the loop calls `return 2` immediately, leaving all unstarted chapters unprocessed. For a 14-chapter book (Kitab al-Riyad), a stuck ch03 would have left ch04-ch14 unstarted for the entire human-review cycle. Fix: add `continue_on_failure` mode (flag `--continue-on-failure` or default-True for books with >4 chapters): collect failed chapters into a `failures[]` list, continue the loop for independent chapters, surface all failures together at the end. Watchdog then retries failed slugs individually. | 2026-05-25 (code review of orchestrate_book.py:1390-1405 + watchdog `_is_iter_cap_halt()`) | **High** | Open | — |
| F34 | Phase 0b refinement windows and Phase 0d source-chapter processing run sequentially in a Python for-loop — no parallelism. Code-confirmed: `_authoring.py` Phase 0b and 0d both iterate `for sc in source_chapters:` and call `_run_claude_p()` synchronously per window. For a 12-window Phase 0b, windows are independent (each processes a discrete text chunk with a 120-word overlap tail for continuity — output files don't share mutable state). A ThreadPoolExecutor with 3 concurrent workers would cut wall-clock time by ~3× for these phases. Rate-limit risk is low: claude-opus-4-7's API tier easily handles 3 concurrent calls; the per-window 10-min timeout provides natural back-pressure. Phase 0d source chapters are also independent: each chapter contract is generated from its own slice. Same fix applies. | 2026-05-25 (code review of _authoring.py Phase 0b loop + Phase 0d sc loop) | **High** | Open | — |
| F35 | No per-chapter LLM cost ceiling — a stuck chapter can exhaust the convergence loop's max iterations (3 outer × 5 inner = 15 challenger passes + 9 fixer passes) at avg $3.47/challenger + $0.36/fixer ≈ $55 per chapter before halting. There is no circuit breaker. Fix: add `--chapter-cost-cap N` (default $20): track per-chapter accumulated cost from the cost ledger (filter by chapter slug + session ERROR_TS); if cost exceeds cap before convergence, abort that chapter's loop, mark it `FAILED` with `reason=cost_cap_exceeded`, and let the watchdog surface it for human review. Operator can re-run with `--chapter-cost-cap 40` to allow more spend on a known-difficult chapter. | 2026-05-25 (cost ledger analysis: will-command-and-the-seven had framing=2 + challenger=4 + fixer=6 passes before failing) | **High** | Open | — |
| F36 | Azure costs not tracked during Phase 0a (Document Intelligence) and Phase 0c (Speech/Translator). Code-confirmed: `orchestrator-state.json` has the right fields (`docintel_usd`, `translator_usd`, `speech_usd`) but all are $0.00 — nothing writes to them. The pipeline calls Azure Document Intelligence for PDF parsing (Phase 0a) and Azure Translator/Speech for phonetics (Phase 0c) but never writes cost back to state. For a 200-page PDF like master-and-the-disciple, Document Intelligence costs ~$3-4 (invisible to operator). Fix: in `_azure.py:docintel_analyze_pdf()`, estimate cost from page count (`pages × $0.015`); in Phase 0c's TTS/translator calls, accumulate character count and compute cost at phase end; write back to `orchestrator-state.json.cost.*_usd` fields via `update_phase()`. | 2026-05-25 (state file inspection: all cost fields $0.00; confirmed live on master-and-the-disciple run) | Medium | Open | — |
| F37 | No per-chapter timing data in orchestrator state — operators cannot see which chapters are slow, ETAs are coarse averages, and post-mortem diagnosis of cost outliers requires manual ledger analysis. Code-confirmed: state.json tracks only `phases.per-chapter.ts_started` (one timestamp for the whole phase), not per-chapter start/end. The heartbeat loop computes `avg_s = elapsed_s / done` which is inflated by retry cycles (father-revealed's 7 framings inflate avg by ~45 min). Fix: add `chapter_timings: {slug: {started, completed, framing_calls, challenger_calls, fixer_calls, cost_usd}}` to the per-chapter state extras after each chapter completes. Heartbeat can then show per-chapter duration and flag outliers. Also unblocks F35's cost-ceiling implementation. | 2026-05-25 (heartbeat avg/ch analysis: avg showing 3h 49m vs expected ~2h 20m for clean chapters, inflated by retry cycles) | Medium | Open | — |
| F31 | No mid-book inter-chapter quality signal propagation — the trainer runs post-publish only; completed chapters' P0/P1 findings never feed forward into subsequent chapters' framing prompts during the same book run. Code-confirmed: `author_framing()` reads only the chapter contract + chapter file + static rules; the per-chapter loop in `orchestrate_book.py:1372-1419` passes zero quality state from completed chapters to the next framing invocation; `invoke_trainer()` fires only in the `publish → trainer → merge → done` pipeline, after ALL chapters ship. Result: if ch01 produces a systemic P0 (e.g. welcome-sentence missing, analogy cap blown), ch02-ch06 framing authors repeat the same mistake — the snowball effect runs backwards. Fix: add a lightweight "inter-chapter flash brief" step between `completed_chapter_slugs.add(slug)` and the next slug's `author_framing()` call — extract P1+/P0 finding IDs from the just-completed chapter's `challenger-report.md`, inject as a ≤5-bullet "prior chapter lessons" block into the next framing prompt. No spec edits, no regression gate — just runtime signal injection within the same book run. Distinct from the trainer (which edits the spec post-hoc across books). | 2026-05-25 (Asif observation confirmed by code review of `_authoring.py:author_framing()` + `orchestrate_book.py:1372-1419` during master-and-the-disciple run) | **High** | Open | — |

---

## Item details

### F1 — Phase 0g framing-gen LLM ignores hard word-count caps

**Where:** `scripts/podcast/_authoring.py:author_framing()` lines 1158–1187, the `claude -p` prompt that generates `00-framing.md`.

**What goes wrong:** The prompt explicitly says `"Length: Default tier 200–500 words; Extended tier 1,000–1,800 body words + pronunciation block; hard cap 3,500 words per build_episode_txt.py"`. For KaR EP14, the LLM produced 4,959 words anyway — 41% over the cap. Validator then halted on R-FRAMING-WORD-BAND.

**Impact:** Every chapter whose generated framing overshoots the cap requires a manual `claude -p` trim pass ($1–3 + 5–10 min editor time per episode). At-scale, this is ~12 retries per book × queued books = 60+ retries projected.

**Proposed fix:** Add explicit per-section word caps in the framing-gen prompt (e.g., `Pronunciation: max 800 words; Central tensions: max 500 words; Three-part focus: max 500 words; other sections: max 200 words each`). Optionally: instruct the LLM to self-check word count before returning, and re-trim if over.

**Verification:** Re-run framing-gen for one over-budget chapter (e.g., ch14b) and confirm output ≤ 3500 words without manual trim.

**Status:** **CLOSED (shipped 2026-05-25).** Two-layer defense:
1. Framing-author prompt at [_authoring.py:1576-1585](../../scripts/podcast/_authoring.py) carries explicit per-section word caps (Pronunciation 800, Central tensions 500, Three-part focus 500, etc.) plus the self-count-before-return instruction.
2. Post-authoring guard at [_authoring.py:1791+](../../scripts/podcast/_authoring.py): `author_framing()` reads the freshly-written framing, counts words; if > FRAMING_WORD_MAX (3700), invokes ONE focused compression re-author with trim priority (Pronunciation first, then Three-part focus, Central tensions, Background). Composes with F33-second graceful-degrade — if compression also runs over, build gate handles the rest.

---

### F2 — Phase 0g framing-gen produces unused pronunciation entries

**Where:** Same prompt as F1; the Pronunciation section in particular.

**What goes wrong:** The prompt instructs `"Use imperative \`Pronounce \"X\" as \"Y\". Say it as one fluent word.\` for every Arabic term that appears in the chapter (consult \`_phonetics.md\` first)"`. The LLM correctly consults `_phonetics.md` but generates entries for EVERY phonetics-mapped term in the BOOK, not just terms in this CHAPTER. For KaR EP14, 19 of the pronunciation entries were for terms not in ch14b — pure padding.

**Impact:** Inflates the framing word count (the Pronunciation section was the single biggest contributor to EP14's overflow). Wastes NotebookLM's customize-prompt budget on unused entries.

**Proposed fix:** Tighten the prompt — explicitly instruct: `"First, grep the chapter file for every Arabic/transliterated term. Then for each term found, look up its phonetic in _phonetics.md and generate one imperative line. Do NOT generate entries for terms not present in the chapter file."` Alternative: do the grep deterministically in Python before invoking the LLM, and pass only the chapter-relevant subset of `_phonetics.md`.

**Verification:** Re-run framing-gen for a name-dense chapter (ch14b) and confirm only terms appearing in the chapter source get pronunciation entries.

**Status:** **CLOSED (shipped 2026-05-21).** Framing-author prompt at [_authoring.py:1598-1605](../../scripts/podcast/_authoring.py) carries the F2 framework guard: "First grep the chapter file for every Arabic/transliterated term. For each term FOUND in the chapter, look up its phonetic in `_phonetics.md` and generate one imperative line. Do NOT generate pronunciation entries for terms not present in the chapter." Validated by Tier 2.5 build gate.

---

### F3 — Phase 0e enrichment emits manuscript-history meta-commentary

**Where:** `scripts/podcast/_authoring.py:author_phase_0e()` (or equivalent — the enrichment prompt that produces `chapters/ch##-*.txt`).

**What goes wrong:** Phase 0e enriches the source into NotebookLM-ready prose. The current prompt produces sections like `"## What survives at the head of the manuscript"` followed by paragraphs about "damaged folios," "reconstructed fragments," "the text breaks off." These are editorial framings about the manuscript's physical condition that have no place in the spoken audio — NotebookLM hosts will read them aloud and the listener gets meta-commentary about the manuscript instead of the philosophy.

**Impact:** Five KaR chapters carry this noise (ch03a heaviest, then ch04b/ch07/ch15). Each affected chapter needs hand-cleanup before its episode ships.

**Proposed fix:** Add a "Do NOT include" instruction to the Phase 0e prompt: `"Do not write editorial framings about the source manuscript's physical state (damaged folios, reconstructed fragments, OCR breakdowns, translator's notes, editor's notes). The chapter file is the spoken content — only include prose the hosts should discuss as substantive philosophy."`

**Verification:** Re-run Phase 0e for one chapter (preferably without piping back to NotebookLM — just verify the output prose) and confirm no manuscript-meta language.

**Status:** **CLOSED (shipped).** R-NO-MANUSCRIPT-META validator wired in [build_episode_txt.py:1245](../../scripts/podcast/build_episode_txt.py) — hard-gates manuscript-history meta-commentary at build time, framing-author prompt instructs to suppress upstream.

---

### F4 — Phase 0d chapter design includes editorial-intro chapters

**Where:** `scripts/podcast/_authoring.py:author_phase_0d()` — the chapter-design step that maps source abwāb/fusūl to podcast episodes.

**What goes wrong:** For KaR, Phase 0d produced ch01a — "The Four Da'is and the Debate" — as one of 14 episodes. But ch01a's entire body is editor Aref Tamer's introduction to the book (biographies of the three preachers, chain of four debate-books, historical setup). None of it is al-Kirmani's own prose. It shipped as an episode contract anyway.

**Impact:** Asif had to manually drop ch01a from the series after observing the content. For a book with extensive editorial frontmatter (which most scholarly editions have), this happens by default.

**Proposed fix:** Phase 0d should distinguish "content chapters" (the author's own prose) from "editorial frontmatter" (editor's intro, translator's preface, manuscript history) and either (a) skip frontmatter entirely from the episode plan, or (b) emit it as `intro-context` non-episode metadata for the series plan to optionally use.

**Verification:** Run Phase 0d on a book with substantial editorial frontmatter (e.g., a future scholarly edition) and confirm the editor's intro doesn't show up as an episode contract.

**Status:** **CLOSED (shipped 2026-05-25).** Phase 0d author prompt at [_authoring.py:1006+](../../scripts/podcast/_authoring.py) now carries the F4 guard: "EXCLUDE editorial frontmatter from the episode array. If a source-chapter is the editor's introduction, translator's preface, publisher's note, manuscript history, biographical sketch of the editor's team, or any other non-authorial paratext... DO NOT emit a `chapter-contracts/` file for it. Instead include it in `series-plan.md` under a `frontmatter:` list with one-line descriptions, so the operator can optionally script an intro episode from the apparatus by hand." Composes with F23's `thesis_relevance: out-of-scope` route — same exclusion list.

---

### F5 — Phase 0e enrichment emits repeated honorific glyphs

**Where:** `scripts/podcast/_authoring.py:author_phase_0e()` — same prompt as F3.

**What goes wrong:** Phase 0e generates chapter prose that uses the honorific glyph ﷺ (sallallahu alayhi wa sallam) multiple times per chapter. For KaR: ch12 had 26 occurrences, ch14b had 11, ch08 and ch09 had 3 each. The R-HONORIFIC-ONCE rule then halts the episode at Phase 0g build step because NotebookLM vocalizes every glyph as the full phrase.

**Impact:** Four chapters required manual dedup. ([X6 fix](https://github.com/asifhussain60/podcast-factory/commit/801d2fd) deduplicated KaR's chapter files but the underlying enrichment prompt still emits the repeats.)

**Proposed fix:** Add to the Phase 0e prompt: `"Honorific glyphs (ﷺ, peace be upon him, etc.) should appear AT MOST ONCE per figure per chapter — on first mention. Subsequent mentions use the contracted name only."`

**Verification:** Run Phase 0e on a chapter known to be prophet-dense (e.g., a future book's prophetic-cycle chapter) and confirm ≤1 occurrence of ﷺ per figure.

**Status:** **CLOSED (shipped).** R-HONORIFIC-ONCE enforcement in [build_episode_txt.py](../../scripts/podcast/build_episode_txt.py) (F27 Tier 2.5 validator #5) — each honorific allowed exactly once per chapter (not zero, not 2+). Detection via [test_challenger.py:detect_honorific_repeat()](../../scripts/podcast/test_challenger.py).

---

### F6 — Cost-ledger silently fails on Python 3.9

**Where:** `scripts/podcast/_authoring.py:_run_claude_p()` — the per-LLM-call cost-ledger append.

**What goes wrong:** Throws `AttributeError("module 'datetime' has no attribute 'UTC'")` on every Claude shell-out. `datetime.UTC` is Python 3.11+. Air runs Python 3.9 (per `infra/azure/store-keychain-keys.sh` and observed runtime). The cost-ledger silently fails to record spend; the orchestrator continues without halting.

**Impact:** Spend on Air-run books is not tracked. Need to reconstruct retroactively from wall-clock + per-episode rates. Studio (which probably runs 3.11+) is unaffected.

**Proposed fix:** Replace `datetime.UTC` with the compatibility-safe `datetime.timezone.utc`. Verify across all callsites.

**Verification:** Re-run any Phase that calls `_run_claude_p` on Python 3.9 and confirm `cost-ledger.jsonl` gets appended successfully.

**Status:** **CLOSED (shipped 2026-05-21).** `_now_iso()` in [_cost_ledger.py:103-107](../../scripts/podcast/_cost_ledger.py) uses `datetime.timezone.utc` (compat with 3.9+). Inline comment documents the F6 fix.

---

### F7 — Orchestrator doesn't surface multi-task cost projection

**Where:** `scripts/podcast/orchestrate_book.py:_drive_authoring_through_0f()` and the per-chapter loop in `run_resume()`.

**What goes wrong:** When resuming after Phase 0f, the orchestrator launches into per-chapter authoring for all queued chapters without surfacing the projected total spend. For KaR, this means starting a run that will burn $14-42 across 14 episodes without an explicit "this exceeds the $20 multi-task cost ceiling" warning.

**Impact:** Asif has to mentally project the spend each time. The coord-protocol cost cap is advisory not enforced.

**Proposed fix:** At resume time, before entering the per-chapter loop, the orchestrator computes `remaining_episodes × estimated_per_episode_cost` and either prints a warning or requires `--accept-cost N` if over the cap.

**Verification:** Resume a book at the per-chapter phase and confirm the orchestrator surfaces the projection before starting.

---

### F8 — Stale `episode-drafts/EP*` directories accumulate

**Where:** `scripts/podcast/orchestrate_book.py:per_chapter_pass()` and `_authoring.py:author_framing()`.

**What goes wrong:** When an X-class bug causes the orchestrator to write a framing to the wrong directory (e.g., `EP14b/` instead of `EP14/`), the wrong directory persists across subsequent runs. Manual cleanup commits are required (KaR did this multiple times today).

**Impact:** Confusing filesystem state; risk that the validator picks the wrong directory.

**Proposed fix:** At per-chapter loop start, scan `_system/episode-drafts/` for any directory whose name doesn't match the expected `EP##-<slug>` for the chapters in `chapters/`. Either delete (aggressive) or warn (conservative).

**Verification:** Trigger an X-class bug scenario, then run resume; confirm stale directories are cleaned (or surfaced for cleanup).

**Status:** **CLOSED (shipped).** `_sweep_orphan_episode_drafts(book_dir)` lives in [orchestrate_book.py](../../scripts/podcast/orchestrate_book.py) and is invoked from 3 call-sites (per-chapter loop start, preflight_resume, finalize). Deletes any `EP*` subdir whose name isn't in the expected slug set.

---

### F9 — R-PHONETICS-OUT pattern set audit needed

**Where:** `scripts/podcast/build_episode_txt.py:168-179` — `INLINE_PHONETIC_PATTERNS`.

**What goes wrong:** Pattern #1 was over-broad — matched scholarly Arabic transliterations alongside true pronunciation guides. Fixed in [X5 commit c9424dd](https://github.com/asifhussain60/podcast-factory/commit/c9424dd). But the other R-* rules in the validator may have similar intent-vs-implementation drift.

**Status:** Triaged — X5 fixed the immediate hit. Remaining work: audit each R-* rule's regex against its handbook-defined intent, looking for false-positive risk.

**Proposed fix:** Pair each rule's regex with a unit test exercising both "should match" and "should not match" cases. Today none of the validator rules have unit tests.

**Verification:** Run the audit; produce a rule-set health report.

---

### F10 — Word-band rules with "~" prose use exact thresholds in code

**Where:** `scripts/podcast/build_episode_txt.py` — `CHAPTER_WORD_MAX_HARD`, `FRAMING_WORD_MAX`, etc.

**What goes wrong:** The rule prose in `content/podcast/.skill/handbook/notebooklm-best-practices.md` says things like `"episodes over ~10,000 words risk..."`. The tilde is empirical-tolerance language. But the code enforced exact 10000. For KaR ch12 (10180) and ch14b (10112), the chapters were 1-2% over a round-number cap and got blocked.

**Status:** Triaged — [X6](https://github.com/asifhussain60/podcast-factory/commit/801d2fd) bumped `CHAPTER_WORD_MAX_HARD` from 10000 → 10500 (5% tolerance, aligning code with prose). `FRAMING_WORD_MAX` (3500) is still exact.

**Proposed fix:** Apply the same alignment to `FRAMING_WORD_MAX` if its prose source carries similar "~" language. Or introduce a `TOLERANCE_PCT` constant that derives soft/hard bands from a single source-of-truth threshold.

**Verification:** Run a book whose framing lands at 3501 and confirm the validator's response is consistent with the prose's stated intent.

---

### F11 — Iter-1 SHIP verdict + iter-2 challenger timeout = chapter marked FAILED (even though episode shipped)

**Where:** `scripts/podcast/orchestrate_book.py:per_chapter_pass()` — the converge loop after `extract → frame → build`.

**What goes wrong:** When the build step succeeds, the episode `.txt` artifact is emitted to `episodes/EP##-<slug>.txt`. That artifact IS the ship — uploaded to NotebookLM, the chapter generates audio. The converge loop then runs the challenger to find P0/P1/P2 issues, runs the fixer to address them, and iterates. If any iteration's challenger pass times out, the orchestrator marks the entire chapter FAILED — overwriting the shipped status. KaR observed this on EP04 / EP07 / EP08: all three shipped via build step at iter 1, then iter-2's challenger timed out, all three were marked FAILED, requiring manual `state.completed_slugs` patches.

**Impact:** Every dense chapter follows this pattern, blocking auto-progress through the queue. The orchestrator restarts after each manual patch. ~3 minutes per chapter of operator work, recurring on every book.

**Proposed fix:** When any iteration achieves a SHIP-READY or SHIP-WITH-CAUTION verdict, set the chapter as shipped in `state.completed_slugs` immediately (without waiting for the converge loop to fully terminate). Subsequent iterations are best-effort polish — their timeouts should be logged but NOT roll back the ship verdict. Reformulate "FAILED" semantics: a chapter is FAILED only if BUILD fails (no episode artifact emitted). Converge timeouts/errors after a successful ship verdict are recorded as a warning, not a halt.

**Verification:** Run on a chapter known to produce SHIP-WITH-CAUTION at iter 1 (e.g., KaR ch08). Confirm chapter advances to next slug even if iter-2 challenger times out.

**Status:** **CLOSED (shipped 2026-05-25).** [_convergence.py:converge_chapter()](../../scripts/podcast/_convergence.py) now tracks `best_verdict_so_far` and `best_verdict_at_iter` across iterations. When a later challenger pass raises `AuthoringError` (timeout, crash, parse failure), the loop checks the prior ship signal: if iter-N produced SHIP-READY (any iter) or SHIP-WITH-CAUTION at iter >= SHIP_WITH_CAUTION_MIN_ITER, the verdict is PRESERVED rather than wiped to FAILED. Notes record "preserved SHIP-* from iter N (later challenger timeout did not invalidate the prior ship signal)" so the operator can see why the chapter shipped despite a downstream error.

---

### F12 — Episode IDs derived from chapter filename digits, not from `contract.episode_number`

**Where:** `scripts/podcast/orchestrate_book.py:per_chapter_pass()` (around line 720) and `scripts/podcast/_authoring.py:author_framing()` (around line 1153) — both currently extract the digit prefix from the chapter filename (with X3 + X7 letter-strip logic) to form the episode_id.

**What goes wrong:** Listener-facing episode IDs derive from chapter filenames. Chapter files carry source-baab provenance (ch03a, ch04b, ch05c, ch13a, ch14b) and may include gaps after a chapter drop (ch01a, ch02b dropped → no EP01/EP02). The listener sees a non-sequential episode feed (KaR shipped EP04 / EP07 / EP10 / EP12 / EP14, queued EP03 / EP05 / EP06 / EP08 / EP09 / EP11 / EP13 / EP15 — visible gaps at EP01 / EP02 and the irregular spacing).

**Impact:** The chapter contracts already have an `episode_number:` field declaring the listener-facing sequence. The orchestrator ignores it and derives from filename digits instead. Renaming chapter files would lose source-baab provenance; the contract field is the right source of truth.

**Proposed fix:** Both `per_chapter_pass()` and `author_framing()` should read `contract.episode_number` and format it as `EP{episode_number:02d}-<slug>` instead of extracting digits from the chapter filename. Operator updates `episode_number` per contract to be sequential 1..N in series-plan order; orchestrator regenerates episode artifacts with the new IDs on next per-chapter pass. Chapter filenames remain unchanged (ch03a, ch04b, ch05c etc. preserve source-baab provenance for future books from the same author).

**Verification:** Set `episode_number: 1` on chapter contract `the-perfect-and-the-perfection-of-the-soul.yml` (currently ch03a). Run the per-chapter pass on it. Confirm episode artifact lands at `episodes/EP01-the-perfect-and-the-perfection-of-the-soul.txt`.

**Out-of-band KaR-specific rename:** see [series-plan.md](../../content/drafts/kitab-al-riyad/_system/series-plan.md) footer for the per-chapter rename checklist scoped to KaR. Execution waits for the orchestrator to quiesce on the current queue.

**Status:** **CLOSED (shipped 2026-05-25).** New helper `_resolve_episode_id(book_dir, chapter_file, chapter_slug)` in [orchestrate_book.py](../../scripts/podcast/orchestrate_book.py) reads `chapter-contracts/<slug>.yml` and prefers `episode_number` from the contract over filename digits. Both callsites in `per_chapter_pass()` (pre-flight lint, build) now use this helper. Falls back to filename digits (X3 letter-strip logic preserved) when contract is missing or lacks the field. Smoke-tested on the-master-and-the-disciple/ch01.

---

### F13 — Phase 0e enrichment leaks inline `(pho-net-ic — gloss)` parens despite R-PHONETICS-OUT

**Where:** `scripts/podcast/_authoring.py` Phase 0e enrichment prompt that produces `chapters/ch##*.txt`, AND the validator pass that's supposed to enforce R-PHONETICS-OUT (per [skills-staging/podcast/SKILL.md](../../skills-staging/podcast/SKILL.md) INVARIANT 5).

**What goes wrong:** R-PHONETICS-OUT (effective 2026-05-17) forbids inline `(pho-net-ic — gloss)` parens in chapter txt — phonetics belong only in the customize-prompt `## Pronunciation` block. Yet [ch15-tawhid-and-the-critique-of-al-mahsul.txt](../../content/drafts/kitab-al-riyad/chapters/ch15-tawhid-and-the-critique-of-al-mahsul.txt) shipped with 18 inline phonetics on terms (`tawhid (taw-heed — monotheism)`, `al-hayula (al-ha-yoo-laa — prime matter)`, etc.) plus 1 on a people-name (`Abu Hatim al-Razi (a-boo haa-tim ar-raa-zee)`). Sibling chapters (ch03a, ch04b, ch05c, ch06–ch09, ch10–ch14b) are all clean — only ch15 leaked. Manually stripped 2026-05-21 in the post-ship audit, but the underlying enrichment regression slipped past the validator.

**Impact:** Operator audit time to catch + manually strip per affected chapter (~10 min per chapter). At-scale across queued books, R-PHONETICS-OUT violations would drift into shipped episodes if not caught. Worse, the audit shows ch15 is INCONSISTENT with its 14 siblings — the regression is non-deterministic per chapter, suggesting either a prompt-sensitivity issue (some chapters' source text triggers more LLM inline-phonetic emission than others) or a validator gap (the rule fires on some patterns and not others).

**Proposed fix (two parts):**
1. **Detector:** Add a strict R-PHONETICS-OUT validator pass over every `chapters/ch##*.txt` after Phase 0e completes. Pattern: `\(([a-z']+(-[a-z']+){1,})(\s+—\s+[^)]+)?\)` — matches hyphenated-lowercase-syllable groups inside parens, optionally followed by ` — gloss`. Whitelist legitimate transliteration parens (no hyphens between Roman-letter syllables, e.g., `(al-aimma al-bararah)` passes; `(al-a-im-mah al-ba-ra-rah)` fails). Halt Phase 0e on detection; do not advance to framing.
2. **Auto-stripper:** When detector fires, run a deterministic strip that preserves glosses (`(taw-heed — monotheism)` → `(monotheism)`; `(al-mah-sool)` → drop parens entirely if no gloss) and emit a diff for operator review before re-running validator.

**Verification:** Re-run Phase 0e on a chapter whose source text is known to elicit inline phonetics from the current prompt (any chapter where the operator previously stripped phonetics manually — e.g., ch15 source). Confirm: (a) detector fires before framing; (b) auto-stripper output matches the manual strip diff; (c) re-validator passes.

**Related:** F9 (R-PHONETICS-OUT pattern #1 was over-broad — shipped as X5). F13 is the inverse problem: pattern coverage is now too narrow / not invoked at the right gate.

**Status:** **CLOSED (shipped).** Two-layer: deterministic [strip_inline_phonetics.py](../../scripts/podcast/strip_inline_phonetics.py) post-pass strips `(pho-net-ic — gloss)` parens from chapter prose; framing-author prompt enforces R-PHONETICS-OUT upstream. Tier 2.5 build gate refuses any chapter with inline phonetics.

---

### F14 — Arabic names repeated dozens of times per episode; NotebookLM TTS mangles each occurrence inconsistently

**Where:** Two prompts contribute: (a) `_authoring.py:author_phase_0e()` — chapter-source generation; (b) `_authoring.py:author_framing()` — customize-prompt name-discipline section.

**What goes wrong:** Surfaced 2026-05-21 by listener feedback on the NotebookLM-generated audio for KaR Ch07 ("How the Soul Touches Prime Matter"). The transcript shows NotebookLM's text-to-speech mangling "al-Kirmani" into roughly eight different garbled forms in a single 30-minute episode: `al-Quraymani`, `alkyr M a knee`, `I'll carry many`, `Alcure MNE`, `al-kheir MNE`, `I'll care ma me`, `Alkur Emini`, `Alkyr a main knee`. Similar mangling on `al-Islah` (becomes `all is La H`), `al-Nusra` (`an NUS Ross` / `NUS Rob` / `an NUS raw`), `al-Hayuli` (`all how you law`, `al-hi you la`, `alayullah`), `ma'lul` (`ma. Lol`), `Ghurar al-Hikam` (`Garar al-hikm`). The listener hears pronunciation noise instead of substance.

**Impact:** Every chapter ships with this defect because the chapter prose + framing both repeat Arabic names dozens of times. Each occurrence is an independent TTS attempt — NotebookLM doesn't anchor to a prior pronunciation. The framing's `## Pronunciation` block tries to fix this with imperative pronounce-as-X-as-Y lines, but in practice the TTS still drifts. The listener's grasp of the philosophical content is undermined by constantly mangled name references.

**Proposed fix — three layers:**

1. **Phase 0e (chapter prose).** Add to the enrichment prompt: "Use each Arabic figure name ONCE on first mention with an English role-reference appositive (e.g., `Hamid al-Din Ahmad al-Kirmani, the author of Kitab al-Riyad`). Thereafter, refer to that figure using the English role-reference or a pronoun, NOT the Arabic name. The chapter prose should contain at most 1–2 occurrences of any Arabic figure name; everything else uses English aliases." Applies to authors, scholars, transmitters; technical Arabic vocabulary (tawhid, hudud, etc.) is unaffected — those are concept-words, not figure-names.

2. **Phase 0g (framing host-discipline).** Strengthen the existing "Name discipline" section in the framing template. Instead of just "use alias for subsequent mentions," enumerate a ROTATION SET of 3–4 English aliases per figure and instruct the hosts to rotate naturally among them (avoiding "the author" 20 times in a row). Example for al-Kirmani: rotation set = `{the author, the master, our author, he}`. For Imam Ali: rotation set = `{the Commander of the Faithful, the cousin of the Prophet, the gate of knowledge, the first Imam}`. The framing's `## Name discipline` section lists the rotation set for every figure that appears in the chapter.

3. **Per-figure rotation-set design (book-level decision).** For each figure that recurs across multiple chapters in a book, define a fixed rotation set at the book level (in `_system/series-plan.md` or a sibling file). The framing-gen step reads this and embeds the per-figure rotation set into every chapter's framing. Ensures consistency across episodes — listener hears the same English aliases for the same figure in every chapter, building familiarity.

**KaR-specific remediation (out-of-band):** the 7 already-shipped KaR episodes carry the defect in their generated audio. Options: (a) accept the cost; re-upload after a chapter-prose + framing edit pass; (b) accept what shipped and apply the framework fix to future books only. The 6 chapters still in the queue can benefit from a framing-level fix immediately — patch the framing-gen prompt with the rotation-set instructions before they run.

**Verification:** Re-author one chapter's framing with the strengthened name-discipline section; have NotebookLM regenerate the episode; transcript audit should show ≤2 Arabic-name occurrences per figure and natural rotation among English aliases.

---

### F15 — Framing produces "two hosts unpacking" dynamic instead of "explainer vs genuine challenger"

**Where:** `scripts/podcast/_authoring.py:author_framing()` — the framing-gen prompt; specifically the `## Host dynamic`, `## Central tensions`, and `## Three-part focus` instructions.

**What goes wrong:** Surfaced 2026-05-21 by an independent GPT review of the KaR Ch07 NotebookLM-generated audio transcript. Four structural defects:

1. **Second host too agreeable.** Transcript shows phrases like "That is a remarkably precise analogy", "That beautifully maps al-Kirmani's intent", "That is the perfect translation" — supportive-explainer dynamic instead of genuine-challenger dynamic. The episode reads like a polished lecture disguised as dialogue.
2. **Central tension introduced + resolved too quickly.** The crisis ("if higher and lower realities are categorically different, how do they connect at all?") is stated, then both reformers' positions, al-Kirmani's correction, and several analogies are explained before the listener has time to feel the problem.
3. **Analogy proliferation.** Ch07's 30-minute episode contains 14+ distinct analogies (footprint, political border, messenger, white-coat doctor, glass-and-stone, fulcrum, sphere, pie chart, cathedral, ladder/mountain/valley, seven seas, solar panels, wax-seal). Some are valuable; cumulative effect is fatigue.
4. **Thesis stated once, not repeated.** Al-Kirmani's central settled formula ("contact does not require resemblance — it requires rank, receptivity, and transmitted power") is stated once and never returned to. Listener loses the anchor.

**Impact:** Listener gets information but not suspense; the philosophical stakes (an-Nusra's universe-disconnection fear) are explained but don't land emotionally; the episode's intellectual richness is undermined by structural choices.

**Proposed fix (4 parts, all in Phase 0g framing-gen prompt):**

1. **Narrative-arc template for debate-format chapters.** Add a 6-beat structural arc to the framing's `## Three-part focus` template:
   - Beat 1: crisis statement (state the problem so the listener feels its stakes)
   - Beat 2: failed answer A (al-Islah's position; let it sound reasonable)
   - Beat 3: failed answer B (al-Nusra's position; same)
   - Beat 4: al-Kirmani's pivot (the move that escapes both)
   - Beat 5: non-bodily correction (why category mistakes were made)
   - Beat 6: human/political stakes (why this matters beyond metaphysics)
   - Beat 7 (closing): unresolved listener question
2. **Challenger-discipline section in host_dynamic.** Require the Color host (or scholar_companion) to genuinely push back. Examples of acceptable pushback openings: "I don't buy that yet…", "That sounds like wordplay…", "Isn't this just replacing X with Y…", "How is this different from hiding the problem under a different word…". Forbid agreeable affirmations as a host's FIRST sentence ("That's a remarkably precise…", "That beautifully maps…", "Perfect translation…"). The Color host's role is FRICTION, not chorus.
3. **Analogy budget — cap at 3–5 governing analogies.** The framing's `## Tone constraints` enumerates the chosen governing analogies UPFRONT (e.g., "for this chapter use these 3: footprint, messenger, light-through-glass-and-stone"). Hosts elaborate on the chosen ones, but cannot introduce new analogies mid-episode. Forbidden mid-episode invention.
4. **Recurring-thesis rule.** The chapter's central settled formula (from `contract.anchor_passages`) must be repeated 3 times across the episode: once at the open, once at the pivot, once at the close. Framing's `## Opening directive` + `## Three-part focus` + `## Landing` instructions explicitly reference the repetition rule.

**Push-back on GPT's recommendation:** GPT recommended capping analogies at 3. We recommend 3–5 — for dense philosophical chapters, 3 may be too few for the listener to find footholds across 30 minutes of audio. 5 governing analogies allows breadth without descending into the 14-analogy fatigue Ch07 produced.

**Related root cause (separate framework gap):** ch07's contract assigned `host_dynamic: curious_mind + scholar_companion`, which is supportive-by-design — the wrong host pairing for an adjudicative chapter that debates two reformers. Adjudicative chapters should default to `advocate_a + advocate_b + arbiter`. Phase 0d host-dynamic-selection heuristic needs review (queue as F16 if not already triaged by series-plan classification rules).

**KaR-specific remediation (out-of-band):** the 7 already-shipped KaR episodes carry this defect. The 6 remaining chapters can benefit from X16 (the Phase 0g prompt patch) on next orchestrator launch. Re-doing the 7 shipped is the same Middle Path vs Full Remediation decision as F14.

**Verification:** Re-author one debate-format chapter's framing with X16 in place; regenerate; transcript audit should show ≤5 distinct analogies, ≥3 challenger-pushback moments, central thesis repeated 3 times, and the 6-beat narrative arc visible in pacing.

**Status:** **CLOSED (shipped).** `host_dynamic_table` mechanism in [orchestrate_book.py:542](../../scripts/podcast/orchestrate_book.py) injects explicit asymmetric host roles (explainer-vs-challenger) into Phase 0d planning. R-HOST-ROLE-PARITY (CHALLENGER_VERSION 2.1) locks Host A = scholar / Host B = seeker across the book.

---

### F16 — Framing announces source-book chapter number, not podcast episode number

**Where:** `_authoring.py:author_framing()` — the `## Opening directive` section of the framing template.

**What goes wrong:** The framing instructs hosts to open with "*Kitab al-Riyad*, Chapter Three" (the source-book's chapter number). The listener hears "Chapter 3" and gets confused when they're listening to "Episode 7" of the podcast. Empirical: KaR Ch07 v2 audio surfaced this — listener explicitly asked "why does the audio say chapter 3?"

**Impact:** Listener loses series-position context. For a 13-episode book, knowing whether you're at episode 4 of 13 or episode 11 of 13 matters for pacing your listen-through.

**Proposed fix:** Opening directive instructs hosts to announce BOTH — "Episode 7 of our walkthrough of *Kitab al-Riyad*, covering the book's Chapter Three." Order matters: episode-number first (listener's reference), source-chapter second (provenance reference). Phase 0g framing-gen prompt also gets a section reminder that `contract.episode_number` is the listener-facing reference; `contract.source_chapter_ref` is the source-tracing reference.

**Verification:** re-author one chapter's framing post-fix; transcript audit should show "Episode N" announced in the open before "Chapter M of the source."

**Status:** **CLOSED (shipped 2026-05-25).** Closed by [F12](#f12--episode-ids-derived-from-chapter-filename-digits-not-from-contractepisode_number) — `_resolve_episode_id()` reads `contract.episode_number` first, so framing's episode declarations always match the listener-facing sequence rather than chapter-filename digits.

---

### F17 — R-ANALOGY-CAP under-enforced; hosts introduce new analogies mid-episode despite explicit instruction

**Where:** `_authoring.py:author_framing()` R-ANALOGY-CAP rule (X16 addition); also the framing's `## Tone constraints` section.

**What goes wrong:** X16 added R-ANALOGY-CAP, instructing the framing to enumerate 3-5 governing analogies upfront and forbidding mid-episode introduction. KaR Ch07 v2 transcript audit shows the rule was PARTIALLY honored — hosts elaborated on the 3 governing analogies (footprint, messenger, light-on-glass-and-stone) AND introduced 5+ new ones (cosmic ruler, crystal pitcher + silver cup, Venn diagram of reality, signet ring + wax, radio tower / antenna).

**Impact:** v1 had 14+ analogies; v2 had 8 (3 governing + 5 invented). Improvement, but the cap discipline didn't fully take. NotebookLM apparently treats "forbidden mid-episode invention" as a soft suggestion rather than a hard rule.

**Proposed fix:** Strengthen the rule. Two options: (a) make the forbidden mid-episode invention an EXPLICIT instruction in the framing's `## Three-part focus` sections — "Beat 3 MAY ONLY use the governing analogies from Tone constraints; introducing new analogies here violates R-ANALOGY-CAP and the conversation should pause and return to a governing analogy"; or (b) extend the validator (Tier 2 additions) to count distinct analogies in the framing's prose and FAIL if any beat-section contains an analogy not declared upfront.

**Verification:** re-author one chapter's framing post-fix; transcript audit shows ≤5 distinct analogies and 0 mid-episode introductions.

**Status:** **CLOSED (shipped).** R-ANALOGY-CAP validator in [build_episode_txt.py:638](../../scripts/podcast/build_episode_txt.py) (F27 Tier 2.5 #3) hard-gates new analogies introduced in framing/chapter prose beyond the framing's declared 3 governing analogies. Empirical baseline established 2026-05-21.

---

### F18 — Single-Arabic-occurrence still mangled by TTS

**Where:** R-NAMEDISCIPLINE (X15 addition) — currently allows one Arabic-name occurrence on first mention with English appositive.

**What goes wrong:** Even with name-rotation discipline reducing the COUNT to ~1 per chapter, NotebookLM TTS mangles the single occurrence into multiple inconsistent garbled variants. The mangling propagates: when the host then says "the author" (the English alias), the listener has already heard 8+ garbled pronunciations and can't anchor.

**Impact:** F14's count-reduction discipline was a partial fix; F18 names the deeper truth that ANY Arabic occurrence in spoken content triggers TTS unpredictability.

**Status:** **CLOSED (superseded by F20 — also closed).** Doctrine shift to total Arabic-name removal eliminated F18's surface entirely. F18 preserved as the diagnostic step that motivated F20.

---

### F19 — TTS-induced phonetic collisions create theological errors

**Where:** NotebookLM TTS engine; not directly under operator control.

**What goes wrong:** Empirical Ch07 v2 audio observations:
- "al-Kirmani" → "al-Qur'an Mayni" (the author's name collides with the Quran itself in the listener's ear)
- "Sahih al-Sajidiyya" — the TTS conflates "Sahih al-Bukhari" (a hadith collection) with "al-Sahifa al-Sajjadiyya" (Imam Zayn's supplication). Two distinct works become one wrong work in the audio.

**Impact:** These aren't pronunciation imperfections — they're THEOLOGICAL ERRORS introduced by TTS. A listener hearing "al-Qur'an Mayni argued that the Second is born from the First" hears a claim that the Quran itself argues a metaphysical proposition. That's wrong content, not just wrong pronunciation.

**Status:** **CLOSED (superseded by F20 — also closed).** TTS-collision risk eliminated by removing Arabic personal names from spoken content entirely. F19 preserved as the empirical evidence motivating F20.

---

### F20 — Arabic names (person, book, author) leak into spoken audio; doctrine shift: remove entirely

**Where:** `_authoring.py:author_phase_0e()` (chapter-prose enrichment) + `_authoring.py:author_framing()` (host-instruction framing).

**What goes wrong:** F14 reduced the COUNT of Arabic names; F18 + F19 showed reduction is insufficient because EVEN ONE Arabic occurrence triggers TTS mangling AND phonetic collisions that create theological errors.

**Editorial doctrine (Asif 2026-05-21):** "I want all Arabic names (person, book and authors) removed from all chapters. Ignoring the reference weave the quote or statement directly in the dialog generalizing it to a scholar, a Daa-ee, messenger etc. This will resolve the issue. The knowledge is the key not the references."

**Proposed fix (three layers):**

1. **Phase 0e — chapter prose discipline.** New rule **R-NO-ARABIC-NAMES** instructing the LLM: NEVER write Arabic person-names, book-titles, or scholar references in the chapter prose. Replace ALL person-names with generic descriptors: "a scholar", "a preacher", "a Da'i" (acceptable loanword for a role-title), "the messenger", "a transmitter", "the early reformer". Quote attributions weave the statement directly into the conversation without naming the source ("It is said that…" / "A scholar of the school argued…" / "One early transmitter recorded…").

2. **Phase 0g — framing host-discipline.** The framing's `## Name discipline` section becomes `## No-name discipline` — explicitly instructs hosts to NEVER speak Arabic person-names or book-titles. The `## Pronunciation` section drops ALL figure-name entries. Concept-word loanwords that are necessary role-terms (Da'i, Imam) may stay with pronunciation guidance; figure-names cannot.

3. **Show notes / book entry preserves attribution.** The audio strips all Arabic; the written companion (book entry on the journal site + per-episode `99-show-notes.md`) preserves the full bibliography with Arabic names, transliterations, English glosses, and suggested-reading list. Listener who wants deeper study has full access; listener who only consumes audio gets clean prose.

**Push-back recorded:** Claude recommended specific English role-descriptors ("the Fatimid philosopher", "the chief preacher of the Persian school") instead of generic ("a scholar") to preserve figure-tracking across an episode. Asif chose generic per the simpler editorial doctrine. The trade-off accepted: listener cannot easily distinguish which-of-several-scholars-said-what; audio quality wins. Mitigation: when the same scholar is referenced multiple times in close sequence, use "the same scholar" or "the one who argued earlier" to preserve continuity within a beat.

**KaR-specific remediation:** the 8 already-shipped KaR episodes carry the defect. Per the established Middle Path scope for F14/F15: accept what's shipped; apply F20's framework patch for future books. KaR Ch07 v3 could be authored as a fresh lab iteration under the new doctrine if Asif wants to test.

**Verification:** apply F20 prompt patches; regenerate one chapter; transcript audit should show ZERO Arabic person-names spoken; ZERO Arabic book-titles spoken; ZERO TTS-mangle events of the F14/F18/F19 class. Show notes contain the full Arabic attribution.

**Status:** **CLOSED (shipped).** R-NO-ARABIC-NAMES doctrine codified in [_authoring.py:1316+](../../scripts/podcast/_authoring.py) (`F20 doctrine 2026-05-22; empirically locked …`). Framing-author prompt now instructs functional paraphrase + English role-descriptors instead of Arabic person/book names. Verified on the-master-and-the-disciple's 6 shipped episodes.

---

### F21 — Book-title references in audio need natural-language wrapping ("the book *The Harvest*")

**Where:** Phase 0e + Phase 0g — wherever book titles appear in chapter prose or framing.

**What goes wrong:** F20 mandates English book titles instead of Arabic transliterations ("The Harvest" not "al-Mahsul"). But bare "The Harvest" in conversation can be heard as a poem, a metaphor, an idea, or a season — not clearly a book.

**Editorial refinement (Asif 2026-05-21):** "When referencing book, mention it is a book as in 'as stated in the book *The Harvest*…'". Wrap every book reference with the role-word "book" to disambiguate.

**Proposed fix:** Phase 0e + Phase 0g prompts require book references to use natural-language wrappings:
- First mention: "the book *The Harvest*" / "a book called *The Defense*" / "in the book *The Repose of the Intellect*"
- Subsequent in close sequence: "the book" / "that book" / "the earlier work" / "the same book"
- Scripture is the exception: "the Quran" is already unambiguous; doesn't need "the book the Quran". Hadith collections become "the canonical hadith collection" rather than "the book *Sahih al-Bukhari*".

**Verification:** apply prompt patch; transcript audit shows every English book-title is preceded or followed by the word "book" in conversation, OR uses an unambiguous descriptor ("the earlier work", "the corrective treatise").

**Status:** **CLOSED (shipped).** Framing-author prompt at [_authoring.py:1641-1643](../../scripts/podcast/_authoring.py) bullet 5 enforces book-wrap: first mention `the book *The Harvest*`; thereafter `the book` / `that book` / descriptor (`the corrective treatise`). NEVER speak Arabic book titles. Composes with F20 (R-NO-ARABIC-NAMES).

---

### F23 — Pipeline has no chapter-relevance check vs book-thesis

**Where:** Phases 0a → 0f. No stage compares a chapter's content against the book's thesis.

**What goes wrong:** PDFs commonly include editor's introductions, appendices, bibliographies, or off-topic material that survives Phase 0a (ingest) and Phase 0b (refine) untouched. Phase 0d clusters them into chapter chunks; Phase 0e writes contracts for them; Phase 0f's series-plan ordering takes them as given. Only manual Phase 0f review catches drift — and only if a human notices.

**Concrete cost (KaR):** ch01a was an editor's introduction discussing manuscript stemma and editorial discovery, not al-Kirmani's philosophy. It survived Phases 0a-0e and only got dropped at Phase 0f after ~2 hours of manual review. State.json then needed surgery to remove the chapter from `completed_slugs` and contracts.

**Proposed fix:** Add a Phase 0d.5 "book-coherence" sub-step:
1. Extract book-level thesis from cover + preface + author-intro into a one-sentence `book_thesis.md`.
2. For each chapter, score relevance against the thesis (LLM semantic similarity + topical-alignment).
3. Flag any chapter below threshold as "drift candidate" → human review at Phase 0f gate.
4. Output: `book-coherence.md` with per-chapter scores + flagged items.

**Verification:** run against KaR — ch01a should score below threshold; ch07-ch15 should score high.

**Status:** **CLOSED (shipped 2026-05-25).** Phase 0d chapter-contract author prompt at [_authoring.py:1023+](../../scripts/podcast/_authoring.py) now requires a `thesis_relevance` field on every chapter contract — a 1-2 sentence statement connecting the chapter to the book's central thesis. If the chapter does NOT advance the thesis (digression, appendix, apparatus, fundraising), `thesis_relevance: "out-of-scope"` excludes it from the episode array and routes it to series-plan's `frontmatter:` list. Composes with F4's editorial-frontmatter exclusion — same end state, two intake paths. Deterministic validator (assert every chapter contract has the field) is straightforward follow-up if false-positive rate on the LLM-side rule warrants it.

---

### F24 — Alqaab/honorific titles need functional-paraphrase discipline

**Where:** Phase 0e (chapter authoring) + Phase 0g (framing-gen). Specifically: any moment a chapter introduces an Arabic alqaab (honorific title) for a figure.

**What goes wrong:** Three failure modes when chapters reference alqaab:
1. **Literal English translation damages register.** "The Striker" (al-Karrar / al-Daraab) sounds like a sports nickname; "The Returner" sounds like a fantasy character.
2. **Multiple alqaab for the same figure clutter audio.** Ali has Asadullah, al-Murtada, al-Karrar, Haydar — speaking all of these confuses identity tracking even if pronounced correctly.
3. **TTS mangles even well-known alqaab.** "Asadullah" → various unrecognizable forms.

**Editorial principle (from Asif's recommendation doc):** Use only established English forms with scholarly currency (Commander of the Faithful, Lion of God). For novel/obscure alqaab, use **functional paraphrase** that describes the title's role rather than translating it literally.

**Proposed fix:** Phase 0e prompt patch:
- Allowed spoken forms: `Commander of the Faithful`, `Lion of God`, and any alqaab with established English form in scholarly literature.
- Novel alqaab → functional paraphrase: "one of his martial honorifics," "a traditional title associated with his rank," "a devotional title emphasizing sacred authority."
- Phase 0e contract `figures[].audio_label` field becomes the single audio anchor.
- Written show-notes (F25) carry the literal alqaab in scholarly form.

**Verification:** validator `assert_alqaab_only_established_or_paraphrased` scans framing + chapter for any unfamiliar transliterated alqaab; passes only if every honorific is either on the allowed list OR is a functional paraphrase.

**Status:** **CLOSED (shipped).** R-ALQAAB-FUNCTIONAL-PARAPHRASE doctrine codified in [_authoring.py:1344+](../../scripts/podcast/_authoring.py) framing-author prompt. Functional paraphrase required for novel alqaab; established forms (Commander of the Faithful, Lion of God) explicitly allowed; literal Arabic alqaab routed to show-notes apparatus only.

---

### F25 — Show-notes apparatus-table schema

**Where:** Phase 0g — `99-show-notes.md` emission.

**What goes wrong:** Current show-notes are freeform paragraphs. Scholarly traceability requires structured per-term mapping so the listener (or a future researcher) can move from "the author" in audio to "Hamid al-Din al-Kirmani" in the written record. Freeform paragraphs make this lookup inconsistent across episodes.

**Editorial principle (from Asif's recommendation doc):** Every audio script must be accompanied by a written name-and-title table.

**Proposed schema:**
```markdown
## Name and Title Preservation Table

| Original / Transliteration | Category | Written Form | Audio Label | First Audio Use | Later Audio Use | Speak in Audio? | Reason |
|---|---|---|---|---|---|---|---|
| Ḥamīd al-Dīn al-Kirmānī | Person | Hamid al-Din al-Kirmani | the author | the author of the book at hand | the author | No | TTS instability |
| Abū Ḥātim al-Rāzī | Person | Abu Hatim al-Razi | the first reformer | the first reformer | the first reformer | No | TTS instability |
| al-Sahifa al-Sajjadiyya | Book | al-Sahifa al-Sajjadiyya / The Psalms of Islam | the book *The Psalms of Islam* | the book *The Psalms of Islam* | the book | No Arabic | Risk of conflation with Sahih al-Bukhari |
| Amir al-Mu'minin | Honorific | Amir al-Mu'minin | Commander of the Faithful | Commander of the Faithful | the Commander of the Faithful | Yes, English only | Established English rendering |
```

**Categories:** `Person` | `Book` | `Title/Alqaab` | `Concept` | `Technical term` | `Quranic surah` | `Geographic name`

**Proposed fix:** Phase 0g emits the apparatus table as the head of `99-show-notes.md`; validator `assert_show_notes_has_apparatus_table` checks for the table header + at least N rows per chapter.

**Verification:** for KaR, the apparatus-table should have ~25 rows per episode (author + 2 reformers + 4 Imams + 3 books + 8 concept-words + 5 honorifics + ~2 surahs).

**Status:** **CLOSED (shipped).** `F25-APPARATUS-TABLE` validator wired in [build_episode_txt.py:1018+](../../scripts/podcast/build_episode_txt.py); silent-skip when 99-show-notes.md absent so legacy bundles don't break. Per-book apparatus emission per Phase 0g flow. Followups (per-row schema enrichment) tracked under F26.

---

### F26 — `name-aliases.yml` schema evolution

**Where:** `content/drafts/<book>/_system/name-aliases.yml` per book; consumed by Phase 0g framing-gen.

**Current schema:**
```yaml
- canonical: al-Kirmani
  first_mention: "the author of the book at hand"
  aliases: ["the author", "the master", "our author"]
```

**What's missing:** Recommendation doc's F23 schema adds fields the validators and the apparatus-table (F25) both need:
- `original_arabic` — for written-layer rendering
- `transliteration` — academic form (e.g., "Ḥamīd al-Dīn al-Kirmānī")
- `written_display` — readable English form ("Hamid al-Din al-Kirmani")
- `role_in_argument` — single English sentence ("author of the book under discussion")
- `forbidden_spoken_forms` — explicit list for code-side regex check ("al-Kirmani", "Kirmani", "al-Karman", etc.)

**Stable-roles doctrine (v4 finding):** Collapse `aliases[]` to a single `audio_label` per figure. Rotation aliases hurt identity tracking.

**Proposed schema:**
```yaml
- original_arabic: حميد الدين الكرماني
  transliteration: Ḥamīd al-Dīn al-Kirmānī
  written_display: Hamid al-Din al-Kirmani
  role_in_argument: the author of the book under discussion
  audio_label: the author
  first_audio_introduction: "the author of the book at hand"
  forbidden_spoken_forms:
    - al-Kirmani
    - Kirmani
    - al-Kirmaani
    - Hamid al-Din al-Kirmani
  category: Person
```

**Proposed fix:** Phase 0d auto-emits the richer schema (Tier 3 backlog ticket); migrate existing `name-aliases.yml` files (KaR has one); validator `assert_name_aliases_schema_v2` checks structure.

**Verification:** Phase 0d run on a book produces the v2 schema; Phase 0g framing-gen consumes `audio_label` (not `aliases[]`).

---

### F27 — TTS-safe audit must be a code-side validator suite

**Where:** `scripts/podcast/build_episode_txt.py` — currently has 6 `assert_*` validators from Tier 2; needs ~6 more.

**What goes wrong:** Audit-as-checklist depends on a human (Asif) listening and marking PASS/FAIL. v3 audit proved this catches doctrine violations after the fact but doesn't *prevent* them. M1 (LLM ignores prompt-only rules) keeps repeating because there's no code-side enforcement.

**Proposed validator additions (Tier 2.5):**
- `assert_no_arabic_transliteration_in_chapter` — regex for "al-", "Abū", "Ibn", apostrophes, hyphenated Arabic patterns; fails if any survive in chapter.txt.
- `assert_no_arabic_transliteration_in_framing` — same regex applied to framing.md.
- `assert_alqaab_only_established_or_paraphrased` — alqaab whitelist + paraphrase pattern detection.
- `assert_framing_no_modern_artifacts` — banned modern-vocabulary list (TV, broadcast, 4K, cosplay, etc.).
- `assert_framing_analogy_cap_strict` — extracts analogy-like patterns ("think of it like", "imagine a", "it's like when") and checks against the framing's declared 3 governing analogies + banned list.
- `assert_framing_honorific_bounded_both_sides` — each honorific exactly 1 occurrence; not 0, not 2+.
- `assert_show_notes_has_apparatus_table` — F25 enforcement.
- `assert_name_aliases_schema_v2` — F26 enforcement.

**Verification:** run on KaR Ch07 v4 lab; should pass all validators if v4 doctrine holds. Run on Ch07 v3 lab; should FAIL on alqaab + modern-artifacts + analogy-cap (which is exactly what the v3 audio audit found by ear).

**Status:** **CLOSED (shipped).** Tier 2.5 validator suite landed in [build_episode_txt.py:695+](../../scripts/podcast/build_episode_txt.py) under F27 banner — 8 deterministic hard-gate checks wired (F27 #1-#8) covering Arabic-transliteration block in chapter/framing, forbidden analogies, modern-vocab contamination, honorific count, Arabic surah names (F27 #6 / F29), awkward alqaab literal-translation (F27 #7), and apparatus-table presence (F27 #8 / F25). 11 explicit F27/Tier-2.5 references across the file.

---

### F28 — Backward-compat decision for shipped episodes

**Where:** All shipped episodes in `content/drafts/<book>/episodes/`.

**What goes wrong:** Once F20+F21+F24+F25+F26+F27 doctrine is locked, the 9 already-shipped KaR episodes (EP04, 06, 07, 08, 09, 10, 12, 14, 15) will fail the new validators. Future books will pass; shipped books will sit at v1-quality.

**Options:**

1. **Re-emit all under new doctrine.** Cost: ~9 episodes × ~30 min hand-effort each + audio re-generation = 6.5+ hrs. Benefit: consistent series quality.
2. **Grandfather them as v1-quality.** Cost: 0 hrs. Drawback: inconsistency; listeners get pre-doctrine quality on early episodes and post-doctrine quality on later ones.
3. **Hybrid.** Re-emit only the worst offenders (probably EP07 and EP14b based on prior audits); grandfather the rest.

**Decision needed.** This is template-setting — what we do for KaR shapes what we do for every book that ships pre-v4 doctrine.

**Asif to decide.** No verification step until decision is made.

**Status:** **CLOSED — DECISION: GRANDFATHER (option 2) 2026-05-25.** Recorded as the standing policy for pre-doctrine shipped episodes:

- Kitab al-Riyad (shipped May 2026 pre-v4 doctrine): grandfathered. Episode files at [content/published/books/kitab-al-riyad/](../../content/published/books/kitab-al-riyad/) are the v1-quality reference for the listener.
- The-master-and-the-disciple onward: full v4 + v2.2 + F30 + scaffold-retirement doctrine applied; expected to ship at the new quality bar.
- Re-emission of KaR is OPT-IN per chapter at operator discretion — there is no scheduled re-emission pass. The cost calculus (6.5+ hrs hand-effort + audio re-gen vs. listener marginal benefit on episodes already absorbed) does not justify backfill.
- Pre-doctrine validator failures on KaR are accepted as historical artifacts (the gates still run; they emit warnings rather than blocking on the published tree).

Rationale: Asif's autonomous-execution memory says ship forward, not backfill. Future books that ship through the post-doctrine pipeline will be uniformly v4-quality from day one; the discontinuity at KaR is documented in the registry rather than fixed in episode files.

---

### F29 — Arabic surah names leak to audio; TTS mangles them

**Where:** Chapter prose at Phase 0e enrichment. Chapter sources contain Quranic verse citations with Arabic surah names: "the chapter al-Shams," "the chapter al-Ahzab," "the chapter Qaf." Framing instructs to use English meanings; chapter prose contains the Arabic. Model follows the source.

**What goes wrong:** TTS mangles Arabic surah names. Empirically observed in KaR Ch07 v4-revised audio (2026-05-21):
- "Qaf" → spoken as "cough" (the English noun for a respiratory expulsion). Comedic and theologically catastrophic.
- "al-Shams" → spoken with Arabic phonemes; audible but TTS-unstable across renderings.
- "al-Ahzab" → spoken as "al-azab" (truncated/mangled).

This is the same M1 + F20 pattern: framing rule ignored because chapter source forces it. The framing said use English meanings; the model used what was in the chapter.

**Editorial fix:** Phase 0e prompt patch — REWRITE Quranic verse citations in chapter prose to use English surah meanings:
- al-Shams → "the chapter on the sun"
- al-Ahzab → "the chapter on the confederates" / "the chapter of the clans"
- Qaf → "the chapter Qaf" or drop and lead with verse content
- al-Isra (the night journey) → "the chapter on the night journey"
- al-Baqarah → "the chapter on the cow"

**Allowed-list of TTS-safe surahs (verified):** None yet. All Arabic surah names are at risk; default doctrine should be "use English meaning."

**Proposed fix paths:**
1. Phase 0e prompt: enforce English surah meanings; provide a lookup table for the ~30 most-cited surahs in Islamic philosophy.
2. Validator: `assert_no_arabic_surah_names_in_chapter_or_framing` — regex match against known surah names + Arabic phonetic patterns; fails if any survive.
3. Per-book artifact: `surah-aliases.yml` mapping Arabic surah name → English meaning per book.

**Verification:** apply prompt patch; v4-revised chapter rewrite removes "al-Shams / al-Ahzab / Qaf"; next audio render shows zero surah-name mangling.

**Status:** **CLOSED (shipped).** R-SURAH-ENGLISH-ONLY doctrine codified in [_authoring.py:1336+,1697+](../../scripts/podcast/_authoring.py) framing-author prompt with the verified surah→English-meaning table. Reinforced by R-NO-AI-CLICHE / R-NO-ESSENTIALISM-EXTERNAL surrounding doctrine. Validator (F27 #6) at [build_episode_txt.py:958](../../scripts/podcast/build_episode_txt.py).

---

### F30 — Bundle-level NotebookLM-readiness audit (Gemini Gem + Claude mirror) has no operational path until the Gem is created

**Where:** Three new artifacts that together compose a bundle auditor, none of which is yet wired into the pipeline or activated in Gemini:

| Artifact | Path | Status |
|---|---|---|
| Consolidation packer (bundle dir → single Gemini-friendly .md with `<!-- FILE: ... -->` virtual-path delimiters) | [scripts/podcast/pack_bundle_for_gemini.py](../../scripts/podcast/pack_bundle_for_gemini.py) | Built + verified 2026-05-25 against `content/published/books/kitab-al-riyad` (20 files, 0.76 MB) and `content/drafts/kitab-al-riyad` (170 files, 4.34 MB) |
| Canonical Gem prompt (single source of truth; BEGIN/END markers wrap the prompt body) | [prompts/gemini-bundle-auditor.md](../../prompts/gemini-bundle-auditor.md) | Built 2026-05-25 |
| Claude-native auditor mirror (shells `claude -p` with the Gem prompt + packed bundle; emits same `claude-code-fixes` JSON shape) | [scripts/podcast/audit_bundle.py](../../scripts/podcast/audit_bundle.py) | Built + syntax-verified 2026-05-25; not yet run end-to-end against a real bundle |

**What goes wrong (today):**

1. **The Gemini Gem itself does not exist.** The prompt file is ready to paste, but the Gem in the Gemini UI has not been created. Any documentation that says "upload the packed file to the Bundle Auditor Gem" silently assumes a Gem that an operator has not yet built. The first operator to attempt the Gem path will hit a dead end. **The original zip-based upload approach failed against Gemini's hard limits (10 files max inside a zip, 100 MB total, no audio/video) — the consolidate-to-one-markdown path is the chosen workaround, but it presupposes the Gem.**

2. **~~No orchestrator integration.~~ WIRED 2026-05-25.** Phase 0g now runs (a) `phase_0g_register()` then (b) `phase_0g_audit_bundles()` in [orchestrate_book.py](../../scripts/podcast/orchestrate_book.py) — the latter sweeps every per-chapter NotebookLM bundle (`_system/episode-drafts/EP##-<slug>/`) through `audit_bundle.py` + `audit_bundle_gemini.py` launched in parallel via `subprocess.Popen`. Reports land at `BOOK_DIR/audits/<EP-slug>.audit.{claude,gemini}.md`, with a summary table at `audits/0g-audit-summary.md`. Idempotent (skips bundles whose audit reports are newer than `00-framing.md`). Gemini auditor gracefully skipped if `security find-generic-password -s gemini_api_key` fails (Claude auditor still runs). The original pre-0f slot proposal was abandoned: per-chapter bundles don't exist until per-chapter authoring completes, so 0g is the earliest valid slot.

3. **No "Gem exists?" guard in operator workflows.** The audit-loop instructions in [prompts/gemini-bundle-auditor.md](../../prompts/gemini-bundle-auditor.md) under "How to use this Gem" assume the Gem is live. They do not explicitly say "create the Gem first." A future skill or runbook that drives this audit must prompt the operator to confirm Gem creation before kicking off the consolidate-and-upload path.

4. **No fix-application back-channel.** Once the Gem (or `audit_bundle.py`) emits the `claude-code-fixes` JSON array, there is no `audit_bundle.py --apply-fixes <json>` subcommand yet. The JSON has to be hand-fed to Claude Code. Stub mentioned in the prompt file's operator notes, not implemented.

**Impact:**
- Bundle quality issues (Arabic-token mispronunciation risk, missing pronunciation/citation appendices, banned crutch phrases, multi-thesis framings, missing 'skip the intro' instruction, host-role-drift) are caught today only by post-render audio review, after Azure speech spend.
- Catching the same issues at bundle time (before NotebookLM ingestion) saves the per-episode TTS spend and the operator's audio-review hour.
- Without the Gem operational guard, future operator instructions silently assume a Gem that doesn't exist and stall on the first attempt.

**Proposed fix paths:**

1. **Stand up the Gem.** Open Gemini → Gems → Create. Name: "Podcast Bundle Auditor." Paste the contents between `## BEGIN GEM PROMPT` and `## END GEM PROMPT` from [prompts/gemini-bundle-auditor.md](../../prompts/gemini-bundle-auditor.md) into the Instructions box. Save. Note the Gem URL/ID for the runbook. **This is the unblocking step; everything else assumes it.**

2. **Add a Gem-existence guard to the audit-loop instructions.** Update the "How to use this Gem" section in [prompts/gemini-bundle-auditor.md](../../prompts/gemini-bundle-auditor.md) and any future operator runbook (e.g., `_workspace/runbooks/bundle-audit.md`) to make step 0 explicit: "Confirm the Gemini Gem 'Podcast Bundle Auditor' exists in your Gemini workspace. If it does not, create it now using the BEGIN/END block in this file before proceeding." Any agent or skill that drives the audit must check for Gem URL/ID configuration and prompt the operator if missing.

3. **Wire `audit_bundle.py` into the orchestrator as optional Phase 0g.** Add `phase_0g_audit` to [_phases.py](../../scripts/podcast/_phases.py); call `audit_bundle()` from `_authoring.py` after Phase 0e enrich and before the Phase 0f review halt. Gate severity P0 findings as halt-and-surface; P1/P2 as informational. Off by default until two clean runs against published bundles establish a baseline.

4. **Implement `--apply-fixes <json>` on `audit_bundle.py`.** Takes the `claude-code-fixes` JSON array and applies each fix to the named file via `claude -p` (per-fix prompts, scoped to the named file + anchor + fix instruction). Same shell-out pattern as `_authoring.py`. Idempotent re-runs against the same JSON skip already-applied fixes.

5. **Cross-validate.** Once the Gem is live, audit the same bundle through both paths (Gem and `audit_bundle.py`); diff the JSON arrays. Persistent disagreement on a finding is a signal that the bundle has genuinely ambiguous prose, not that one auditor is wrong. Track diffs under `_workspace/audit-reports/bundle-cross-check/`.

**Cross-references:**

- [scripts/podcast/pack_bundle_for_gemini.py](../../scripts/podcast/pack_bundle_for_gemini.py) — the consolidation packer; bundle directory → single .md with `<!-- FILE: <rel-path> START -->` / `<!-- FILE: <rel-path> END -->` delimiters. Caps output at 90 MB (Gemini's hard ceiling is 100). Skips audio/video/images/archives/bytecode by default. PDFs become path-only stubs unless `--include-pdfs` is set.
- [prompts/gemini-bundle-auditor.md](../../prompts/gemini-bundle-auditor.md) — canonical Gem prompt with `## BEGIN GEM PROMPT` / `## END GEM PROMPT` markers. Single source of truth for both the Gemini UI Gem (paste between markers) and the Claude-native auditor (which reads the markers programmatically). All audit rules from the original spec preserved verbatim: severity tiers, articulation style, NotebookLM pitfalls, host-role consistency, the `claude-code-fixes` JSON schema.
- [scripts/podcast/audit_bundle.py](../../scripts/podcast/audit_bundle.py) — Claude-native mirror. `python3 scripts/podcast/audit_bundle.py <bundle_dir>` → audit.md + JSON. `--json-only` pipes JSON to stdout. `--packed <file.packed.md>` skips the packer step. Exit codes: 0 = success, 1 = invalid input, 2 = `claude -p` shell-out failure, 3 = output parse failure.

**Verification (to be done after the Gem exists):**

1. Pack a known-good bundle (e.g., `content/published/books/kitab-al-riyad`); upload to the Gem; confirm the Gem emits a `claude-code-fixes` JSON array with no P0 findings and only expected P2 polish items.
2. Pack a known-bad bundle (e.g., a draft with bullet lists in chapter prose, missing pronunciation appendix, multi-thesis framing); confirm Gem flags all expected categories (`articulation`, `pronunciation`, `format`).
3. Run `audit_bundle.py` against the same two bundles; diff JSON arrays against Gem output; agreement on at least ~80% of P0/P1 findings.

**Lessons captured here (for future meta-pattern synthesis):**

- *Vendor constraints matter at design time, not implementation time.* The zip approach was natural-fit until it hit Gemini's hard limits. Cost of catching this late: one full Gem prompt design that had to be reworked to consume a consolidated format. Future: check vendor upload limits (file count, size, type) before committing to a delivery shape.
- *Single source of truth for prompts.* The Gem prompt lives in [prompts/gemini-bundle-auditor.md](../../prompts/gemini-bundle-auditor.md) with explicit `BEGIN GEM PROMPT` / `END GEM PROMPT` markers so the same file feeds both the Gemini UI (human-paste) and `audit_bundle.py` (programmatic read). Duplicating the prompt between the Gemini Gem UI and a Python string literal is exactly the M7 (rule-set drift) pattern this debt file already tracks for R-rules.
- *Operator guards are part of the design.* Any external-tool dependency (Gem, MCP, third-party API key) needs a "does this exist? prompt the operator if not" check baked into the runbook, not assumed-live.

---

### F31 — Pipeline overfit to Islamic / Arabic / Ismaili content (tradition-pack refactor)

**Where:** Tradition-specific data and rules are spread across [_doctrinal.py](../../scripts/podcast/_doctrinal.py) (pins `ISLAM_DATA = REPO_ROOT/"content"/"_shared"/"islam"`), [_rules.py](../../scripts/podcast/_rules.py) (HONORIFICS, ABBREVIATIONS_MAP, ESSENTIALISM_STEM_PATTERNS all Islamic-only or 6-tradition hardcoded), [_authoring.py:486+](../../scripts/podcast/_authoring.py) (Phase 0c phonetic pass explicitly named "Arabic Phonetic Transcription Pass"). No tradition-pack resolver; no per-script transliteration scheme handling for Devanagari, Greek, Hebrew, Pali, IAST.

**What goes wrong:**
1. A Buddhist sutra commentary (or Christian patristic, Hindu philosophical, Daoist, indigenous, secular philosophy book) entering the pipeline silently no-ops T1-T5 doctrinal checks (wrong tradition's data loaded) AND mis-runs Phase 0c (Arabic-only prompt against non-Arabic source).
2. R-HONORIFIC-ONCE doesn't fire on "Bhagavan Buddha" / "Sri Sri Ravi Shankar" / "Saint Augustine" repetition — non-Islamic honorific patterns are unguarded.
3. R-NO-ABBREVIATION only knows Ihya/Nahj/Sahihayn; doesn't catch Lotus Sutra (LS), Summa Theologiae (ST), Brahma Sutras (BS).
4. `R-SURAH-ENGLISH-ONLY` has no parallel R-SUTTA-TITLE / R-PSALM-NUMBERED / R-UPANISHAD-IAST.

**Proposed fix paths:**
1. Refactor `_doctrinal.py` into `_doctrinal/{tradition}/...yml` registry; `load_doctrinal_pack(tradition)` dispatch.
2. `traditions.yml` registry with `{slug, demonym, adjective, scripts: [...], honorific_patterns: [...]}`; derive ESSENTIALISM_STEM_PATTERNS, HONORIFICS, etc. from it.
3. Parameterize Phase 0c prompt with `source_scripts: [arabic, devanagari, greek, hebrew, pali, ...]` from `series-config.yaml`; per-script transliteration scheme hints.
4. `build_episode_txt.py` reads `source_tradition` and only invokes the matching doctrinal pack's gates.
5. Emit `T-NO-PACK` informational finding when a tradition lacks a pack yet (so silence isn't mistaken for cleanliness).

**Severity:** P0 — blocks running ANY non-Islamic book end-to-end without false-positive or silent-no-op failures.

**Status:** Open. Identified 2026-05-25 forward-looking audit. Not yet scheduled; awaits explicit authorization (multi-day refactor).

---

### F32 — Pipeline overfit to `books` category (genre generalization)

**Where:** [_branching.py:39-46](../../scripts/podcast/_branching.py) advertises 6 categories (books, articles, documents, lectures, interviews, letters) but only `books` has tested end-to-end paths. [intake_book.py:124-132](../../scripts/podcast/intake_book.py) hardcodes `source_kind: "pdf"`. [_rules.py:78](../../scripts/podcast/_rules.py) `EPISODE_FORMAT_ALLOWED = ("deep_dive", "debate")` cannot accept walkthrough / monologue / interview / recap. Phase 0d/0e/0f/per-chapter authoring all assume multi-chapter long-form.

**What goes wrong:**
1. A `letter/<slug>` would run Phase 0d chapter-design pointlessly — a letter is one episode.
2. A lecture MP3 has no intake path (`_intake_from_audio` doesn't exist); the `import_transcript.py` workaround handles only one case.
3. An interview's natural format (co-host conversation) doesn't fit deep_dive/debate; R-HOST-ROLE-PARITY's scholar/seeker asymmetry doesn't apply.
4. The `audience` and `host_dynamic` defaults in [extract_chapter.py:450+](../../scripts/podcast/extract_chapter.py) presume scholar-companion + mentor-student framing — wrong for catechist-novice or peer-peer contexts.

**Proposed fix paths:**
1. Extend `EPISODE_FORMAT_ALLOWED` to include `walkthrough, monologue, interview, recap`; gate which formats are valid per category in a `category → allowed_formats` table.
2. Add `_intake_from_audio(mp3_path)`, `_intake_from_text(txt_path)`, `_intake_from_docx(docx_path)` siblings to `_intake_from_pdf`; dispatch by extension.
3. Per-category phase plan: `letter` skips 0d entirely; `lecture` routes audio → transcription → single-chapter pipeline; `interview` uses peer-peer host dynamic.
4. Audience/host_dynamic defaults derived from category, not hardcoded.

**Severity:** P0 — blocks running ANY non-book category end-to-end. Letters/articles/lectures all sit at the gate.

**Status:** Open. Identified 2026-05-25 forward-looking audit. Awaits explicit authorization (multi-day refactor; cleanly separable from F31).

---

### F33 — Cross-book observability gap

**Where:** [_cost_ledger.py](../../scripts/podcast/_cost_ledger.py) emits per-book `_system/cost-ledger.jsonl`. [cost_ledger_summary.py](../../scripts/podcast/cost_ledger_summary.py) reads ONE book at a time. Heartbeat card is per-in-flight-book. `findings.jsonl` is shared substrate but only the trainer reads it; no dashboard surfaces "which check fires most in the last 30 days."

**What goes wrong:** at 5+ in-flight books simultaneously, the operator has no single-pane-of-glass for burn rate, throughput, or rule-firing patterns. Decisions like "is dual-auditor still worth the cost across all books" are unanswerable.

**Status:** **CLOSED 2026-05-25.** Three pieces shipped:
- [cross_book_dashboard.py](../../scripts/podcast/cross_book_dashboard.py) — fleet-level phase/status/cost/chapter-timing table. Survives 5+ in-flight books cleanly.
- [learn_aggregate.py](../../scripts/podcast/learn_aggregate.py) `--by-check-id --since <window>` — rule-firing telemetry histogram (top 50 ranked, P0/P1/P2 split, books-affected count, top-book attribution per check_id). New `_parse_since` accepts `7d / 30d / 4w / 2m / 24h`.
- [_rules.py:emit_finding](../../scripts/podcast/_rules.py) now carries `bypassed_gate: str` field so post-publish findings tag which G1-G7 gate they slipped past. Trainer can compute per-gate false-negative rate. Empty for in-pipeline findings.

Outstanding (deferred to a later session): fleet-level heartbeat that auto-switches from per-book card to combined card when N≥2 books in flight — implementation is mechanical (heartbeat prompt drives the switch, no new code needed; just a documentation discipline in memory).

**Severity:** P1 — friction at 2+ books, painful at 5+.

---

### F34 — Doctrine-collision hazards in build-time gates

**Where:** [build_episode_txt.py](../../scripts/podcast/build_episode_txt.py) wires the doctrinal checks from [_doctrinal.py](../../scripts/podcast/_doctrinal.py) as universal hard gates regardless of `source_tradition`. T3_FORBIDDEN_IMAM_TITLES, T2 imam-lineage checks, etc. all run against every book.

**What goes wrong:** for a Buddhist or Christian book, the Islamic doctrinal gates no-op silently (no matches) — but the architecture is wrong: doctrinal checks should be tradition-conditional. Conversely, future tradition packs (Buddhist, Christian) would NOT be reached by the build gate even when present.

**Proposed fix:** dispatch build-time doctrinal gates through `load_doctrinal_pack(tradition)` (F31 prerequisite). Until F31 lands, document the no-op behavior so future operators know why their non-Islamic book "passed" doctrinal gates trivially.

**Severity:** P0 once a non-Islamic book runs; P3 (informational) until then.

**Status:** Open. Blocked on F31.

---

### F35 — `findings.jsonl` concurrent-append race condition

**Where:** [_rules.py:emit_finding](../../scripts/podcast/_rules.py) appended to a shared `content/podcast/.skill/_learning/findings.jsonl` from multiple concurrent orchestrators without file locking. Single-line writes under PIPE_BUF (4 KiB) are atomic on POSIX, but the JSONL record can exceed PIPE_BUF when `context_excerpt` is near its 300-char cap with multi-byte UTF-8.

**Status:** **CLOSED 2026-05-25.** `emit_finding` now wraps the append in an `fcntl.LOCK_EX` critical section with `flush()` before release. Cost ~1 ms per emit, negligible vs LLM-call latencies.

---

## Closed / shipped (historical)

For X-class fixes that have already shipped, see git log on `book/kitab-al-riyad`. As of 2026-05-21:

| ID | Title | Shipped commit |
|---|---|---|
| X1, X2 | Earlier Phase 0g blockers + state reset | [b8a2b82](https://github.com/asifhussain60/podcast-factory/commit/b8a2b82) |
| X3 | Strip letter suffix from chapter filename when forming episode_id (orchestrate_book.py) | [562b7d5](https://github.com/asifhussain60/podcast-factory/commit/562b7d5) |
| X4 | Don't renormalize chapter filename in extract_chapter (preserve letter suffix) | [ba52d21](https://github.com/asifhussain60/podcast-factory/commit/ba52d21) |
| X5 | R-PHONETICS-OUT regex tightened (pattern #1 had false-positive on scholarly transliterations) | [c9424dd](https://github.com/asifhussain60/podcast-factory/commit/c9424dd) |
| X6 | ﷺ honorific dedup across 4 chapters + chapter word-band 10000→10500 | [801d2fd](https://github.com/asifhussain60/podcast-factory/commit/801d2fd) |
| X7 | Mirror X3 fix in _authoring.author_framing() (second code path) | [95c4569](https://github.com/asifhussain60/podcast-factory/commit/95c4569) |

### F32 — Framing re-runs from scratch on every per_chapter_pass() restart

**Where:** `scripts/podcast/orchestrate_book.py:per_chapter_pass()` — the chapter pipeline always runs `extract → author_framing → build → converge` top-to-bottom, with no checkpoint between framing and convergence.

**Code confirmation:** `per_chapter_pass()` calls `author_framing(book_dir, chapter_slug)` unconditionally on every invocation. No state check, no skip condition. When the watchdog restarts the orchestrator after a crash or iter-cap halt, `per_chapter_pass()` re-runs from the top for the failed chapter — including a fresh `author_framing()` call even if the prior framing was structurally fine and the failure was a content finding in the convergence loop.

**Empirical cost (master-and-the-disciple, 2026-05-25):**

| Chapter | Framing calls | Challenger calls | Fixer calls |
|---|---|---|---|
| father-revealed-and-the-faces-of-seeking | 7 | 5 | 4 |
| the-greater-shaykh-and-the-naming | 5 | 4 | 1 |
| will-command-and-the-seven | 2 | 4 | 6 |
| justice-monotheism-and-the-guardians | 1 | 2 | 1 |
| the-call-and-the-covenant | 1 | 2 | 1 |
| world-hereafter-and-the-right-of-wealth | 1 | 1 | 0 |

`father-revealed` had 7 framing calls at avg $3.12 = ~$22 in framing for one chapter. The convergence loop itself (`_convergence.py`) never calls `author_framing()` — the re-runs all came from watchdog restarts triggering fresh `per_chapter_pass()` invocations. Each restart discarded a potentially-valid framing and paid $3.12 to regenerate it.

**Impact:** Across the 6 chapters, 17 framing calls should have been ~6-8 (one per chapter, one retry for will-command). The extra 9-11 calls cost ~$28-34 unnecessarily. For a 14-chapter book with multiple restarts, this compounds to $70-100+ in redundant framings.

**Proposed fix:** After `author_framing()` succeeds, write a `"framing_done": true` flag and framing file mtime to the chapter's per-chapter state extras. On `per_chapter_pass()` entry, check: if `framing_done` is set AND `00-framing.md` exists AND is non-empty AND the prior failure was not a framing-structural finding (check `challenger-report.md` for `P0-FRAMING-*` finding IDs) → skip `author_framing()` and jump directly into `converge_chapter()`. This saves one $3.12 LLM call per restart per chapter.

**Verification:** Induce a watchdog restart mid-convergence (kill the orchestrator after challenge pass 1). Confirm the resumed `per_chapter_pass()` skips framing and continues at the convergence loop, with the same `00-framing.md` on disk. Confirm cost ledger shows no new `framing/<slug>` entry for the resumed pass.

---

### F33 — Book halts on first per-chapter failure, blocking independent subsequent chapters

**Where:** `scripts/podcast/orchestrate_book.py:_drive_per_chapter_and_after()` — lines 1394-1401.

**Code confirmation:**
```python
if outcome.final_verdict == "FAILED":
    update_phase(book_dir, phase="per-chapter", status="failed", ...)
    _err(f"chapter {slug} failed; halting per-chapter loop.")
    return 2
```
First FAILED chapter immediately halts the entire book. Subsequent chapters in the queue never start.

**Impact at scale:** For Kitab al-Riyad (14 chapters), if ch03 hits the iter-cap halt with a systemic P0, ch04-ch14 never start. The operator fixes ch03, resumes, ch04-ch14 finally begin. Wall-clock delay: the full fix-and-resume cycle (human review + fix + re-run ch03) may take 2-6 hours — during which 11 other chapters sit idle despite being fully independent. For a 14-chapter book where each chapter takes ~2h, this halt serializes what could overlap.

**Nuance:** Chapters must be processed sequentially within a book (the orchestrator commits after each chapter; parallel chapter authoring risks git conflicts on shared state files). But a failed chapter does not need to block SUBSEQUENT chapters that have not yet started. The correct behavior is: mark the failed chapter, skip it, continue the remaining queue, surface all failures at the end.

**Proposed fix:**

1. Add `--continue-on-failure` flag (default `True` for books with ≥4 chapters, `False` for ≤3 where the overhead isn't worth it).
2. When a chapter fails: add it to a `failures[]` list, update state with `failed_slugs: [slug1, slug2, ...]`, continue the loop.
3. After all non-failed chapters complete: update phase to `per-chapter/partial` (new status), log a summary of failures, return code 3 (new code = partial completion).
4. Watchdog: treat rc=3 as a human-review gate (not a crash) — stops retrying, surfaces the failed chapters list.
5. `--retry-phase per-chapter` re-runs only the `failed_slugs`, skipping already-completed slugs as before.

**Verification:** Run a 4-chapter book where ch02's contract has a known systemic P0 (inject one). Confirm ch03 and ch04 complete successfully. Confirm state.json shows `failed_slugs: ["ch02-slug"]` and `completed_slugs: ["ch01-slug", "ch03-slug", "ch04-slug"]`. Confirm `--retry-phase per-chapter` re-runs only ch02.

**Status:** **CLOSED (shipped 2026-05-25).** [orchestrate_book.py:_drive_per_chapter_and_after()](../../scripts/podcast/orchestrate_book.py) now graceful-degrades: failed chapters added to `failed_chapter_slugs` set, loop continues to next chapter, state writes `failed_slugs` list each iteration. End-of-loop check: if ≥1 failures, phase marked `failed` with summary error (X of Y failed, list of slugs, hint to triage or raise cost cap and `--resume`). Skipped slugs on next resume: both `completed_slugs` and `failed_slugs` are honored as skip sets at the top of the loop (operator uses `--retry-chapter` to re-attempt). Default behavior — no flag needed.

---

### F34 — Phase 0b and 0d windows run sequentially; 3× wall-clock speedup available

**Where:** `scripts/podcast/_authoring.py` — Phase 0b loop over windows (calls `run_windowed()` sequentially per window); Phase 0d loop `for sc in source_chapters:` (processes each source chapter slice sequentially).

**Code confirmation:** Both phases use `for` loops over independent work units. Each unit calls `_run_claude_p()` (a blocking subprocess.run call). No threads, no async, no concurrency.

**Why independence holds:**
- Phase 0b windows: each window writes to its own `win-###.md` output file. The only coupling is the 120-word overlap tail (context from prior window's output), but this is read from the prior window's output file after it completes — ordering must be maintained for the overlap, but N-2 and N+1 windows are independent. Batches of non-adjacent windows can parallelize safely.
- Phase 0d source chapters: each chapter contract is generated from its own text slice with no cross-slice dependencies. All N source chapters can run concurrently.

**Projected speedup:**
- Phase 0b: master-and-the-disciple had 12 windows. At 10-min per window sequential = 120 min. With 3 concurrent workers = ~45 min (3× speedup). For a 20-chapter book with 20 windows: 200 min → 70 min.
- Phase 0d: 6 source chapters. At 30-min per chapter sequential = 180 min. With 3 concurrent = 70 min.
- Combined savings per book: ~2-3 hours of wall-clock time. For Kitab al-Riyad (14 chapters, 20+ Phase 0b windows), this is the difference between a 12-hour pipeline and an 8-hour pipeline.

**Proposed fix:**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

# Phase 0b — replace sequential loop with batched parallel:
with ThreadPoolExecutor(max_workers=3) as pool:
    futures = {pool.submit(_run_window, window_args): idx for idx, window_args in enumerate(windows)}
    for future in as_completed(futures):
        rc, out, err = future.result()
        # log + check rc; abort pool on failure
```

Phase 0b ordering constraint: windows with overlap must be processed in chunks where window N must complete before window N+1 reads its tail. Solution: process windows in batches of `max_workers` with a barrier between batches, or use a pipeline where each window's tail is computed from its input rather than its output (avoiding the dependency entirely).

**Rate-limit safety:** claude-opus-4-7 API tier supports concurrent calls. The per-window 10-min timeout provides natural back-pressure. If a rate-limit error occurs, fall back to sequential for the failed window and retry.

**Verification:** Run Phase 0b on a 12-window book with parallelism enabled. Confirm output is byte-identical to sequential run. Confirm wall-clock time is ~3× shorter. Confirm cost-ledger entries match (same total token count).

**Status:** **CLOSED (shipped 2026-05-25).** [_chunking.py:run_windowed()](../../scripts/podcast/_chunking.py) gains a `max_workers: int = 1` parameter (default = sequential, prior behavior). When > 1, work items are dispatched via `concurrent.futures.ThreadPoolExecutor`; threads release the GIL inside `subprocess.run()` so claude -p calls run in true parallel. Resume-skip logic (already-done windows) runs before queue dispatch so resumed runs are still cheap. Cost-ledger appends are protected by fcntl LOCK_EX (shared with F35 findings-ledger lock pattern). Failures + fatal_error use a `threading.Lock`. P5.1 (rc=0 + no artifact) raises fatal — pending futures cancelled. Defaults: PHASE_0B_MAX_WORKERS=3 (set via env), PHASE_0C_MAX_WORKERS=3. Phase 0d uses its own dispatch pattern (per-SC subprocess pool) and is unchanged.

---

### F35 — No per-chapter LLM cost ceiling

**Where:** `scripts/podcast/_convergence.py:converge_chapter()` and `scripts/podcast/orchestrate_book.py:per_chapter_pass()` — no cost check anywhere in the per-chapter pipeline.

**Worst case budget:** 3 outer iterations × 5 inner challenger iterations + 3 fixer attempts per outer = up to 15 challenger calls + 9 fixer calls per chapter. At avg $3.47 challenger + $0.36 fixer = $52.05 + $3.24 = **$55.29 per chapter at full iteration burn.** For a 14-chapter book, this is $774 if every chapter hits max iterations — with no operator warning.

**Empirical evidence (master-and-the-disciple, will-command-and-the-seven):** challenger=4 + fixer=6 + framing=2. Even before hitting the cap, this chapter burned ~$15-18. With 7 restarts on father-revealed, total chapter spend was ~$28-35.

**Proposed fix:**
1. Add `--chapter-cost-cap N` flag (default: $25).
2. At the start of each outer convergence iteration, query the cost ledger: sum all entries where `step` starts with `challenger/<slug>` or `fixer/<slug>` or `framing/<slug>` since the chapter started.
3. If accumulated cost exceeds cap: abort the convergence loop, mark chapter `FAILED` with `reason=cost_cap_exceeded`, surface to orchestrator.
4. Orchestrator logs the cap breach with the accumulated cost; watchdog surfaces to operator.
5. Operator can retry with `--chapter-cost-cap 40` if the chapter is worth more spend, or fix the systemic issue and retry at default cap.

**Why not just rely on the iter cap?** The iter cap (3 outer × 5 inner) is a *count* ceiling, not a *cost* ceiling. A chapter that takes 6 challenger passes and no fixers burns less than one that takes 3 challenger passes and 9 fixer-of-fixer passes. The cost ceiling is a budget guard independent of iteration count.

**Verification:** Set `--chapter-cost-cap 5` and run a chapter known to require 2+ challenger passes. Confirm the loop aborts after the first or second pass when the cap is reached. Confirm state.json shows `reason=cost_cap_exceeded` and the operator can resume with a higher cap.

**Status:** **CLOSED (shipped 2026-05-25).** Implemented per-chapter cap via series-plan.md flag `per_chapter_cost_cap_usd` (default $5.00) rather than CLI flag — fits the existing `_series_flag/_series_numeric` pattern. Loop reads `_chapter_cost_so_far(book_dir, slug)` from cost-ledger.jsonl before and after each `per_chapter_pass()`; if delta exceeds cap, marks chapter `FAILED` with note "COST-CAPPED: chapter spent $X.XX > cap $Y.YY". Composes with F33-second graceful-degrade: cost-capped chapter halts loop with summary; raise cap in series-plan.md and `--resume` to retry.

---

### F36 — Azure costs not tracked; docintel/translator/speech fields always $0.00

**Where:** `scripts/podcast/_azure.py` — Azure API calls for Document Intelligence (Phase 0a), Translator, and Speech TTS. `content/drafts/<slug>/_system/orchestrator-state.json` — `cost` object has the right fields but is never populated.

**Code confirmation:** `orchestrator-state.json` cost object:
```json
{"docintel_usd": 0.0, "translator_usd": 0.0, "speech_usd": 0.0, "anthropic_usd": 0.0, "total_usd": 0.0}
```
All zeros on every book. The pipeline never calls any `update_state(cost=...)` after Azure API calls.

**Actual Azure costs incurred (estimated for master-and-the-disciple):**
- Document Intelligence: ~200 pages × $0.015/page = ~$3.00 (Phase 0a)
- Azure Translator (Phase 0c): ~50,000 characters × $0.000015/char = ~$0.75
- Azure Speech TTS (if used): not used in this pipeline (NotebookLM handles TTS)
- **Total uncaptured: ~$3-4 per book** — invisible to operator

**Proposed fix:**
1. In `_azure.py:docintel_analyze_pdf()`: after the API response, read `result['pages']` count. Compute `cost = pages × 0.015`. Call `update_phase(book_dir, cost_delta={"docintel_usd": cost})`.
2. In Phase 0c translator calls: accumulate character count across all windows. After phase completes, compute `cost = chars × 0.000015`. Write to `cost.translator_usd`.
3. Add `update_phase(cost_delta={...})` to update state: read current cost, add delta, write back.
4. Heartbeat card shows the Azure cost as the running total from state.json (already does this — will auto-populate once fields are written).

**Verification:** Run Phase 0a on a 50-page test PDF. Confirm `orchestrator-state.json.cost.docintel_usd` shows ~$0.75 after the phase completes.

**Status:** **CLOSED (shipped 2026-05-25).** Three new helpers in [_cost_ledger.py](../../scripts/podcast/_cost_ledger.py): `append_azure_docintel_cost(book_dir, phase, step, pages)`, `append_azure_translator_cost(book_dir, phase, step, char_count)`, `append_azure_speech_cost(book_dir, phase, step, char_count)`. Pricing constants in `AZURE_PRICING_USD` dict at top of module. Callsites wired: [ingest_source.py](../../scripts/podcast/ingest_source.py) appends after `docintel_analyze_pdf` and `translate_text`; [translate_bundle.py](../../scripts/podcast/translate_bundle.py) appends after Phase 0c translation. Rows carry `model='azure-docintel-prebuilt-read' / 'azure-translator-text' / 'azure-speech-neural-tts'` so cross_book_dashboard.py shows Azure spend in the same cost_usd column as LLM spend (separable by model field). Cost-ledger append wrapped in try/except so a ledger failure never fails the intake.

---

### F37 — No per-chapter timing data in orchestrator state

**Where:** `scripts/podcast/orchestrate_book.py:_drive_per_chapter_and_after()` — state updates track only `phases.per-chapter.ts_started` (one timestamp for the whole phase). No per-chapter start/end timestamps.

**Impact:**
- Heartbeat `avg/ch` is computed as `elapsed_s / done` — inflated by retry cycles. For master-and-the-disciple: 19h elapsed / 5 done = 3h 49m avg, but clean chapters (the-call, justice) took ~1h 20m each; the 3h 49m avg is dominated by father-revealed's 7-restart cycle.
- No way to identify which chapters are slow without manually grepping the cost ledger.
- F35's cost ceiling implementation needs per-chapter cost tracking as its data source.
- ETA estimates are wrong when retry cycles inflate the average: "~3h 49m remaining" when the final chapter (a clean one) will likely take ~1h 20m.

**Proposed fix:** After `completed_chapter_slugs.add(slug)`, write per-chapter timing to state extras:
```python
update_phase(book_dir, phase="per-chapter", status="running", extras={
    "completed_slugs": sorted(completed_chapter_slugs),
    "chapter_timings": {
        **prior_timings,
        slug: {
            "started": chapter_start_iso,
            "completed": now_iso(),
            "duration_s": elapsed,
            "framing_calls": outcome.fixer_attempts,  # extend ChapterOutcome
            "challenger_calls": outcome.outer_iterations,
            "fixer_calls": outcome.fixer_attempts,
            "cost_usd": chapter_cost_from_ledger,
        }
    }
})
```

The heartbeat script reads `chapter_timings` and computes `avg` from completed (non-retried) chapters only, giving an accurate ETA for the remaining chapters.

**Verification:** Complete a 4-chapter run. Confirm `orchestrator-state.json.phases.per-chapter.chapter_timings` has 4 entries with accurate timestamps and call counts. Confirm heartbeat `avg/ch` shows per-chapter breakdown on demand.

**Status:** **CLOSED (shipped 2026-05-25).** [orchestrate_book.py:_drive_per_chapter_and_after()](../../scripts/podcast/orchestrate_book.py) now writes `phases.per-chapter.chapter_timings` with per-slug `{started_ts, completed_ts, duration_sec, verdict, cost_usd}` (cost from F35-second). Cross-book dashboard ([cross_book_dashboard.py](../../scripts/podcast/cross_book_dashboard.py)) surfaces mean chapter duration in the fleet table. Future heartbeat ETA can compute from clean-chapter timings only (excluding cost-capped/FAILED), giving accurate remaining-time estimates.

---

### F31 — No mid-book inter-chapter quality signal propagation

**Where:** `scripts/podcast/orchestrate_book.py` — the per-chapter loop (`_drive_per_chapter_and_after()`, lines ~1372-1419) and `scripts/podcast/_authoring.py:author_framing()` — the framing prompt builder.

**Code confirmation:** `author_framing()` reads exactly three inputs: `BOOK_DIR/chapter-contracts/<slug>.yml`, `BOOK_DIR/chapters/ch##-<slug>.txt`, and static rules from `scripts/podcast/_rules.py`. It reads no prior-chapter challenger findings, no health trend, no `_learning/findings.jsonl`. The per-chapter loop in `orchestrate_book.py` tracks `completed_chapter_slugs` (a set of slug strings) but passes nothing from completed chapters to the next slug's framing invocation — `author_framing(book_dir, slug)` is called with just `book_dir` and `slug`, no context bag. `invoke_trainer()` fires only after all chapters ship in the `publish → trainer → merge → done` pipeline — far too late to help in-flight chapters.

**What goes wrong:** When ch01 produces systemic P0/P1 findings (e.g., welcome-sentence missing every time, analogy cap always blown, framing word count always over), ch02–ch06's framing authors start from scratch with the same static prompt. The challenger on ch02 surfaces the same findings. The fixer addresses them per-chapter at full LLM cost. This pattern repeats across every chapter — paying the convergence loop's full price for the same mistake repeatedly instead of eliminating the root cause after the first chapter surfaces it.

**Concrete example (master-and-the-disciple):** If ch01 (the-call-and-the-covenant) produced a P1 for framing structure and ch02 (will-command-and-the-seven) repeated it, nothing in the pipeline notified ch03's (world-hereafter...) framing author to avoid the same structure. The failure mode compound linearly with chapter count: for a 14-chapter book (Kitab al-Riyad), a systemic P1 costs 14 challenger + 14 fixer passes that could have been 1 challenger + 1 framing-prompt fix.

**Distinction from the trainer:** The trainer (`invoke_trainer()`) runs post-publish, edits the spec (`_rules.py`, SKILL.md), and requires a regression gate — it's a cross-book learning mechanism that changes future books' rules. F31's fix is intra-book and runtime — no spec changes, no regression gate, just reading the prior chapter's finding IDs and injecting a brief "avoid these patterns" signal into the next framing prompt.

**Proposed fix — inter-chapter flash brief:**

In `_drive_per_chapter_and_after()`, after `completed_chapter_slugs.add(slug)` and before the next slug's `per_chapter_pass()`, add a 3-step flash brief:

```python
# After slug N completes:
prior_findings = _extract_prior_chapter_findings(book_dir, completed_chapter_slugs)
# prior_findings = list of (finding_id, severity, one-line-description) from last N chapters' challenger-report.md
# Inject into next chapter's author_framing() call via a new `prior_lessons` kwarg:
author_framing(book_dir, next_slug, prior_lessons=prior_findings)
```

`author_framing()` appends a ≤5-bullet block to the framing prompt:

```
Prior chapter lessons (apply to this framing, do not repeat these patterns):
- [P1-WELCOME-MISSING] ch01: opening sentence was not a direct question from Host A. Start with Host A's question.
- [P0-WORD-BAND] ch02: framing was 3,820 words — over the 3,500 hard cap. Self-check word count before returning.
```

The flash brief is capped at the top 5 P0+P1 findings from the most recent 2 completed chapters (more than that risks prompt bloat). It is advisory — the framing author may override with explicit justification. It is NOT a spec change.

**Second mechanism (parallel, simpler):** A systemic-P0 early-halt: if the SAME finding ID appears in ≥2 consecutive completed chapters, pause the per-chapter loop, surface the pattern to the operator, and offer a one-shot prompt fix before continuing. This is the signal the user described as "snowball effect" — catching a pattern after chapter 2 saves chapters 3-N.

**Priority:** High — the gap compounds linearly with book length. A 14-chapter book with one systemic P1 wastes 13 unnecessary fixer passes. At ~$8/fixer pass, that's ~$100 of avoidable spend per systemic finding per book.

**Verification:** Run a 4-chapter test book where ch01's framing deliberately violates the analogy cap (>5 analogies). Confirm ch02's framing prompt includes the flash brief mentioning the analogy cap violation. Confirm ch02's first challenger pass does NOT flag analogy cap (finding eliminated by the brief).

---

## How to use this file

When a new framework gap surfaces:
1. Add a row to the "Active framework debt" table at the top
2. Add the detail block to "Item details"
3. If it's a code patch that ships in the same session (like the X-class fixes), close it: move the row out of the active table, add to "Closed / shipped"
4. Commit on the active book branch; merge to develop with the next book ship

When triaging:
- **Severity High** — actively blocks a book in flight or wastes substantial operator time per episode
- **Severity Medium** — wastes operator time per book; would be felt on next book
- **Severity Low** — observed but mitigated; nice to fix when there's slack
