# Podcast Challenger Report — challenger v2.0

**Verdict:** SHIP-WITH-CAUTION
**Book:** kitab-al-riyad
**Chapter:** ch10-motion-stillness-hyle-and-form
**Episode:** EP10-motion-stillness-hyle-and-form
**Run:** 2026-05-22 (challenger v2.0)
**Scope:** per-chapter: motion-stillness-hyle-and-form
**Iterations:** 1 of 5 max — intelligent-break applied (0 auto-fixes; remaining findings require author resolution)
**Auto-fixes applied:** 0
**P0:** 0 | **P1:** 3 | **P2:** 1
**Score:** 0.35 (Caution)

---

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| — | — | — | No auto-fixes applied this run. No em-dashes, no repeated honorifics, no cross-episode refs, no exact-match filler tells. |

---

## Findings requiring author resolution

### P0 (blocks ship)

*None.*

---

### P1 (ship-with-caution)

#### N3-a: `*Al-hayula*` appears in chapter body without a Pronounce directive in framing

- **Signature:** `N3:al-hayula-unpronounced:ch10-motion-stillness-hyle-and-form:35`
- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch10-motion-stillness-hyle-and-form.txt`
- **Lines:** 35, 37, 77, 181, 185 (5 occurrences)
- **Context excerpt:** `*Al-hayula* is the *acted-upon*. Form *informs*. *Al-hayula receives*.`
- **Rule:** N3 — every transliterated Arabic term in the chapter must have a matching Pronounce directive in the framing Pronunciation block.
- **Problem:** The framing covers `hayle` (the English vernacular rendering) but `*Al-hayula*` is used 5 times as an italicized Arabic scholarly term. The framing's tone_constraints notes `al-hayula (al-ha-yoo-laa)` as needing phonetic guidance, but no `Pronounce "Al-hayula" as "..."` directive exists in the Pronunciation block. Without it the voice model has no instruction for this form.
- **Suggested fix:** Add to the framing Pronunciation block: `Pronounce "Al-hayula" as "al-ha-YOO-laa". Say it as four fluent syllables, accent on the third; this is the Arabic for prime matter. Do not spell it.` Then re-run `build_episode_txt.py` to sync the episode txt.
- **Severity:** P1.

---

#### N3-b: `*al-nafs*` appears in chapter body without a Pronounce directive in framing

- **Signature:** `N3:al-nafs-unpronounced:ch10-motion-stillness-hyle-and-form:57`
- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch10-motion-stillness-hyle-and-form.txt`
- **Line:** 57
- **Context excerpt:** `*Al-nafs* and *the spirit* are two synonyms for the same thing, and that thing is not a body.`
- **Rule:** N3 — every transliterated Arabic term in the chapter must have a matching Pronounce directive in the framing Pronunciation block.
- **Problem:** `*Al-nafs*` appears once at line 57 in the synonymy argument of sub-chapter three. The shared Arabic manifest lists `nafs` with canonical phonetic `nafs`, but the framing Pronunciation block carries no `Pronounce "Al-nafs"` directive.
- **Suggested fix:** Add to the framing Pronunciation block: `Pronounce "Al-nafs" as "al-NAFS". Say it as two fluent syllables; this is the Arabic for the soul as a technical term.`
- **Severity:** P1.

---

#### A4: Q16:40 translation attribution does not match Pickthall's actual rendering

- **Signature:** `A4:translation-mismatch:Q16-40:Pickthall:ch10-motion-stillness-hyle-and-form:105`
- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch10-motion-stillness-hyle-and-form.txt`
- **Line:** 105
- **Context excerpt:** `> *Our only word for a thing,when We will it,is that We say to it,"Be," and it is.* (Quran 16:40,Surah the chapter of the bee; translation rendered after Pickthall)`
- **Rule:** A4 — Quranic translations must be verbatim or clearly attributed; translator attribution must match the actual rendering used.
- **Problem:** Pickthall's actual Q16:40 reads "But Our commandment is but one (commandment), as the twinkling of an eye." The chapter's rendering ("Our only word for a thing, when We will it, is that We say to it, 'Be,' and it is") tracks Yusuf Ali's Q16:40 ("For to anything which We have willed, We but say the word, 'Be', and it is") much more closely than Pickthall. The "translation rendered after Pickthall" qualifier does not cover this divergence. The citation reference (Quran 16:40; Surah the chapter of the bee) is correct; only the translator attribution is in question.
- **Suggested fix:** Options: (a) re-attribute to Yusuf Ali if that is the source used; (b) replace with a literal rendering attributed to the author; (c) adjust the rendering to match Pickthall's actual Q16:40 text. Any of the three resolves the A4 concern.
- **Severity:** P1 — translator attribution mismatch; author should verify before upload.

---

### P2 (advisory)

#### F6: Canonical two-host-framing steering phrases not present verbatim

- **Signature:** `F6:steering-phrases-absent:EP10-motion-stillness-hyle-and-form`
- **File:** `content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP10-motion-stillness-hyle-and-form/00-framing.md`
- **Rule:** F6 — framing should carry at least one canonical steering phrase from two-host-framing.md ("Slow down on...", "Treat X as the central tension...", "End on a question...").
- **Note:** The Landing section has "Close on the unresolved tension and a question, not a recap" — semantically equivalent to "End on a question." The framing's pushback scripts and six-beat arc are dense and already specific. P2 advisory only; the framing can work without exact canonical phrases.
- **Severity:** P2 (advisory).

---

## Health metrics

| Chapter | Words | Band | In-band | Tiers | Blockquote ratio | Phonetic gaps | Framing words | Framing in-band |
|---|---|---|---|---|---|---|---|---|
| ch10-motion-stillness-hyle-and-form | 9,014 | extended (soft 5,500–9,500; hard 10,500) | YES | 4 | ~4% | 2 groups (Al-hayula ×5, al-nafs ×1) | 3,562 | PASS (cap 3,700) |

**Citation audit summary:**
- Quran 36:82 (line 99): A1/A3/A4 PASS — Pickthall named on first Quranic occurrence; rendering consistent.
- Quran 16:40 (line 105): A1 PASS (reference valid); A4 FAIL (P1) — translator attribution mismatch with Pickthall.
- Quran 112:1-4 (line 149): A1/A4 PASS.
- Quran 42:11 (line 163): A1 PASS; A4 advisory (rendering departs from Pickthall but "rendered after" qualifier noted).
- Nahj al-Balagha Sermon 1 (line 137): A1 functional (English title wrapper, sermon number present); A2 PASS. P2 advisory on format.
- Sahih al-Bukhari Book 59 Hadith 3191 (line 143): A1 PASS; A2 PASS. The hadith is authentic and the citation is complete.

**Honorific audit (O1/C3):** Two honorifics, one per figure, on first occurrence only. PASS.

**Structural gates summary:** B1/B2/B3 — PASS. N1/N2/N4 — PASS. M1/M2 — PASS. H1/H2/H3/H5 — PASS. I1/I2 — PASS. K1/K2 — PASS. R1-R5 — PASS. F2/F4 — PASS. G1/G3/G4 — PASS. A5/A6/D1/D2/D4/E1/E2/E3/E4 — PASS. S1/S2/S5 — PASS. Category P (debate format): not applicable (deep_dive). Transcript checks M3/M4/N5/O3/R6/R7: no transcript present, skipped.

---

## Score

**P0:** 0 | **P1:** 3 | **P2:** 1 | **Chapters in scope:** 1 | **Auto-fixes this run:** 0

```
penalty = (0 × 1.0 + 3 × 0.2 + 1 × 0.05) = 0.0 + 0.6 + 0.05 = 0.65
score   = max(0.0, 1.0 - 0.65) = 0.35  (Caution)
```

**Verdict: SHIP-WITH-CAUTION** — 0 P0 findings. 3 P1 findings require author resolution before upload: N3-a (Al-hayula Pronounce gap), N3-b (al-nafs Pronounce gap), A4 (Q16:40 translator attribution). Episode txt is structurally valid and in sync. The chapter is not blocked — upload can proceed after the P1 items are addressed.

---

*Report generated by podcast-challenger v2.0. Per-chapter scope: motion-stillness-hyle-and-form.*

STALE_CONTENT_MARKER_DO_NOT_SHIP

- **Signature:** `F5:discussion-spine-unfilled:EP10-motion-stillness-hyle-and-form`
- **File:** `content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP10-motion-stillness-hyle-and-form/04-discussion-spine.md`
- **Line:** null (whole file)
- **Context excerpt:** All 8 beats contain `[LLM-FILL]` in Key question, Tension, Anchor passage, and Landing fields.
- **Rule:** F5 — discussion spine must have 6–12 beats with substantive content.
- **Note:** The spine is a sidecar document and does NOT feed into the episode txt. The framing (`00-framing.md`) is fully authored with a rich six-beat arc, four tensions with pushback scripts, and a complete Landing directive. The generated audio is not at risk from the unfilled spine. However, the pipeline contract requires authored spines as documentation.
- **Severity:** P1 — the episode can be generated without this; it is pipeline hygiene.

---

#### N3: Arabic surah names in chapter prose without Pronounce directives in framing

- **Signature:** `N3:surah-names-unpronounced:Surat-Ya-Sin-Surat-an-Nahl:ch10:97-103`
- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch10-motion-stillness-hyle-and-form.txt`
- **Line:** 97, 103
- **Context excerpt:** Line 97: `runs through the *Surat Ya Sin*:` / Line 103: `*Surat an-Nahl*, where the *Be* of Allah`
- **Rule:** N3 — every transliterated Arabic term in the chapter must have a matching `Pronounce "..."` directive in the framing's Pronunciation block.
- **Problem:** `*Surat Ya Sin*` (line 97) and `*Surat an-Nahl*` (line 103) are Arabic surah names left in the chapter source. The framing's `## Do not` block tells hosts not to speak Arabic surah names and to use English descriptions instead. But there are no Pronounce directives for `Ya Sin` or `an-Nahl` in the framing's `## Pronunciation` block to guide the voice model if it does encounter them. This is a gap between the chapter content and the framing's coverage. Note: lines 147 and 161 use English-translated forms (`*Surat the chapter on sincerity*`, `*Surat the chapter on consultation*`) — the consistency of surah-naming should be reviewed across the chapter.
- **Suggested fix (option A):** Add `Pronounce "Ya Sin" as "YAA-seen". Say it as two fluent syllables.` and `Pronounce "an-Nahl" as "an-NAHL". Say it as two fluent syllables.` to the framing's Pronunciation block.
- **Suggested fix (option B):** Replace `*Surat Ya Sin*` with `*the chapter of the mystic letters*` or `*the chapter that opens "Ya Sin"*` (an English description consistent with lines 147 and 161), and replace `*Surat an-Nahl*` with `*the chapter of the bee*`. Option B is more consistent with the book's TTS strategy and with the framing's `## Do not` instruction.
- **Severity:** P1 — audible risk of mispronunciation or host reading an Arabic name the framing tells them not to say.

---

#### N3: Arabic technical terms in chapter prose without Pronounce directives

- **Signature:** `N3:mawhumiya-takhayyuliya-unpronounced:ch10:87`
- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch10-motion-stillness-hyle-and-form.txt`
- **Line:** 87
- **Context excerpt:** `considered as the act of the divine command, are *imaginary* (*mawhumiya*, *takhayyuliya*).`
- **Rule:** N3 — every transliterated Arabic term in the chapter must have a matching `Pronounce "..."` directive in the framing.
- **Problem:** `*mawhumiya*` and `*takhayyuliya*` are Arabic technical terms (meaning "imaginary/illusory" and "of the imagination") that appear in the chapter without corresponding Pronounce directives in the framing.
- **Suggested fix:** Either (a) add Pronounce directives: `Pronounce "mawhumiya" as "maw-hoo-MEE-yah"` and `Pronounce "takhayyuliya" as "ta-khay-yoo-LEE-yah"` to the framing's Pronunciation block; or (b) replace these terms with their English equivalents in the chapter text (e.g., `*imaginary* (of the imagination, illusory)`) per the substitution policy. Given the book's English-substitution strategy, option (b) is preferred.
- **Severity:** P1 — minor risk of mispronunciation; the terms are in parentheses and may be skipped by the hosts, but the gap is real.

---

#### J3/R-NAMEDISCIPLINE: Framing uses stable single-label approach; no rotation sets present

- **Signature:** `J3:no-rotation-sets:EP10-motion-stillness-hyle-and-form`
- **File:** `content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP10-motion-stillness-hyle-and-form/00-framing.md`
- **Line:** 43–62 (`## Stable role-labels` section)
- **Context excerpt:** `Apply R-STABLE-ROLE-LABELS strictly. Each figure gets EXACTLY ONE English label and that label is used every time. The label does not rotate.`
- **Rule:** J3/R-NAMEDISCIPLINE — the framing must carry rotation sets (3+ English aliases per Arabic figure separated by `/`).
- **Problem:** The framing uses a "stable label" architecture (one fixed English label per figure, no rotation) instead of the rotation-set architecture R-NAMEDISCIPLINE prescribes. Per R-NAMEDISCIPLINE, `Rotation: alias1 / alias2 / alias3 / alias4` lines are required.
- **Mitigation note:** The stable-label approach is arguably STRICTER than rotation — it forbids all Arabic figure names after first mention and requires a consistent English label every time. The empirical motivation for R-NAMEDISCIPLINE (Arabic name drift across a transcript) is fully addressed by the stable-label policy. The challenger flags this per the spec but notes that the stable-label approach may satisfy the R-NAMEDISCIPLINE objective more cleanly than rotation for this chapter's figures, none of whom have 3–4 natural English aliases available.
- **Suggested fix:** Either (a) add rotation sets to the `## Stable role-labels` section for each Arabic figure (e.g., for the author: "the author / the philosopher / our thinker / the adjudicator") while maintaining the stable-label-first policy; or (b) document a deliberate design note in `00-framing.md` explaining why single-label is preferred over rotation for this chapter, and propose a policy amendment for Kitab al-Riyad's figures.
- **Agent recommendation for escalation:** The spec rates this P1, but the stable-label architecture plausibly achieves the R-NAMEDISCIPLINE goal. The author may wish to review whether rotation adds value for these specific figures.
- **Severity:** P1 per spec.

---

### P2 (advisory)

#### A1 (advisory): Nahj al-Balagha citation uses English title wrapper rather than canonical format

- **Signature:** `A1:advisory:nahj-english-title:ch10:137`
- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch10-motion-stillness-hyle-and-form.txt`
- **Line:** 137
- **Context excerpt:** `(the book *The Path of Eloquence*, Sermon 1)`
- **Rule:** A1 advisory — Imam Ali sayings should cite `(Nahj al-Balagha, Sermon/Letter/Aphorism N)`.
- **Note:** The chapter's TTS strategy replaces all Arabic book titles with English wrappers. The citation `(the book *The Path of Eloquence*, Sermon 1)` contains the required content (work identity + sermon number) in TTS-safe form. This is a deliberate design choice consistent with the book's strategy. Not a material violation but deviates from the canonical citation format.
- **Severity:** P2 (advisory only — citation is functional and TTS-safe).

---

#### F3 (advisory): No explicit Audience section in framing

- **Signature:** `F3:advisory:no-audience-section:EP10-motion-stillness-hyle-and-form`
- **File:** `content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP10-motion-stillness-hyle-and-form/00-framing.md`
- **Rule:** F3 — framing should name the audience concretely.
- **Note:** The audience is defined in detail in `chapter-contracts/motion-stillness-hyle-and-form.yml` (`audience:` field) and the `## Background` section of the framing refers to the argumentative chain the audience has followed. There is no dedicated `## Audience` section in `00-framing.md`. This is a pipeline hygiene gap, not a quality risk to the generated audio.
- **Severity:** P2 (advisory only).

---

## Health metrics

| Chapter | Words | Band | Band limits | In-band | Tiers | Blockquote ratio | Phonetic gaps | Framing words | Framing cap |
|---|---|---|---|---|---|---|---|---|---|
| ch10-motion-stillness-hyle-and-form | 9,009 | extended | 5,500–9,500 soft / 10,500 hard | IN SOFT BAND | 4 (Quran, Sunni hadith, Imam Ali/Nahj, al-Kirmani primary) | ~4% | 2 gaps (surah names + mawhumiya/takhayyuliya) | 3,444 | PASS (cap 3,700) |

**Word-count note (E1):** 9,009 words; `length_target: extended`; Extended soft band 5,500–9,500 words. Within soft band. `CHAPTER_WORD_MAX_HARD = 10,500`. PASS. Framing at 3,444 words; `FRAMING_WORD_MAX = 3,700`. PASS (256 words headroom).

**Tier diversity (D1):** Quran (Tier 2) — 4 citations (36:82, 16:40, 112:1-4, 42:11) with translator named on first occurrence. Sahih al-Bukhari (Tier 3) — line 143 (corrupted; actual collection identified as Sahih al-Bukhari). Nahj al-Balagha / Imam Ali (Tier 4) — line 137 with work + sermon number. al-Kirmani's own treatises (Tier 1 — primary source) — *The Repose of the Intellect*, *Milestones of Religion*, *With Lamps* — referenced in the chapter as the standing architecture. 4 tiers present. D1 PASS (note: corrupted Bukhari citation needs correction before tier-3 presence is clean).

**Citation audit:**
- Quran 36:82 (line 99): A1 PASS; A3 PASS — translator `rendered after Pickthall` named on first Quranic occurrence.
- Quran 16:40 (line 105): A1 PASS — subsequent Quranic occurrence, translator inherits.
- Quran 112:1–4 (line 149): A1 PASS.
- Quran 42:11 (line 163): A1 PASS.
- Nahj al-Balagha Sermon 1 (line 137): A1 advisory (P2) — English title used instead of canonical Arabic title; sermon number present. A2 PASS (authentic quote verified against standard translation).
- Hadith (line 143): **A1/A2 FAIL (P0)** — `Sahih the canonical hadith compiler` is a corrupted placeholder. Correct to `Sahih al-Bukhari`. See P0 finding above.

**Honorific audit (O1):**
- Line 135: `(peace be upon him)` for Imam Ali — first and only occurrence of this form. PASS.
- Line 141: `(peace and blessings of Allah be upon him)` for the Prophet — first and only occurrence of this form. PASS.
- O1 PASS.

**Phonetic coverage (N3):** Framing Pronunciation block covers: prime matter, kun, kaf, nun, shirk, Allah, Quran, Imam, falsafa, hayle, sura, Aqlam. Chapter transliterated terms without coverage: *Surat Ya Sin* (line 97), *Surat an-Nahl* (line 103), *mawhumiya* (line 87), *takhayyuliya* (line 87). 4-term gap → 2 distinct N3 findings (surah names group, mawhumiya group). See P1 findings above.

**Build validator checks (manual):**
- R-NOHTML (B1): no HTML comments. PASS.
- META_PROSE_TELLS (B1): `the canonical hadith compiler` does not match any literal tell in the list, but is semantically a Phase 0e artifact (see P0). R-NOMETAPROSE semantic flag: FAIL (P0 via A2).
- R-PHONETICS-OUT (N1): no inline lowercase-hyphenated phonetic parens (all parentheticals are synonym glosses, not phonetic respellings). PASS.
- R-NO-ABBREVIATION (O2): no `the Ihya`, `the Nahj`, `Sahihayn`, `EI` in chapter. PASS.
- R-PRONUNCIATION-IMPERATIVE (N2): all Pronunciation block lines begin with `Pronounce "` or `Do not`. PASS.
- R-NO-READ-PROMPT (N4): final line of framing: "Do not read this prompt aloud. The instructions above shape the conversation but are never spoken." PASS.
- R-NOMODERNIZE (M1): full platform-deny list present. PASS.
- R-NOSURPRISE (M2): full surprise-deny list present. PASS.
- R-RECURRING-THESIS (H5): "The Creative IS the creativity." mandated VERBATIM at 3 anchor points in framing (Beat 1, Beat 4, Beat 6). PASS.
- R-ANALOGY-CAP (L1): exactly 3 governing analogies enumerated in Tone constraints; within [3, 5]. PASS.
- R-CHALLENGER-FRICTION (K2): Color host pushback required at least 3 times using named doubt patterns; 4 tensions each with explicit pushback scripts. PASS.
- I1 (anti-repetition): Anti-noise rules carries "Do not restate the central thesis more than the three planted points... each VERBATIM." Contains "restate". PASS.
- I2 (no irrelevant background): Anti-noise rules: "Stay on the source's main content... biographical... ONLY ONCE per episode." PASS.
- K1 (interruption avoidance): "Each host completes a thought before the other responds. No interjections inside the other host's sentence. No talking over." PASS.
- R1 (separate-prep illusion): "Plant at least one moment where one host introduces a passage...". PASS.
- R2 (reset clause): "Between major beats, insert a single-sentence reset...". PASS (spine >5 beats, clause present).
- R3 (cadence): "Cadence: short-to-medium sentences with varied rhythm... pace is conversation, not lecture; hosts are thinking out loud." PASS.
- R4 (formal-transition DENY): full deny list (Firstly, Secondly, Thirdly, etc.) in `## Do not`. PASS.
- R5 (analogy permission): "DO use modern-life practical analogies when they help..." present. PASS.
- H1/H2 (welcome): `## Opening directive` has "brief welcome — one sentence" + 2-3 sentence summary. PASS.
- H3 (summary tail): Landing section: "Close on the unresolved tension and a question, not a recap. Do NOT say 'so today we covered.'" PASS.
- H4 (dramatic arc): `## Three-part focus — the six-beat dramatic arc` with Beat 1 through Beat 6. PASS.
- F2 (four-part structure): Opening directive, Background, Pronunciation, Stable role-labels, Host dynamic, Conversation choreography, Central tensions, Three-part focus, Tone constraints, R-NOMODERNIZE, Do not, Anti-noise rules, Landing. PASS.
- F4 (4 tensions): 4 named specific tensions with pushback scripts. PASS.
- F5 (discussion spine): 8 beats present but ALL `[LLM-FILL]` — beat count valid, content absent. P1 (see finding above).
- F6 (steering phrases): Landing: "Close on the unresolved tension and a question, not a recap." Advisory equivalent to "End on a question...". PASS (P2 advisory met).

**Category G (chapter contracts):**
- G1: contract `motion-stillness-hyle-and-form.yml` present. PASS.
- G2: `angle: faithful_exposition`, `episode_format: deep_dive`, `length_target: extended`, `debate: null`, `host_dynamic: curious_mind + scholar_companion`. All required fields present; enum values valid. PASS (note: cannot run extract_chapter.py to validate exit status — Python execution blocked in this environment).
- G3: No EP## refs or meta-prose tells detected in contract fields. PASS.
- G4: No `derived_from:` field — not a derivative. PASS.

**Category Q (chapter-set, per-book — per-chapter invocation; book-scope deferred):**
- Q2: Title "Motion, Stillness, *al-Hayula*, and Form" (from contract) — 5 words + 1 Arabic italic term; char count ~42. Under 60-char hard cap. PASS.
- Q3: Not generic. PASS.
- Q4: 9,009 words; `length_target: extended`. Extended soft band 5,500–9,500. IN BAND. PASS.

**Category S (safety):**
- S1: No active orchestrator process; `phase_status: running` is stale (13 min old, no process). Not HALT.
- S2: No `content/babu-memoir/` paths in chapter or framing. PASS.
- S5: Modified files (cost-ledger.jsonl, orchestrator-state.json) are within book scope; not in scope_out. PASS.

**Checks skipped (no transcript present for EP10):** M3, M4, N5, O3, R6, R7, P12, P13.

---

## Score

**P0:** 1 | **P1:** 5 | **P2:** 2 | **Chapters in scope:** 1 | **Auto-fixes this run:** 0

```
penalty = (1 × 1.0 + 5 × 0.2 + 2 × 0.05) / 1 = (1.0 + 1.0 + 0.1) / 1 = 2.1
score   = max(0.0, 1.0 - 2.1) = 0.00  (Unstable)
```

**Verdict: BLOCKED** — 1 P0 finding (corrupted hadith citation). 5 P1 findings remain. Do NOT upload this episode until the P0 is resolved.

---

## Blocking P0 items (max 5 — all P0 items listed)

1. **A2/A1 — Corrupted hadith citation** (`ch10-motion-stillness-hyle-and-form.txt`, lines 141–143): Phase 0e template variable `the canonical hadith compiler` was not resolved. Prose reads "Imam the canonical hadith compiler" and citation reads "Sahih the canonical hadith compiler". Correct both to "Imam Muhammad al-Bukhari" and "Sahih al-Bukhari" respectively.

**Caller contract:** Fix the P0 item above, then re-invoke the challenger. The outer loop should surface to human if two consecutive invocations produce identical P0 count.

---

## Fixer-pass notes (2026-05-22, P1 sweep)

- **P0 (A2/A1 hadith citation):** Already resolved in the chapter file (lines 141 and 143 read `Imam Muhammad al-Bukhari` and `Sahih al-Bukhari` — the Phase 0e placeholder is no longer present). Report excerpt was stale.
- **P1 B1 (line 79 garbled italic):** Fixed. Replaced `by origination at *dar an earlier work on origination'*` with `by origination` (option c — cleanest TTS-safe reading; avoids introducing a new Arabic term that would need a Pronounce directive).
- **P1 N3 (surah names Ya Sin / an-Nahl):** Fixed via option B. Lines 97/99 → `*Surat the chapter of the mystic letters*` / `Surah the chapter of the mystic letters`; lines 103/105 → `*Surat the chapter of the bee*` / `Surah the chapter of the bee`. Pattern matches existing lines 147/161 (sincerity / consultation). Citation lines updated for consistency.
- **P1 N3 (mawhumiya / takhayyuliya):** Fixed via option (b). Line 87 now reads `*imaginary* (of the imagination,illusory)` — English equivalents per the substitution policy.
