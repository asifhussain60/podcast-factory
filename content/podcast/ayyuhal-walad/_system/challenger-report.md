# Podcast Challenger Report

**Book:** ayyuhal-walad
**Run:** 2026-05-17 (podcast-challenger agent, v1.4 — second outer-loop invocation)
**Scope:** per-book sweep (5 chapters + 5 framings, all in scope)
**Iterations:** 2 (of 5 max; intelligent-break per Section 4.6b)
**Verdict:** SHIP-WITH-CAUTION

---

## Convergence summary

| Iter | Auto-fixes applied | P0 | P1 | P2 | Break reason |
|---|---|---|---|---|---|
| 1 | 2 | 0 | 3 | 2 | (proceed) |
| 2 | 0 | 0 | 3 | 2 | Intelligent break: (P0, P1) identical to iter 1 AND zero auto-fixes |

All 5 episode txts rebuilt clean via `build_episode_txt.py` post-iter-1. Build script structural gates all pass: no HTML comments, no meta-prose tells, no inline phonetic parens, no abbreviated work titles, no parenthetical-honorific repeats, all framings carry imperative Pronunciation block + canonical `## Do not` DENY block + no-read-aloud guard, all chapter and framing word counts inside hard bands.

The deterministic P1-3 (`qudsi` phonetic gap) and P1-4 (editorial-notes `nafs` sync) findings from the prior outer-loop pass were resolved by the caller between invocations:
- `Hadith qudsi → ha-deeth qud-see` row added to `content/_shared/arabic/03-arabic-english-manifest.md` §4 line 106.
- `Pronounce "qudsi" as "qud-see"...` line present in EP05 framing line 77.
- `editorial-notes.md` "Kept by exception" section now documents both the ch02 `nafs` gloss (line 24) and the ch05 `qudsi` exception (line 25).

This pass surfaced **two new N3 gaps** in chapters that were missed by the prior agent's term audit. Both are deterministic auto-fixes (shared-manifest-grounded). They have been applied.

---

## Auto-fixes applied (iteration 1)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | N3 / R-PRONUNCIATION-IMPERATIVE | _system/episode-drafts/EP01-frame-and-first-counsel/00-framing.md:88 | Inserted `Pronounce "fard kifaya" as "fard ki-faa-yah". Say it as one fluent run.` — `*fard kifaya*` italicized in ch01 line ~166; canonical phonetic from shared manifest §5. |
| 1 | N3 / R-PRONUNCIATION-IMPERATIVE | _system/episode-drafts/EP05-method-and-closing-prayer/00-framing.md:82 | Inserted `Pronounce "taqwa" as "taq-waa". Say it as one fluent word.` — `*taqwa*` italicized in ch05 line 113; canonical phonetic from shared manifest §5. |

Total auto-fixes iteration 1: **2 Pronounce-line gap-fills (N3 deterministic)**.

All 5 episode txts rebuilt via `build_episode_txt.py` after auto-fixes; all pass structural validation:
```
EP01-frame-and-first-counsel:    3,042 words → 1,908 words ✓ (was 1,896; +12 from new Pronounce line)
EP02-hatim-eight-benefits:       2,561 words → 1,590 words ✓
EP03-the-path:                   3,049 words → 1,736 words ✓
EP04-four-cautions:              2,738 words → 1,640 words ✓
EP05-method-and-closing-prayer:  2,680 words → 1,767 words ✓ (was 1,724; +43 from qudsi + taqwa lines)
```

Iteration 2 walked the full catalog again; no further auto-fixes triggered; (P0, P1) counts identical to iteration 1 → intelligent-break invoked.

---

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### P1-1 (inherited from prior pass): Two verbatim-blockquote honorific expansions preserved (R-HONORIFIC-ONCE vs A4 trade-off)

After the prior pass's auto-fix strip across 5 chapters, two residual honorific expansions remain inside **verbatim source blockquotes**:

- **chapters/ch03-the-path.txt:33** — `> This person should have acquired a light from the lights of the Messenger of Allah, peace and blessings be upon him.` This is a verbatim Ghazali quote (the description of the perfected guide). Stripping the honorific from inside a verbatim blockquote violates A4 (verbatim quote integrity). Result: ch03 has 2 prose-form "peace and blessings be upon him" expansions (line 19 first mention + line 33 verbatim blockquote).
- **chapters/ch05-method-and-closing-prayer.txt:107** — `> ...descend upon Muhammad, peace and blessings be upon him, who is the best of all creations...` Inside the verbatim closing supplication that Ghazali asks the student to recite after every prayer. The full supplication is the chapter's load-bearing closing artifact. Stripping the honorific from the supplication body would change the prayer.

**Status:** unchanged since prior pass. Agent recommendation stands: **accept both as preserved** — verbatim integrity is more important than the marginal honorific drift. The alternative is to paraphrase the lines slightly to drop the honorific, but for the closing supplication that would mean rewording a prayer Ghazali wrote, which is the worse violation.

#### P1-2 (inherited from prior pass): Framing word counts above the catalog soft band (E1)

All 5 framings land at 1,639–1,954 words (1,590–1,908 in the rendered episode txt), above the catalog's soft target of 200–1,000 words for framings. They are well inside the build script's hard band (150–2,000) and inside the typical NotebookLM customize-prompt size that practitioners report works, but the catalog's soft target is meaningfully lower.

- _system/episode-drafts/EP01-frame-and-first-counsel/00-framing.md: 1,955 words → episode 1,908 words (post-iter-1 with new `Pronounce "fard kifaya"` line)
- _system/episode-drafts/EP02-hatim-eight-benefits/00-framing.md: 1,639 words → episode 1,590 words
- _system/episode-drafts/EP03-the-path/00-framing.md: 1,785 words → episode 1,736 words
- _system/episode-drafts/EP04-four-cautions/00-framing.md: 1,689 words → episode 1,640 words
- _system/episode-drafts/EP05-method-and-closing-prayer/00-framing.md: 1,809 words → episode 1,767 words (post-iter-1 with new `Pronounce "taqwa"` line and prior-pass `Pronounce "qudsi"` line)

**Status:** unchanged. The framings carry full Central tensions + Three-part focus + extensive Pronunciation blocks + canonical Do-not lists. Three places to consider trimming: (a) the duplicated boilerplate `## Do not` section (~250 words per framing, identical across all 5) could be factored into a shared block the author maintains separately; (b) the Pronunciation lists are 22–29 lines per framing and could be trimmed to terms that actually appear in the matched chapter (EP01's Pronunciation block, for example, retains `Pronounce "Kimiya al-Sa'ada"` twice — once at line 66 and again at line 88 — minor duplication); (c) Background and Audience sections could be tighter. The agent does not auto-fix this — trimming the framing is an authoring decision about what NotebookLM most needs to see. Inherited deferral from prior pass.

#### P1-5 (inherited from prior pass): Per-form vs per-figure honorific ambiguity (catalog O1 vs build script vs R-HONORIFIC-ONCE rule text)

Structural ambiguity surfaced during the prior pass's auto-fix. R-HONORIFIC-ONCE rule text says *"exactly once per chapter, on first mention of each figure"* (per-figure semantics). Catalog O1 detection and the build script's `assert_honorifics_once_only` use *"each honorific phrase form expanded at most once per chapter"* (per-form semantics). The prior agent applied the stricter per-form reading aligned with build-script enforcement. This means: ch01's `(may Allah have mercy upon him)` was stripped from Hasan al-Basri, Sufyan, and Shibli (three different deceased Sufi figures) even though each was a first-mention; only Ghazali keeps the honorific. Same on ch03 Khidr+Musa and ch04 Imam Ali under `peace be upon him`.

**Status:** unchanged. Suggested fix: decide which semantics is canonical and update either the rule text (currently leans per-figure) OR the build script + catalog O1 (currently per-form). For this run the per-form reading was preserved; if Asif intends per-figure, the stripped honorifics on the 2nd+ deceased Sufi / Imam / Prophet should be restored. Agent recommends keeping the per-form reading (it's the empirically-grounded one, matches build-script enforcement) and updating the rule text to match.

### P2 (advisory)

#### P2-1 (inherited from prior pass): ch01 Quranic quote stack (D4)

- **File:** chapters/ch01-frame-and-first-counsel.txt:39–46.
- **Context:** Three Quranic blockquotes stacked back-to-back (99:7-8, 18:110, 18:107) with only minimal bridging prose. Stack is intentional — Ghazali's rhetorical move; the chapter explicitly names the pattern on the next line ("The pattern is unmistakable. The Quran does not separate believing from doing.").
- **Suggested action:** none. Acknowledged authorial choice; carries through to NotebookLM as intended structure.

#### P2-2 (new this pass): Two borderline italicized single-word terms in ch03 without standalone Pronounce lines (C1)

- **File:** chapters/ch03-the-path.txt — `*Murshid*` and `*Sufi*` are italicized in the chapter prose.
- **Context:** `Murshid` is covered by EP03's `Pronounce "Murshid al-Kamil"` (compound form); the standalone bare form has no dedicated line. `Sufi` is an English-naturalized term that listeners read trivially; it is not in the shared manifest as a standalone entry, and the manifest's `tasawwuf` entry covers Sufism the tradition. Both are flagged P2 (not P1) because: (a) neither term is in the shared manifest as a standalone, so N3 auto-fix does not apply; (b) the practical pronunciation risk is low — `Sufi` is universally recognized in English, and `Murshid` is the same syllables as the al-Kamil compound the framing already locks.
- **Suggested action:** optional. If Asif wants belt-and-suspenders coverage, add `Pronounce "Murshid" as "mur-shid". Say it as one fluent word.` to EP03 framing; `Sufi` is fine as-is. Not blocking ship.

---

## Health metrics

| Chapter | Words | Episode words | Enrichment % (blockquote-based) | Citations (Quran + hadith) | Phonetic gaps | Honorific expansions (post-fix) | Em-dashes (chapter) |
|---|---|---|---|---|---|---|---|
| ch01-frame-and-first-counsel | 3,042 | 1,908 | 20% | 8 Quran + 0 named-hadith ref | 0 (post-iter-1, after `fard kifaya` added to EP01) | 1 prose "peace and blessings" + 1 "(may Allah have mercy upon him)" + 1 "peace be upon him" (Imam Ali) | 0 |
| ch02-hatim-eight-benefits | 2,561 | 1,590 | 39% | 16 Quran + 5 hadith | 0 | 1 + 1 + 0 | 0 |
| ch03-the-path | 3,049 | 1,736 | 14% | 4 Quran + 2 hadith | 2 borderline (Murshid, Sufi — P2) | **2** (1 first-mention + 1 verbatim blockquote at line 33) + 0 + 1 (Imam Ali line 79) | 0 |
| ch04-four-cautions | 2,738 | 1,640 | 13% | 3 Quran + 4 hadith | 0 | 1 + 0 + 1 (Prophet Isa line 47) | 0 |
| ch05-method-and-closing-prayer | 2,680 | 1,767 | 24% | 0 Quran direct + 7 hadith refs | 0 (post-iter-1, after `taqwa` added to EP05; `qudsi` was added by caller between outer-loop passes) | **2** (1 first-mention + 1 verbatim supplication at line 107) + 1 (Aisha) + 1 (Imam Ali) | 0 |

**Cross-chapter variance:** 3,049 vs 2,561 = 19% — within the ±30% balance target.

**Tier diversity (D1):** all 5 chapters draw on ≥4 of the 7 enrichment tiers (Tier 1 Quran, Tier 3 Sunni hadith, Tier 4 Imam Ali AS via Nahj al-Balagha + Ghurar al-Hikam, Tier 5 Ismaili tradition via Aga Khan IV + Holy Du'a + Sahifa al-Sajjadiyya, Tier 6 Sufi voices via Junaid + Sufyan + Hasan al-Basri + Shaqeeq + Haatim + Dhu'l-Nun + Ibn Ata Allah + Shibli). Multi-tier, not a monoculture.

**Enrichment ratio D2 (60% cap):** all chapters under cap. ch02 at 39% is the highest, driven by 8 numbered Quranic verses + 4 hadith citations that ARE the structure of the eight-benefits narrative — not displacement of source. Compliant.

**Episode txt word counts:** 1,590–1,908 words. All inside build-script hard band [150, 2000]. All above the catalog's 200–1,000 soft target (P1-2 above).

**Framing structural integrity (F1–F6):** all 5 framings carry Opening directive, Background, Audience, Angle, Central tensions, Host dynamic, Tone constraints, Permission to disagree, Three-part focus, Pronunciation, Do not. F3 (audience named concretely) and F4 (2–4 specific tensions) pass for all 5.

**H1/H2/H3 (welcome + summary + closing landing):** all 5 framings carry welcome clause, 2–3 sentence summary clause, and explicit Landing section with "Close on the unresolved tension..." + "no host commentary after".

**I1/I2 (anti-repetition + no-irrelevant-background):** all 5 framings carry both clauses in the Do-not block.

**J1/J2 (name discipline):** all 5 framings carry Name discipline sub-block; all chapters apply alias after first mention for every long name in `05-name-alias-policy.md`.

**K1/K2 (interruption avoidance + filler vocabulary):** all 5 framings carry Conversation discipline clause with named filler words ("yeah", "right", "exactly") in Host dynamic.

**M1/M2 (DENY-modernize + DENY-surprise):** all 5 framings carry full canonical DENY blocks.

**M3/M4 + N5 + O3 (transcript empirical loops):** **DEFERRED.** `BOOK_DIR/turboscribe/` carries no transcripts yet. Loop M re-runs after Asif uploads, NotebookLM generates audio, and TurboScribe produces transcripts.

**N1/N2/N4 (inline phonetic parens / imperative form / no-read-aloud guard):** all 5 chapters carry zero inline phonetic parens; all 5 framings use imperative `Pronounce "..."` form throughout the Pronunciation block; all 5 framings end with the literal `Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.`

**N3 (gap-fill framing Pronunciation):** post-iter-1 all italicized Arabic terms in chapters are covered. Two minor borderline standalone-singletons in ch03 (`Murshid`, `Sufi`) flagged as P2-2 above; neither is in the shared manifest as a standalone, so neither qualified for auto-fix.

**O2 (no abbreviated work titles):** all 5 chapters use full canonical forms — `Ihya Ulum al-Din`, `Nahj al-Balagha`, `Sahih Bukhari`, `Sahih Muslim`, `Sunan Tirmidhi`, `Sunan Abu Dawud`. Zero hits on the FORBIDDEN_ABBREVIATIONS list.

---

## Build-script verification

After iter-1 auto-fixes, `python3 scripts/podcast/build_episode_txt.py` was re-run for all 5 episodes:

```
EP01-frame-and-first-counsel:   3,042 words → 1,908 words ✓
EP02-hatim-eight-benefits:      2,561 words → 1,590 words ✓
EP03-the-path:                  3,049 words → 1,736 words ✓
EP04-four-cautions:             2,738 words → 1,640 words ✓
EP05-method-and-closing-prayer: 2,680 words → 1,767 words ✓
```

All 5 episodes pass structural validation (chapter SOURCE + framing CUSTOMIZE PROMPT both validate).

---

## Next action for Asif

The book remains **upload-eligible** for all five chapter+customize-prompt pairs. Two new N3 Pronounce-line gaps were auto-filled this pass; the three inherited P1 findings are unchanged and still deserve a once-over:

1. **(P1-1, must-decide)** Accept the two residual honorific expansions inside verbatim Ghazali blockquotes (ch03:33 and ch05:107) as the A4-verbatim-integrity price, OR paraphrase the lines slightly to drop the honorific. Agent recommends accepting.
2. **(P1-2, optional trim)** Consider factoring the duplicate ~250-word `## Do not` boilerplate out of each framing, trim Pronunciation lists to chapter-relevant terms only, and remove the duplicate `Pronounce "Kimiya al-Sa'ada"` line in EP01 framing (lines 66 + 88). Will pull framings under the 1,000-word soft target.
3. **(P1-5, contract clarification)** Decide per-form vs per-figure semantics for R-HONORIFIC-ONCE and update either the rule text or the catalog/build script to match.

Once those are addressed (or consciously accepted), upload per the per-episode flow:
1. Upload `chapters/ch##-<slug>.txt` to NotebookLM as the single source.
2. Paste contents of `episodes/EP##-<slug>.txt` into NotebookLM's Customize prompt box.
3. Click Generate.

After audio is generated and transcribed, drop transcripts into `turboscribe/EP##-<slug>.transcript.txt` and re-invoke `/podcast-challenger ayyuhal-walad` for Loop M (empirical-transcript audit: M3/M4/N5/O3).
