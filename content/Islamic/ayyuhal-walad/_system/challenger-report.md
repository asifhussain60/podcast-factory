# Podcast Challenger Report

**Book:** ayyuhal-walad
**Run:** 2026-06-06 07:27 (challenger v2.4)
**Scope:** per-chapter — EP04-eight-admonitions-and-a-closing-prayer
**content_profile:** islamic_scholarly  ← detected from `_system/series-config.yaml`
**source_tradition:** ismaili-scholarly (resolves to `islam` doctrinal pack)
**Iterations:** 1 (of 5 max) — intelligent break: zero auto-fixable findings remain after prior convergence; re-run yields identical findings.
**Verdict:** SHIP-WITH-CAUTION — zero P0; remaining items are accepted P1 advisories already documented in the book-level report.

## Convergence summary

| File | Words | Build gate | P0 | P1 (new) | P1 (known/accepted) | P2 | Verdict |
|---|---|---|---|---|---|---|---|
| chapters/ch04-eight-admonitions-and-a-closing-prayer.txt | 4,296 | accepted (Longer tier 2800–4500) | 0 | 0 | 2 | 0 | SHIP-WITH-CAUTION |
| episode-drafts/EP04-…/00-framing.md | 771 | accepted (200–2000 band) | 0 | 0 | 0 | 1 | SHIP-WITH-CAUTION |

Async-safety (S1) clear: no concurrent orchestrator. Boundary contract (S2) clear: no writes outside book dir. Doctrinal Category T (T1–T5) passes clean — zero forbidden phrases, no leadership-title + Father-of-Imams personal-name pairing, no Imam lineage violations, no mis-attributions, no weak-hadith hits.

## Auto-fixes applied (this run)

None. The previously-flagged framing P1s on EP04 (R-RECURRING-THESIS not in `## Anti-noise`; Jesus honorific repeated at Beat 3) are RESOLVED in the current framing — verified at framing.md:54 (R-RECURRING-THESIS clause present) and the Jesus honorific now appears only once at line 17 inside the Name-discipline directive block. No further auto-fix candidates remain.

## Findings requiring author resolution

### P0 (blocks ship)
None.

### P1 — new issues
None for this chapter.

### P1 — known / accepted advisories (carried forward from book-level report)

These are the deferred-enrichment advisories accepted at REFINED-English level pre-re-enrichment. Confirmed present on EP04; NOT treated as blockers.

- **R-NO-ARABIC-TRANSLITERATION (F20):** transliterated forms in the chapter (`al-Ghazali`, `Shaykh al-Kamil`, `Sirat al-Mustaqeem`, `Sahah Sitta`, `Azwaj al-Mutahharat`, `Ummahatil Mu'mineen`, `Ihya al-Uloom ad-Deen`, `Ahkamul Hakimeen`, `Fard al-'ayn`, `Fard Kifaya`, `Ahl al-Bayt`, `Sirat`, `Mizan`) and in the framing's Pronunciation block (`Ghazali`, `Aisha`, `Shari'ah`, `Tawakkul`, `Nafs`, `Wajib`, `Shaytan`, `Fasiq`, `Zalim`, `Salaat`, `Fard al-'ayn`). Doctrine says replace with English audio labels at re-enrichment.
- **R-SURAH-ENGLISH-ONLY (F29):** no surah-name occurrences in this chapter — N/A.

### P2 — advisory

#### R-NAMEDISCIPLINE format style (framing-level, book-wide)
- EP04 framing (lines 14–22) uses the bulleted arrow form (`→ **label**`) for Name discipline, while EP01–03 use the prose `stable label: **X**` form. EP04's discipline is substantively complete (stable English label + honorific-once + name policy for each figure). Cosmetic; harmonize at next pass or add an explicit `Rotation:` line.

## Health metrics

| File | Words | Em-dashes | Honorific expansions in body | Phonetic gaps | Forbidden modernizations | Forbidden surprise tells |
|---|---|---|---|---|---|---|
| ch04-eight-admonitions-and-a-closing-prayer.txt | 4,296 | 32 (deliberate prose voice; build-gate accepts) | 2 (Jesus 1×, Aisha 1× — both first-mention only ✓) | 0 (all italicized Arabic terms have inline glosses or are in framing Pronunciation block) | 0 | 0 |
| EP04 framing | 771 | 7 (acceptable in framing prose) | 3 (Prophet/Jesus/Aisha — name-discipline directives only, single occurrence each ✓) | 0 | 0 (DENY block present line 60) | 0 (DENY block present line 60) |

## Category audit

| Category | Status |
|---|---|
| A — Authenticity | Clean — citations inline; translations marked; verbatim integrity preserved; no source-shifting |
| B — NotebookLM literalness | Clean — no meta-prose tells; no cross-episode refs; no file-length self-refs; no translator-apparatus prefixes; em-dashes are deliberate prose voice (accepted) |
| C — Phonetic discipline | Clean — Arabic terms glossed inline; framing Pronunciation uses imperative `Say each term ONCE` form |
| D — Enrichment | Clean — multi-tier (Quran, hadith, Ghazali's own *Ihya*), citations cluster on the eight admonitions, no quote-stacking |
| E — Articulation | Clean — 4,296w within Longer tier; one-sentence summary holds ("eight admonitions: four to refuse, four to take up"); clear arc |
| F — Framing integrity | Clean — four-part structure present; spine sentence verbatim 3× discipline declared |
| G — Extract contract | Clean — contract present, `episode_format: deep_dive`, `length_target: longer` matches actual word count |
| H/I/K — Welcome / anti-repetition / interruption | Clean — opening directive carries welcome + spine; anti-repetition rule R-RECURRING-THESIS now in `## Anti-noise rules` |
| J — Name aliasing | Clean — 8 figures mapped to stable English labels in framing |
| M — Modernization + surprise | Clean — DENY block at framing line 60; no transcript present for this episode (Loop M dormant) |
| N — Phonetic-as-content | Clean — zero inline parenthetical phonetics in chapter; framing uses imperative form |
| O — Honorific + abbreviation | Clean — each honorific first-mention only; no abbreviated work titles |
| Q — Host role parity | Clean — Host A scholar / Host B seeker declared at framing line 3, consistent with EP01–EP03 |
| R — Conversation choreography | Clean — `## Do not` block enumerates formal-transition + surprise + modernization DENY lists; cadence and reset implicit in three-part-focus structure |
| S — Safety + boundary | Clean — no concurrent orchestrator; no writes outside book dir |
| T — Doctrinal accuracy | **Clean** — no forbidden phrases; no lineage violations; canonical attributions preserved; Ghazali's `Ihya` cited authentically |
| U — Scholarly-conversation rubric | Clean — no AI-cliché, no faux-profundity opening, no premature closure, no deep-dive self-reference; tradition-internal qualification consistent (Ghazali's framework presented as his own) |
| V — Interest & engagement | Clean — opening curiosity hook ("knowledge will turn against the scholar…"), challenge-defeat arc (four refrainings → four takings-up → supplication), modern-relevance carried by the household-servant analogy, no strawman framing of opposing views |
| W — Augmentation quality | N/A — no augmentation ledger entry for this episode; chapter ships as-authored |

## PEQ Score

| Axis | Weight | Score |
|---|---|---|
| Fidelity | 30% | 92 |
| Voice | 20% | 88 |
| Structure | 18% | 95 |
| Enrichment | 17% | 86 |
| Interest | 15% | 90 |
| **Total** | **100%** | **90.6** — PASS |

Threshold reference: ≥ 85 = PASS · 70–84 = WARN · < 70 = FAIL.
