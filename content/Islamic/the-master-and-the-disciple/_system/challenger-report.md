# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-06-11 (challenger v2.5)
**Scope:** per-chapter emptying-the-cup
**Iterations:** 1 (of 5 max) — intelligent-break: identical (P0=0, P1=2) to prior run; no deterministic auto-fixes available
**Verdict:** SHIP-WITH-CAUTION
**content_profile:** islamic_scholarly  ← detected from _system/series-config.yaml

## Auto-fixes applied (iteration-by-iteration)

None. The two P1 findings (R-NO-ARABIC-TRANSLITERATION on source-dialogue character names; missing F25 preservation table) require authoring judgment. The 18 em-dashes in chapter prose are load-bearing definitional gloss markers (`kasrah — demolition`, `arif — the sanctified scholar`, `ilm — knowledge`); a mechanical B5 strip would corrupt the scholarly-dialogue voice and is therefore not safe to auto-apply at this density.

## Findings requiring author resolution

### P0 (blocks ship)

None. Doctrinal pack (T1 attribution / T2 lineage / T3 forbidden phrases) clean. Build-script gates pass. No HTML comments, no meta-prose tells, no DENY-list violations outside the framing's legitimate `## Do not` enumeration. Chapter word count 2,438 within Default Deep Dive band (1,800–2,800). Framing word count 746 within soft band. Debate-mode contract complete: `episode_format: debate`, `resolution: host_b_concedes`, both host roles and positions populated, source moves named.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION: 8 Arabic transliterations detected in chapter SOURCE
- **File:** content/Islamic/the-master-and-the-disciple/chapters/ch15d-emptying-the-cup.txt (throughout)
- **Context:** Build script flags: 'Abu Malik', 'al-Bakhtari', 'al-Balagha', 'al-Din', 'al-Ghazali', 'al-Radi', 'al-Shari', 'al-Sharif'. Salih + Abu Malik are the two named interlocutors of the source dialogue; al-Bakhtari is the host at the door; the al-* prefixes belong to cited work-titles and authors (*Nahj al-Balagha*, *Ihya Ulum al-Din*, al-Ghazali, al-Sharif al-Radi). The framing already instructs hosts to use "the young teacher" / "the visiting scholar" / "the father at the door" audio labels (R-NAMEALIAS satisfied), so audio output is TTS-safe; the chapter SOURCE retains the canonical names since they are load-bearing for the written show notes / preservation table.
- **Suggested fix:** Author decides — replace character names with English labels throughout chapter text, OR accept that the framing's name-discipline rule covers audio safety and the SOURCE preserves the names for the written apparatus. Cited work-titles and historical author names (al-Ghazali, al-Sharif al-Radi) should remain — these are bibliographic, not character dialogue.

#### F25-APPARATUS-TABLE: 99-show-notes.md missing 'Name and Title Preservation Table' section
- **File:** content/Islamic/the-master-and-the-disciple/_system/episode-drafts/EP15-emptying-the-cup/99-show-notes.md
- **Context:** Every published episode's 99-show-notes.md is expected to carry the written-layer apparatus (Original/Transliteration → Audio Label crosswalk). This show-notes file ends mid-reference and carries no apparatus table.
- **Suggested fix:** Author writes the preservation table covering: Salih → the young teacher; Abu Malik → the visiting scholar; al-Bakhtari → the father at the door; *Nahj al-Balagha* → *The Peak of Eloquence*; *Misbah al-Shari'a* → *The Lamp of the Sacred Law*; *Ihya Ulum al-Din* → *The Revival of the Religious Sciences*; Commander of the Faithful (peace be upon him); chapter 2 verse 156 (the verse of return); chapter 39 verse 9 (the chapter on the throngs).

### P2 (advisory)

- **B5-EM-DASH-DENSITY:** 18 em-dashes in chapter (1 per ~135 words) + 19 in framing. Most are definitional-gloss bindings (`kasrah — demolition`, `arif — the sanctified scholar`, `ilm — knowledge`, `marifa — gnosis`, `khabar`/`iyan`). Mechanical replacement with comma would damage the scholarly-dialogue voice. Author may selectively convert non-definitional em-dashes (lines 7, 13, 17, 19, 51, 59) to comma-bounded clauses; preserve definitional gloss markers.
- **R-RECURRING-THESIS verification:** framing instructs hosts to repeat spine thesis verbatim 3× (open, pivot, close). Cannot verify at framing-review time — empirical transcript audit applies post-publication.
- **F4 central tensions:** debate-mode override active (Category P P1 satisfied via populated contract.debate block) — F4 deep-dive tension check correctly skipped.
- **CS5 chapter-set balance:** book-scope check is the authority; per-chapter run does not gate.

## Health metrics

| Chapter | Words | Enrichment ratio | Tier diversity | Citations | Phonetic gaps |
|---|---|---|---|---|---|
| ch15d-emptying-the-cup | 2,438 | ~24% (Nahj al-Balagha Saying 147; Quran 2:156 + 39:9; *Misbah al-Shari'a* ch.32; al-Ghazali *Ihya* Book One ch.2) | 4 tiers (Quran, Nahj al-Balagha, hadith collection, classical kalam) | 5 explicit with translator + page | 0 (no inline phonetics per R-PHONETICS-OUT; framing carries imperative Pronunciation block with 14 terms) |

## Build-gate status

- `build_episode_txt.py`: PASS with 2 P1 advisories (R-NO-ARABIC-TRANSLITERATION, F25-APPARATUS-TABLE) — both surfaced above.
- Doctrinal pack (T1 / T2 / T3): clean.
- Honorifics: '(peace be upon him)' appears 1× in chapter and 1× in framing — within R-HONORIFIC-ONCE bound.
- Debate-mode contract (Category P): proposition, both host positions, source moves, resolution (`host_b_concedes`) all populated. Framing carries Opening directive, Three-part focus, Host dynamic, Tone constraints, `## Do not`, Landing.

## PEQ Score (Wave K, 5-axis)

Stable at iter-1; matches sibling episodes' SHIP-WITH-CAUTION pattern (R-NO-ARABIC-TRANSLITERATION + F25-APPARATUS-TABLE are systemic across the book and are author-judgment items, not blockers).
