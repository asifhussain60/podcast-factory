# Podcast Challenger Report

**Book:** ayyuhal-walad
**Run:** 2026-05-17 (podcast-challenger agent run, v1.4)
**Scope:** per-book sweep (5 chapters + 5 framings, all in scope)
**Iterations:** 2 (of 5 max; intelligent-break per Section 4.6b)
**Verdict:** SHIP-WITH-CAUTION

---

## Convergence summary

| Iter | Auto-fixes applied | P0 | P1 | P2 | Break reason |
|---|---|---|---|---|---|
| 1 | 23 | 0 | 5 | 1 | (proceed) |
| 2 | 0 | 0 | 5 | 1 | Intelligent break: (P0, P1) identical to iter 1 AND zero auto-fixes |

All 5 episode txts rebuilt clean via `build_episode_txt.py` post-iter-1. The build script structural gates pass: no HTML comments, no meta-prose tells, no inline phonetic parens, no abbreviated work titles, no parenthetical-honorific repeats, all framings carry imperative Pronunciation block + canonical `## Do not` DENY block + no-read-aloud guard, all chapter and framing word counts inside hard bands.

The honorific work was the load-bearing fix. Producer self-audit had assumed honorific discipline was clean because the build script's `HONORIFIC_PHRASES` regex requires parentheses, which the chapter prose form does not use. The R-HONORIFIC-ONCE rule itself (and Loop O1 in the catalog) covers any expansion form — parenthetical or prose appositive. Empirically, NotebookLM reads both forms aloud, so both must collapse to one expansion per chapter.

---

## Auto-fixes applied (iteration 1)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch01-frame-and-first-counsel.txt:17 | Stripped "peace and blessings be upon him" (2nd expansion; first at line 9 preserved) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch01-frame-and-first-counsel.txt:48 | Stripped "peace and blessings be upon him" (3rd expansion) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch01-frame-and-first-counsel.txt:89 | Stripped "peace and blessings be upon him" (4th expansion) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch01-frame-and-first-counsel.txt:117 | Stripped "peace and blessings be upon him" (5th expansion) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch01-frame-and-first-counsel.txt:137 | Stripped "peace and blessings be upon him" (6th expansion) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch01-frame-and-first-counsel.txt:97 | Stripped "(may Allah have mercy upon him)" on Hasan al-Basri (2nd expansion; first at line 7 on Ghazali preserved) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch01-frame-and-first-counsel.txt:127 | Stripped "(may Allah have mercy upon him)" on Sufyan al-Thawri (3rd expansion) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch01-frame-and-first-counsel.txt:169 | Stripped "(may Allah have mercy upon him)" on Shibli (4th expansion) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch02-hatim-eight-benefits.txt:84 | Stripped "peace and blessings be upon him" (2nd expansion; first at line 44 preserved) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch02-hatim-eight-benefits.txt:118 | Stripped "peace and blessings be upon him" (3rd expansion) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch02-hatim-eight-benefits.txt:156 | Stripped "peace and blessings be upon him" (4th expansion) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch03-the-path.txt:27 | Stripped "peace and blessings be upon him" (2nd expansion; first at line 19 preserved) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch03-the-path.txt:127 | Stripped "peace and blessings be upon him" (3rd expansion) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch03-the-path.txt:142 | Stripped "peace and blessings be upon him" (4th expansion) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch03-the-path.txt:172 | Stripped "peace be upon him" for Khidr and Musa pair (2nd/3rd expansion; first at line 79 on Imam Ali preserved) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch04-four-cautions.txt:49 | Stripped "peace and blessings be upon him" (2nd expansion; first at line 25 preserved) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch04-four-cautions.txt:64 | Stripped "peace be upon him" on Prophet Isa (2nd expansion of the form; first at line 47 preserved) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch04-four-cautions.txt:104 | Stripped "peace be upon him" on Imam Ali (3rd expansion of the form) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch05-method-and-closing-prayer.txt:32 | Stripped "peace and blessings be upon him" (2nd expansion; first at line 21 preserved) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch05-method-and-closing-prayer.txt:62 | Stripped "peace and blessings of Allah be upon him" (3rd expansion) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch05-method-and-closing-prayer.txt:75 | Stripped "peace and blessings of Allah be upon him" (4th expansion) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch05-method-and-closing-prayer.txt:86 | Stripped "peace and blessings be upon him" (5th expansion) |
| 1 | O1 / R-HONORIFIC-ONCE | chapters/ch05-method-and-closing-prayer.txt:97 | Stripped "peace and blessings be upon him" (6th expansion) AND "peace be upon him" on Imam Zayn (2nd expansion of that form; first at line 43 on Imam Ali preserved) |
| 1 | N3 / R-PRONUNCIATION-IMPERATIVE | _system/episode-drafts/EP02-hatim-eight-benefits/00-framing.md:78 | Inserted `Pronounce "farman" as "far-maan"...` (term in ch02 line 102; canonical phonetic from shared manifest §9) |

Total auto-fixes iteration 1: **23 stripped honorific repeats across 5 chapters + 1 Pronounce-line gap-fill in EP02 framing**.

All 5 episode txts rebuilt via `build_episode_txt.py` after auto-fixes; all pass structural validation.

---

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### P1-1: Two verbatim-blockquote honorific expansions preserved (R-HONORIFIC-ONCE vs A4 trade-off)

After applying the auto-fix strip across 5 chapters, two residual honorific expansions remain inside **verbatim source blockquotes**:

- **chapters/ch03-the-path.txt:33** — `> This person should have acquired a light from the lights of the Messenger of Allah, peace and blessings be upon him.` This is a verbatim Ghazali quote (the description of the perfected guide). Stripping the honorific from inside a verbatim blockquote violates A4 (verbatim quote integrity). Result: ch03 has 2 prose-form "peace and blessings be upon him" expansions (line 19 first mention + line 33 verbatim blockquote).
- **chapters/ch05-method-and-closing-prayer.txt:107** — `> ...descend upon Muhammad, peace and blessings be upon him, who is the best of all creations...` This is inside the verbatim closing supplication that Ghazali asks the student to recite after every prayer. The full supplication is the chapter's load-bearing closing artifact. Stripping the honorific from the supplication body would change the prayer. Result: ch05 has 2 prose-form expansions (line 21 first mention + line 107 verbatim supplication).

**Suggested fix (author judgment):** either accept these two residual expansions as the price of A4 verbatim integrity (the listener will hear the honorific repeated once, which is mild), or paraphrase the line slightly so the honorific is dropped (e.g., line 33 → "This person should have acquired a light from the lights of the Messenger of Allah."; line 107 → leave the supplication blockquote intact, since changing the words of a quoted prayer is the worse violation). Agent recommends **accepting both as preserved** — the verbatim integrity is more important than the marginal honorific drift.

#### P1-2: Framing word counts above the soft band (E1)

All 5 framings land at 1,629–1,954 words (and 1,580–1,896 in the rendered episode txt), above the catalog's soft band of 200–1,000 words for framings. They are well inside the build script's hard band (150–2,000) and inside the typical NotebookLM customize-prompt size that practitioners report works, but the catalog's soft target is meaningfully lower.

- _system/episode-drafts/EP01-frame-and-first-counsel/00-framing.md: 1,954 words → episode 1,896 words
- _system/episode-drafts/EP02-hatim-eight-benefits/00-framing.md: 1,629 words → episode 1,590 words (post-iter-1 with new `Pronounce "farman"` line)
- _system/episode-drafts/EP03-the-path/00-framing.md: 1,785 words → episode 1,736 words
- _system/episode-drafts/EP04-four-cautions/00-framing.md: 1,689 words → episode 1,640 words
- _system/episode-drafts/EP05-method-and-closing-prayer/00-framing.md: 1,773 words → episode 1,724 words

**Suggested fix:** the framings carry full Central tensions + Three-part focus + extensive Pronunciation blocks + canonical Do-not lists. Three places to consider trimming: (a) the duplicated boilerplate `## Do not` section (`Do NOT modernize`, `Do NOT perform surprise`, `Do NOT abbreviate`, `Do NOT restate`, `Stay on the source's main content`) is ~250 words per framing and is identical across all 5 — could be factored into a shared "appendix" the author maintains separately, then the per-framing version refers to the canonical block. (b) The Pronunciation lists are 25–30 lines per framing; trim to terms that actually appear in the matched chapter. (c) Background and Audience sections could be tighter. The agent does not auto-fix this — trimming the framing is an authoring decision about what NotebookLM most needs to see.

#### P1-3: `qudsi` italicized in ch05 with no framing Pronounce line (N3)

- **File:** chapters/ch05-method-and-closing-prayer.txt:32 — `Ghazali quotes a hadith *qudsi*, ...`
- **Context:** `qudsi` is italicized as a transliterated Arabic term; per N3, every italicized Arabic term in the chapter should have a matching `Pronounce "..."` line in the framing. The term is not in `content/_shared/arabic/03-arabic-english-manifest.md` and not in `_system/source/text/_phonetics.md` either.
- **Suggested fix:** add `qudsi` to the shared manifest (canonical phonetic: `**qud-see**`, plain English: "divine, sacred", as in "a hadith spoken by Allah through the Prophet") and add `Pronounce "qudsi" as "qud-see". Say it as one fluent word.` to EP05's Pronunciation block. Author authoring decision; agent does not auto-fix terms unknown to the manifest.

#### P1-4: `nafs` kept in ch02 without documented justification in framing (C4)

- **Files:** chapters/ch02-hatim-eight-benefits.txt:53, 55, 64.
- **Context:** Lines 53 and 64 are verbatim Haatim blockquotes (acceptable under §3 verbatim-quote exception). Line 55 is chapter prose: *"In Sufi technical vocabulary, the nafs is the part of you that pulls toward base appetite..."* — which itself functions as an inline gloss / technical-vocabulary definition, satisfying the substitution-policy exception (1)+(5). However: `_system/editorial-notes.md` line 22 states *"Kept by exception: nafs in ch01 only at the one moment where the source explicitly defines it as the technical Sufi term"* — which contradicts the actual ch02 chapter content. The editorial-notes file is out of sync with the chapter. The EP02 framing's `## Pronunciation` block includes `Pronounce "Nafs"` but does not document the keep-rationale.
- **Suggested fix:** either (a) update `_system/editorial-notes.md` to acknowledge that `nafs` is also kept in ch02 (with the gloss at line 55 satisfying the exception), OR (b) add a one-line justification to EP02's framing Pronunciation block ("Keep *nafs* in this chapter — the source's definition of the Sufi tripartite-soul vocabulary is the load-bearing beat of Benefit Two"). Author judgment.

#### P1-5: Per-form vs per-figure honorific ambiguity (catalog O1 vs build script vs R-HONORIFIC-ONCE rule text)

This is a structural ambiguity that surfaced during auto-fix. The R-HONORIFIC-ONCE rule text says *"exactly once per chapter, on first mention of each figure"* (per-figure semantics). The catalog O1 detection and the build script's `assert_honorifics_once_only` use *"each honorific phrase form expanded at most once per chapter"* (per-form semantics, regardless of figure). The agent applied the **stricter per-form** reading (aligned with build script enforcement) on the empirical grounds cited in the rule ("9 expansions in a single audited episode" = aggregate count). This means: ch01's `(may Allah have mercy upon him)` was stripped from Hasan al-Basri, Sufyan, and Shibli (3 different deceased Sufi figures) even though each was a first-mention; only Ghazali (line 7, first occurrence of the form) keeps the honorific. Same on ch03 Khidr+Musa and ch04 Imam Ali under `peace be upon him`.

The listener still gets each figure's name in full; they just don't get the honorific phrase for the 2nd+ figure in the chapter. If this feels listener-hostile, the alternative is to relax R-HONORIFIC-ONCE to per-figure-per-form (which would require code changes to `assert_honorifics_once_only` in `build_episode_txt.py` and the catalog O1 detection in the agent contract).

**Suggested fix:** decide which semantics is canonical and update either the rule text (currently leans per-figure) OR the build script + catalog (currently per-form). For this run the per-form reading was applied; if Asif intends per-figure, the residual stripped honorifics on the 2nd+ deceased Sufi / Imam / Prophet should be restored. Agent recommends keeping the per-form reading (it's the empirically-grounded one, matches build-script enforcement, and the per-figure reading was not what the audit actually counted) and updating the rule text to match.

### P2 (advisory)

#### P2-1: ch01 quote stack (D4)

- **File:** chapters/ch01-frame-and-first-counsel.txt:39–46.
- **Context:** Three Quranic blockquotes stacked back-to-back (99:7-8, 18:110, 18:107) with only minimal bridging prose. Stack is intentional — Ghazali's rhetorical move; the chapter explicitly names the pattern on the next line ("The pattern is unmistakable. The Quran does not separate believing from doing."). Prior workspace also marked this P2 ADVISORY and accepted.
- **Suggested action:** none. Acknowledged authorial choice; carries through to NotebookLM as intended structure.

---

## Health metrics

| Chapter | Words | Episode words | Enrichment % (blockquote-based) | Citations (Quran + hadith) | Phonetic gaps | Honorific expansions (post-fix) | Em-dashes |
|---|---|---|---|---|---|---|---|
| ch01-frame-and-first-counsel | 3,042 | 1,896 | 20% | 8 Quran + 0 named-hadith ref | 0 | 1 prose "peace and blessings" + 1 "(may Allah have mercy upon him)" + 1 "peace be upon him" (Imam Ali) | 0 |
| ch02-hatim-eight-benefits | 2,561 | 1,590 | 39% | 16 Quran + 5 hadith | 0 (after `farman` added to EP02) | 1 + 1 + 0 | 0 |
| ch03-the-path | 3,049 | 1,736 | 14% | 4 Quran + 2 hadith | 0 | **2** (1 first-mention + 1 verbatim blockquote at line 33) + 0 + 1 (Imam Ali line 79) | 0 |
| ch04-four-cautions | 2,738 | 1,640 | 13% | 3 Quran + 4 hadith | 0 | 1 + 0 + 1 (Prophet Isa line 47) | 0 |
| ch05-method-and-closing-prayer | 2,680 | 1,724 | 24% | 0 Quran direct + 7 hadith refs | 1 (`qudsi` not in framing) | **2** (1 first-mention + 1 verbatim supplication at line 107) + 1 (Aisha) + 1 (Imam Ali) | 0 |

**Cross-chapter variance:** 3,049 vs 2,561 = 19% — within the ±30% balance target.

**Tier diversity (D1):** all 5 chapters draw on ≥4 of the 7 enrichment tiers (Tier 1 Quran, Tier 2 Sunni hadith, Tier 3 Imam Ali AS via Nahj al-Balagha + Ghurar al-Hikam, Tier 4 Ismaili tradition via Aga Khan IV + Holy Du'a + Sahifa al-Sajjadiyya, Tier 6 Sufi voices via Junaid + Sufyan + Hasan al-Basri + Shaqeeq + Haatim + Dhu'l-Nun + Ibn Ata Allah + Shibli). Multi-tier, not a monoculture.

**Enrichment ratio D2 (60% cap):** all chapters under cap. ch02 at 39% is the highest, driven by 8 numbered Quranic verses + 4 hadith citations that ARE the structure of the eight-benefits narrative — not displacement of source. Compliant.

**Episode txt word counts:** 1,590–1,896 words. All inside build-script hard band [150, 2000]. All above the catalog's 200–1,000 soft target (P1-2 above).

**Framing structural integrity (F1–F6):** all 5 framings carry Opening directive, Background, Audience, Angle, Central tensions, Host dynamic, Tone constraints, Permission to disagree, Three-part focus, Pronunciation, Do not, Upload checklist. F3 (audience named concretely) and F4 (2–4 specific tensions) pass for all 5.

**H1/H2/H3 (welcome + summary + closing landing):** all 5 framings carry welcome clause, 2–3 sentence summary clause, and explicit Landing section with "Close on the unresolved tension..." + "no host commentary after".

**I1/I2 (anti-repetition + no-irrelevant-background):** all 5 framings carry both clauses in the Do-not block.

**J1/J2 (name discipline):** all 5 framings carry Name discipline sub-block; all chapters apply alias after first mention for every long name in `05-name-alias-policy.md`.

**K1/K2 (interruption avoidance + filler vocabulary):** all 5 framings carry Conversation discipline clause with named filler words ("yeah", "right", "exactly") in Host dynamic.

**M1/M2 (DENY-modernize + DENY-surprise):** all 5 framings carry full canonical DENY blocks.

**M3/M4 + N5 + O3 (transcript empirical loops):** **DEFERRED.** `BOOK_DIR/turboscribe/` carries no transcripts yet (this is a fresh re-run; no NotebookLM audio has been generated). Loop M re-runs after Asif uploads, NotebookLM generates audio, and TurboScribe produces transcripts.

**N1/N2/N4 (inline phonetic parens / imperative form / no-read-aloud guard):** all 5 chapters carry zero inline phonetic parens; all 5 framings use imperative `Pronounce "..."` form throughout the Pronunciation block; all 5 framings end with the literal `Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.`

**O2 (no abbreviated work titles):** all 5 chapters use full canonical forms — `Ihya Ulum al-Din`, `Nahj al-Balagha`, `Sahih Bukhari`, `Sahih Muslim`, `Sunan Tirmidhi`, `Sunan Abu Dawud`. Zero hits on the FORBIDDEN_ABBREVIATIONS list.

---

## Build-script verification

After iter-1 auto-fixes, `python3 scripts/podcast/build_episode_txt.py` was re-run for all 5 episodes:

```
EP01-frame-and-first-counsel: 3,042 words → 1,896 words ✓
EP02-hatim-eight-benefits:    2,561 words → 1,590 words ✓
EP03-the-path:                3,049 words → 1,736 words ✓
EP04-four-cautions:           2,738 words → 1,640 words ✓
EP05-method-and-closing-prayer: 2,680 words → 1,724 words ✓
```

All 5 episodes pass structural validation (chapter SOURCE + framing CUSTOMIZE PROMPT both validate).

---

## Next action for Asif

The book is **upload-eligible** for the chapter+customize-prompt pair, but the five P1 findings deserve a once-over:

1. **(P1-1, must-decide)** Accept the two residual honorific expansions inside verbatim Ghazali blockquotes (ch03:33 and ch05:107) as the A4-verbatim-integrity price, OR paraphrase the lines slightly to drop the honorific. Agent recommends accepting.
2. **(P1-2, optional trim)** Consider factoring the duplicate ~250-word `## Do not` boilerplate out of each framing, or trim Pronunciation lists to chapter-relevant terms only. Will pull framings under the 1,000-word soft target.
3. **(P1-3, blocker if `qudsi` is to be pronounced correctly)** Add `qudsi` to `_phonetics.md` + `03-arabic-english-manifest.md`, then add a `Pronounce "qudsi"` line to EP05's framing.
4. **(P1-4, doc-consistency)** Update `_system/editorial-notes.md` to note `nafs` is kept in ch02 too, or document the rationale in EP02 framing.
5. **(P1-5, contract clarification)** Decide per-form vs per-figure semantics for R-HONORIFIC-ONCE and update either the rule text or the catalog/build script to match.

Once those are addressed (or consciously accepted), upload per the per-episode flow:
1. Upload `chapters/ch##-<slug>.txt` to NotebookLM as the single source.
2. Paste contents of `episodes/EP##-<slug>.txt` into NotebookLM's Customize prompt box.
3. Click Generate.

After audio is generated and transcribed, drop transcripts into `turboscribe/EP##-<slug>.transcript.txt` and re-invoke `/podcast-challenger ayyuhal-walad` for Loop M (empirical-transcript audit: M3/M4/N5/O3).
