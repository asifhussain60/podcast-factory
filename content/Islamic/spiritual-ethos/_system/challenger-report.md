# Podcast Challenger Report

**Book:** spiritual-ethos
**Run:** 2026-08-06 16:20 (challenger v2.6)
**Scope:** per-chapter dhikr-the-polish-for-hearts (ch09a + EP09)
**Iterations:** 2 (of 5 max) — iter 1 detect, iter 2 auto-fix + re-validate; iter 3 would be no-change (intelligent break)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  ← detected from _system/series-config.yaml (deep_dive, adaptation_mode: faithful, length_target 4600-9500)

> S1 async-safety intentionally bypassed: this invocation runs INSIDE orchestrate_book.py (the pgrep hit is the waiting parent), not a concurrent run.

## Prior-P0 disposition (resolved this cycle)

- **T2 (doctrinal lineage) — RESOLVED.** The prior run (16:09) blocked on framing line 10 labelling Ja'far al-Sadiq "the sixth Imam". The framing now reads "the fifth Imam", which is the correct Ismaili ordinal (imam-lineage-ismaili.yml: ordinal 5 = Ja'far al-Sadiq). `build_episode_txt.py`'s `assert_doctrinal_clean()` gate passes; a fresh T1–T3 semantic pass over chapter + framing finds no lineage, attribution, or forbidden-pairing violation. No P0 remains.
- **B1/B3 (this-episode self-reference) — RESOLVED.** Chapter now uses "this chapter" and the headings "## Where this chapter begins" / "## What this chapter establishes".

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 2 | B2 | ch09a-dhikr-the-polish-for-hearts.txt:7,15,31,41,53 | "in this series" → "in this book" (5×): removed the podcast-meta "series" connotation of a cross-reference NotebookLM cannot satisfy from the single uploaded source; "this book" is the chapter's own established self-reference vocabulary (lines 27, 55, 63) |
| 2 | B2 | ch09a-dhikr-the-polish-for-hearts.txt:51 | "this whole series" → "this whole book" (same rationale) |

Re-ran `build_episode_txt.py EP09-dhikr-the-polish-for-hearts` after the edits — chapter re-validates, episode CUSTOMIZE PROMPT re-emitted clean (5006 words source / 735 words prompt). ("series of practices" on line 17 is ordinary usage, left untouched.)

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION (Category C/N, from build gate) — chapter SOURCE
- **File:** content/Islamic/spiritual-ethos/chapters/ch09a-dhikr-the-polish-for-hearts.txt
- **Context:** 9 Arabic transliterations/names detected (Abu Talib, al-Ashtar, al-Balagha, al-Ghazali, al-Hikam, al-Isfahani, al-Makki, al-Raghib, + one more). F20 doctrine — replace with English audio labels for TTS safety.
- **Mitigation:** the framing's "## Name discipline" block already maps every one of these to an English role (the lexicographer, the early Persian master, the great reviver-theologian, the Persian poet, the fifth Imam, the modern scholars of gnosis) and forbids Arabic book titles. This is the standing SHIP-WITH-CAUTION caution carried identically by all 4 shipped siblings. Not auto-fixed — English audio-label substitution in a faithful reading-edition SOURCE is an authoring decision.

#### N3 — "dhikr" has no settled spoken form
- **File:** EP09-dhikr-the-polish-for-hearts/00-framing.md (Pronunciation block: `- dhikr: dhikr`)
- **Context:** build NOTE — the pronunciation ladder has nothing settled to say for `dhikr`.
- **Suggested fix:** settle by ear — `python3 scripts/podcast/run_pronunciation_probe.py spiritual-ethos` (writes the cross-book ledger; the build recompiles the block). Not hand-fixable per N3.

#### F25-APPARATUS-TABLE (from build gate) — show-notes apparatus missing
- **File:** EP09-dhikr-the-polish-for-hearts/99-show-notes.md
- **Context:** no "## Name and Title Preservation Table" section. F25 — the written-layer apparatus (preserved Arabic + audio-label crosswalk) the TTS-safe audio omits is missing.
- **Note:** 99-show-notes.md is outside the challenger's edit scope (Section 8). Flagged for the author.

#### CS8 / P8 (book-scope n-gram duplication)
- **Context:** dhikr shares 4 distinct 12-word passages with `prayer-as-the-source-of-justice` (the "polish for the hearts, by which they hear after being deaf…" spine) and 3 with `the-veils-that-do-not-veil` ("…the remembrance of God is greater (chapter 29, verse 45)…").
- **Mitigation:** intentional cross-angle return — the chapter states this explicitly ("the same verse … in its bearing on justice"). Real but deliberate; author to confirm it is the acknowledged return, not accidental re-teaching. Never auto-stripped.

### P2 (advisory)

- **E1 / NotebookLM tier dead-zone:** chapter is 5006 words — in the 4500–5500 dead-zone (too dense for Longer Deep Dive, too thin for Extended). Contract band 4600–9500 is satisfied and CS4 did not flag it. Either tighten to ≤4500 or expand via Phase 0e to ≥5500 for a cleaner tier fit. Minor contract drift: `word_count: 4775` in the contract vs 5006 actual — refresh the field.
- **B5 em-dashes:** heavy use; reconciled as reading-edition style — the build gate (code is authority) does not strip or reject them, and all shipped siblings carry them. No action.
- **CS6 / P6 cross-book bleed:** 'walaya' matches `degrees-of-excellence`'s mangle-map — a false positive on common Islamic vocabulary. Surfaced for human review, never auto-stripped.
- **A3 translation provenance:** Quranic passages are Shah-Kazemi's own renderings woven into prose (not separate translator-attributed blockquotes); provenance is the book itself. Consistent with reading-edition style; not raised as P0.

### Book-scope notes (outside this per-chapter target)

- **CS-P4 (P0 on a different chapter):** `the-letter-of-ali-to-malik-al-ashtar` is 10109 words vs its declared `extended` band 5500–9500. It is a complete primary text (a letter) and legitimately long; the P0 belongs to that chapter's own convergence, not this dhikr run. Surfaced so the book-level ship review sees it.
- **CS5 / P5 (P1):** chapter-set word-count variance is 50% (min 5006 = dhikr, max 10109 = the Letter); >30% target. Driven by the two long primary-text chapters (Sermon, Letter). Book-scope.

## Health metrics

| Chapter | Words | Enrichment | Tier diversity | Quran citations | Translit flags | Doctrinal |
|---|---|---|---|---|---|---|
| ch09a-dhikr | 5,006 | rich, integrated (≤60%) | 6+ tiers (Qur'an, Prophet, Imam sayings, Sufi masters, Shi'i gnosis, lexicographer) | 8 (all canonical `(chapter N, verse M)`) | 9 (P1, standing) | 0 P0 (T2 resolved) |

- Quran citation format: all 8 verses use the canonical plain-English `(chapter N, verse M)` form. ✓
- Hadith/Imam blockquotes name the speaker with NO reference-tail (correct under the reading-edition no-noise doctrine). ✓
- Cross-episode self-reference: "in this series" / "this whole series" (6×) auto-normalized to "…book" this run. ✓
- Host-role parity (Q1–Q4): Host A male scholar / Host B female seeker, consistent across all book framings (pool-equivalent). ✓
- No AI-cliché / deep-dive self-reference / faux-profundity opener (U1/U2/U4). ✓
- Arabic script present via honorifics (ع ×8, ﷺ ×1) — N6 satisfied. ✓
- No transcript present — Loop M/N/O/P/Q/R transcript-empirical checks not run (skipped, no EP09 transcript on disk).
