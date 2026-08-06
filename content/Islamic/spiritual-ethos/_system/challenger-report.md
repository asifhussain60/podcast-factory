# Podcast Challenger Report

**Book:** spiritual-ethos
**Run:** 2026-08-06 (challenger v2.6)
**Scope:** per-chapter ali-and-the-prophet (ch01a) + EP01-ali-and-the-prophet framing
**content_profile:** islamic_scholarly  ← detected from _system/series-config.yaml
**Iterations:** 1 (of 5 max) — converged on first pass; no safe auto-fixes available
**Verdict:** SHIP-WITH-CAUTION

> Note: S1 async-safety gate intentionally bypassed for this invocation — it
> originates from within the parent orchestrate_book.py pipeline that spawned it.

## Deterministic gates run

| Gate | Result |
|---|---|
| build_episode_txt.py (chapter SOURCE + framing → episode txt) | exit 0; 5 P1 FLAGs (below) |
| _doctrinal.run_doctrinal_checks (Category T) | clean — 0 findings |
| check_chapter_set.py (Category CS, book scope) | 1 P0 (other chapter), 1 P1, several P2 |

## Auto-fixes applied

None. The chapter and framing were produced by the pipeline and pass the hard
build gate; the remaining items are either (a) authoring decisions on the
chapter SOURCE, (b) known false positives of the naive substring scanners, or
(c) out-of-scope files (99-show-notes.md, sibling chapters). No deterministic,
non-regressing auto-fix was available this run.

## Findings requiring author resolution

### P0 (blocks ship) — BOOK SCOPE, not this chapter

#### CS-P4: Chapter over its declared length band (sibling chapter)
- **File:** content/Islamic/spiritual-ethos/chapters/ch13-the-letter-of-ali-to-malik-al-ashtar.txt
- **Context:** 10,109 words; declared band `extended` is 5,500–9,500. Over by ~600 words.
- **Note:** This is NOT the chapter under per-chapter review (ali-and-the-prophet is 6,177 words, inside the extended band). It is surfaced because Category CS runs at book scope. It will block the BOOK at publish (density_standard: 2). The Letter to Malik is a single primary text; either accept a wider band for it or resegment.
- **Suggested fix:** Re-run Phase 0d for that chapter or relabel its band; does not affect ali-and-the-prophet's per-chapter verdict.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION (F20): 7 transliterations in the chapter SOURCE
- **File:** chapters/ch01a-ali-and-the-prophet.txt
- **Context:** Abu Bakr, Abu Dharr, Abu Talib, al-Bayt, al-Farisi, al-Muttalib, bint Asad.
- **Assessment:** These are biographical PROPER NAMES intrinsic to the narrative (Ali's father Abu Talib, the companions). They cannot be flattened to English audio labels without losing the history. Recommend leaving as-is; the framing's Name discipline and Pronunciation blocks already govern how they are voiced. Flag retained for the record.

#### R-RECURRING-THESIS: framing rule reference missing from an Anti-noise section
- **File:** _system/episode-drafts/EP01-ali-and-the-prophet/00-framing.md
- **Context:** The framing DOES carry the "Repeat the spine thesis verbatim three times — opening, pivot, and close" instruction (in `## Do not`), but the build gate wants it referenced inside a `## Anti-noise rules` section. Substantively satisfied; structurally the gate does not find its anchor.
- **Suggested fix (author): ** move/duplicate the recurring-thesis clause into a `## Anti-noise rules` H2, or add the R-RECURRING-THESIS rule reference.

#### F25-APPARATUS-TABLE: 99-show-notes.md missing the preservation table
- **File:** _system/episode-drafts/EP01-ali-and-the-prophet/99-show-notes.md
- **Context:** No `## Name and Title Preservation Table` header. F25 doctrine requires the written-layer apparatus (preserved Arabic / transliterations + audio-label crosswalk).
- **Suggested fix (author):** add the preservation table to 99-show-notes.md. Out of the challenger's edit scope.

### P1 — recorded but assessed as FALSE POSITIVES

#### R-SURAH-ENGLISH-ONLY: 'quraysh' flagged as a surah name
- **File:** chapters/ch01a-ali-and-the-prophet.txt
- **Assessment:** Every occurrence of "Quraysh" in this chapter names the Meccan TRIBE (e.g. "the Meccan Quraysh and their allies"), not the Qur'anic chapter. False positive; no change needed.

#### R-NOMODERNIZE-STRICT: 'twitter', 'algorithm', 'social media' in framing
- **File:** _system/episode-drafts/EP01-ali-and-the-prophet/00-framing.md
- **Assessment:** These terms appear ONLY inside the `## Do not` DENY list, which is exactly what M1/R-NOMODERNIZE requires the framing to carry. The gate's substring scan cannot distinguish the DENY list from an injection. False positive; the DENY block is correct and should stay.

### P2 (advisory)

- **A3 translation provenance:** The chapter quotes Qur'anic translations ("Verily, thou art of a tremendous nature", etc.) without naming a translator. These are the source author's (Shah-Kazemi's) own scholarly renderings in a faithful_exposition; forcing a "Yusuf Ali / Sahih International" attribution would be inaccurate. Optionally note "the author's rendering" once. Not a blocker.
- **Honorific (ع) x91:** the honorific is attached to nearly every mention of Ali in the SOURCE. The build's honorific gate does not flag the bare (ع) mark, and the framing Name-discipline governs the SPOKEN form ("first mention 'Ali, peace be upon him', then 'Ali'"), so the audio says it once. Written repetition is stylistic; left as-is.
- **B5 em-dashes:** the chapter uses em-dashes throughout as authored literary punctuation. The current build gate accepts them (no flag). Not auto-stripped — mechanically converting 30+ em-dashes would damage a validated literary SOURCE against a contract that permits them.
- **CS-P6 cross-book bleed:** 'Ghadir Khumm', 'qutb', 'walaya' match degrees-of-excellence's mangle-map. Both books treat Ali's spirituality; this is shared Islamic vocabulary, not a bleed. Advisory only; never auto-stripped.

## Category pass summary (islamic_scholarly — full catalog)

| Category | Result |
|---|---|
| A Authenticity | Quran cites all in canonical `(chapter N, verse M)` form (A1 ✓). Sunni/Shi'i sources annotated as parallel traditions (A6 ✓). A3 translator-name P2 advisory. No [VERIFY] markers (A2 ✓). |
| B NotebookLM literalness | "this episode / what this episode lands" are permitted structural frames (per _validator_constants.py), not meta-prose. No cross-episode refs. Clean. |
| C/N Pronunciation | Framing `## Pronunciation` uses correct `- term: form` bullets (N2 ✓); no-read-aloud guard present (N4 ✓). Build NOTE: 5 terms (Ali, Qur'an, mawla, Khaybar, Ghadir Khumm) have no settled spoken form in the ledger — settle by ear with run_pronunciation_probe.py (N3, advisory). |
| D Enrichment | Multi-source (Qur'an, hadith fada'il, Nasir-i Khusraw, Rumi, Ali's own sayings). Coherent to the chapter's three tensions. Clean. |
| E Shape | Clear hook → middle → landing arc; one-sentence summarizable. 6,177 words, inside the extended band (5,500–9,500). Clean. |
| F Framing integrity | Four-part structure present; audience concrete; tensions named. Clean. |
| G Extract contracts | Contract present + validates (build exit 0). Clean. |
| H/I/K/R Choreography | Welcome + summary + closing-landing present. Interruption-avoidance (K1) and formal-transition DENY (R4) not explicitly present, but the current compact framing format validated clean; left as P2-advisory rather than risk a format regression. |
| Q Host parity | Host A male scholar/teacher; Host B female seeker/questioner/challenger — both in-pool (Q1/Q2 ✓); voice-gender declared (Q4 ✓). |
| T Doctrinal | Clean — 0 findings. No forbidden Imam-title/name pairing; lineage correct. |
| U Scholarly rubric | No AI-cliché, no faux-profundity opener, no deep-dive self-reference, no external essentialism. Clean. |
| V Interest | Curiosity hook ("Picture a room…"), challenge-defeat arc (imitation vs assimilation), fair framing of both Sunni/Shi'i readings. Clean. |
| W Augmentation | enable_knowledge_augmenter: false; no augment ledger. N/A. |

## Health metrics

| Chapter | Words | Band | Arabic transliterations | Quran cites | Honorific (ع) | Pronunciation gaps |
|---|---|---|---|---|---|---|
| ch01a ali-and-the-prophet | 6,177 | extended (5,500–9,500) ✓ | 7 (proper names) | 10, all canonical form | 91 (spoken once via framing) | 5 unsettled terms (advisory) |
