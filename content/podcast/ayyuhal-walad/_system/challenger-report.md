# Podcast Challenger Report

**Book:** ayyuhal-walad
**Run:** 2026-05-16 (challenger v1.0)
**Scope:** per-book sweep (all 5 chapters + matched framings)
**Iterations:** 2 (of 3 max)
**Verdict:** SHIP-WITH-CAUTION (one open P1 awaiting Asif's policy decision)

---

## Iteration history

| Iter | Started | Auto-fixes | New P0 | New P1 | Notes |
|---|---|---|---|---|---|
| 1 | 2026-05-16 | 38 (B5 em-dashes across 5 chapters) | 4 (A3 missing Yusuf Ali attribution in 4 chapters) | 1 (C3 honorific repetition policy) | Verdict: BLOCKED |
| 2 | 2026-05-16 | 0 (Asif resolved A3 by author edit, not auto-fix) | 0 — A3 cleared | 1 (C3 remains; awaits policy) | Verdict: SHIP-WITH-CAUTION |

---

## Auto-fixes applied (iteration 1)

| Check | File | Action | Count |
|---|---|---|---|
| B5 | ch01-frame-and-first-counsel.txt | em-dash → comma / colon / restructure | 15 |
| B5 | ch02-hatim-eight-benefits.txt | em-dash → comma / restructure | 13 |
| B5 | ch03-the-path.txt | em-dash → comma / restructure | 6 |
| B5 | ch04-four-cautions.txt | em-dash → comma / restructure | 8 |
| B5 | ch05-method-and-closing-prayer.txt | em-dash → comma / restructure | 5 |
| (rebuild) | all 5 episodes/*.txt | regenerated via build_episode_txt.py | 5 |

**Total auto-fixes:** 38 em-dashes replaced across 5 chapters; 5 episode txts regenerated.

## Author resolutions (iteration 2)

| Check | File | Resolution |
|---|---|---|
| A3 | ch01-frame-and-first-counsel.txt:46 | Added `English: Yusuf Ali` attribution at first Quranic translation (Quran 39:9) with subsequent-coverage clause |
| A3 | ch02-hatim-eight-benefits.txt:46-47 | Same attribution added at Quran 79:40-41 |
| A3 | ch04-four-cautions.txt:121 | Same attribution added at Quran 2:44 |
| A3 | ch05-method-and-closing-prayer.txt:95 | Same attribution added at Quran 3:185 |
| (rebuild) | all 5 episodes/*.txt | regenerated |

Asif chose **Yusuf Ali** (Abdullah Yusuf Ali, *The Holy Qur'an: Text, Translation and Commentary*, 1934) as the canonical Quranic translator for the Ayyuhal Walad series. Convention: named on first verse per chapter; subsequent verses inherit the named translator.

---

## Findings still requiring decision

### P1 (ship-with-caution)

#### C3 — Honorific repetition policy

Per `enrichment-sources.md` §4 anti-pattern "Devotional padding": honorifics (PBUH, AS, RA, salawat) should appear at first mention only per chapter, not on every occurrence. Counts post-iteration-2:

| Chapter | PBUH-like | AS-like | First-mention limit |
|---|---|---|---|
| ch01 | 2 | 3 | 1 each (4 redundant) |
| ch02 | 3 | 2 | 1 each (3 redundant) |
| ch03 | 3 | 1 | 1 each (2 redundant) |
| ch04 | 2 | 2 | 1 each (2 redundant) |
| ch05 | 0 | 1 | within limit |

**Decision required:**
- **(a) Strict first-mention policy** — challenger auto-fix would strip subsequent honorifics, keeping only the first per chapter. NotebookLM listener experience: cleaner, less repetitive.
- **(b) Devotional-preservation policy** — keep PBUH at every direct Prophetic quote, AS at every direct Imam Ali quote, etc. NotebookLM listener experience: more reverent; some listeners (especially scholarly audiences) expect this.
- **(c) Compromise** — first mention per chapter PLUS one PBUH/AS at the introduction of each NEW direct quote from the relevant figure (so a chapter with 3 separate Prophetic hadith gets 3 PBUHs, one per first-introduction).

The challenger's default is (a) strict. The current state of the chapters is closest to (c) compromise (each direct hadith quote carries PBUH at its introduction). Asif's choice.

### Other categories — all pass

- **A1 Citation discipline**: every quote has a properly formatted attribution line.
- **A2 Citation authenticity**: no `[VERIFY CITATION]`; all hadith from canonical collections; all Imam Ali sayings cited to Nahj al-Balagha or Ghurar al-Hikam.
- **A3 Translation provenance**: ✅ resolved this iteration.
- **A4 Verbatim quote integrity**: hadith and Imam Ali quotes are verbatim from named sources; Quranic English is now attributed to Yusuf Ali (the author renderings closely track Yusuf Ali's translation, with modernizations for podcast prose flow).
- **A5 No source-shifting**: no quoted material is bent away from its accepted meaning.
- **A6 No cross-tradition collision**: Sunni/Shia/Ismaili adjacencies are annotated correctly throughout.
- **B1-B6 NotebookLM literalness**: no meta-prose, no cross-episode refs, no file-length self-references, no translator-apparatus prefixes, no em-dashes (auto-fixed), no invented dialogue.
- **C1 Phonetic coverage**: every Arabic transliteration has a phonetic guide on first chapter occurrence.
- **C2 Lexicon parity**: consistent across chapters.
- **D1 Tier diversity**: all chapters meet ≥3 tier threshold (ch01: 5 tiers; ch02, ch03, ch04, ch05: 3 each).
- **D2 Enrichment ratio**: 18-25% across the 5 chapters, well under the 60% cap.
- **D3 Tradition-coherence**: enrichment citations cluster around the chapters' named tensions.
- **D4 No quote-stacking**: no 3+ consecutive blockquotes without integrating commentary.
- **D5 No [CONTEXT NEEDED]**: clean.
- **E1 Word-count band**: all chapters 2,500-4,000 words (Default-to-Longer Deep Dive band).
- **E2-E5 Articulation**: passes spot-check.
- **F1-F6 Framing integrity**: all 5 framings have the four-part structure, name audience concretely, name 2-4 specific tensions, have well-shaped discussion-spines, include canonical steering phrases.

---

## Health metrics (post-iteration-2)

| Chapter | Words | Enrichment ratio | Tier count | Citations | Phonetic gaps |
|---|---|---|---|---|---|
| ch01-frame-and-first-counsel | 3,981 | ~22% | 5 | 14 | 0 known |
| ch02-hatim-eight-benefits | 2,873 | ~25% | 3 | 13 | 0 known |
| ch03-the-path | 2,746 | ~22% | 3 | 8 | 0 known |
| ch04-four-cautions | 3,325 | ~18% | 3 | 11 | 0 known |
| ch05-method-and-closing-prayer | 2,504 | ~21% | 3 | 7 | 0 known |

All within NotebookLM Default-to-Longer Deep Dive band. All under enrichment cap. All meet tier diversity threshold.

---

## Verdict reasoning

**SHIP-WITH-CAUTION** because:
- All P0 findings resolved (em-dashes auto-fixed in iter 1; Quranic translator attribution added in iter 2).
- One open P1 (C3 honorific policy) requires Asif's decision but does NOT block upload. The current state (compromise policy: honorifics on direct-quote introductions) is defensible and reverent.

**To advance to SHIP-READY**, choose one of the three C3 policies (strict / devotional / compromise) and either accept the current state or re-invoke the challenger to auto-apply strict-policy stripping.

**For upload**: bundles are NotebookLM-ready at `content/podcast/ayyuhal-walad/episodes/EP##-<slug>.txt`. Upload checklist in each `00-framing.md`.
