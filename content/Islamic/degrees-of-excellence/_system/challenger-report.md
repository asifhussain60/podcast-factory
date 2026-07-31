# Podcast Challenger Report

**Book:** degrees-of-excellence
**Run:** 2026-07-31 12:57 (challenger v2.6)
**Scope:** per-chapter the-fatimid-world-and-al-naysaburi (ch01a / EP01)
**Iterations:** 1 (of 5 max — converged; no auto-fixes available, findings stable vs prior run)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  ← default (no _system/series-config.yaml on disk)
episode_format: deep_dive · length_target: extended

> S1 async-safety gate BYPASSED for this invocation: the visible orchestrate_book.py process is THIS pipeline's parent (it spawned this challenger call), not a concurrent independent run.

## Gate results (deterministic, authoritative — re-run this pass)

| Gate | Script | Result |
|---|---|---|
| Build (chapter SOURCE + framing) | build_episode_txt.py | EXIT 0 — validated; episode txt emitted (700 words). 3 P1 flags (below) |
| Doctrinal T1–T5 | _doctrinal.run_doctrinal_checks | 0 findings |
| Chapter-set CS (book-scope) | check_chapter_set.py | 8 chapters; ch01a-touching findings folded below |
| Meta-prose B1/B3 | META_PROSE_TELLS + scan | clean (no file-length self-refs; no meta-prose tells caught by the authoritative list) |
| Honorific discipline O1 | per-form count | clean (1× ﷺ, line 49, first-mention only; no repeated expansions) |
| Quran citation A1 | plain-English form scan | clean — both refs now `(chapter N, verse M)` |
| Framing structural validators | build gate | name-discipline + dramatic-arc now PASS (were P1 in the 12:50 run; fixer pass resolved them) |
| Host role parity Q1–Q4 | framing scan | John (male, scholar) / Hannah (female, seeker) — in canonical pools |
| Host parity book-wide Q3 | sibling EP04 + EP07 framings | consistent (same pair across all three emitted framings) |

## Change since the 12:50 run — three actionable items RESOLVED

The prior run flagged three actionable P1s; the intervening fixer pass (re-saved chapter 12:54, framing re-emitted) resolved all three, confirmed by re-running the gates this pass:

- **R-QURAN-CITATION-FORMAT** — RESOLVED. Chapter now carries `(chapter 39, verse 9)` (line 35) and `(chapter 6, verse 165)` (line 69). Zero terse colon-form citations remain.
- **R-NAMEDISCIPLINE** — RESOLVED. Framing role-labels carry the `→ a / b / c` rotation for the Father of Imams (line 9); the build gate no longer flags name-discipline.
- **R-DRAMATIC-ARC** — RESOLVED. Framing `## Three-part focus` carries `Arc: crisis / failed answer / pivot / stakes` (line 28); the build gate no longer flags dramatic-arc.

## Auto-fixes applied (iteration-by-iteration)

None. No auto-fixable finding is present. The three actionable items above were already resolved upstream by the fixer pass before this invocation; the em-dashes (31) are deliberately preserved under this book's TTS-safe prose architecture (see Deliberate non-actions).

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution) — all non-actionable for this chapter

#### R-NO-ARABIC-TRANSLITERATION — chapter SOURCE carries 6 transliterations
- **File:** content/Islamic/degrees-of-excellence/chapters/ch01a-the-fatimid-world-and-al-naysaburi.txt
- **Context:** Detector sample: al-Naysaburi, al-Sijistani, Abu Ya[qub], Salamiyya, al-Aziz, al-Hakim. F20 doctrine prefers English audio labels.
- **Note:** Design-accepted at source level. "al-Naysaburi" is the author's name in the written SOURCE (the framing steers the AUDIO to say "the author"); the imam-caliphs (al-Aziz, al-Hakim) and the philosopher (al-Sijistani) are historical figures the framing maps to English labels. Surfaced by the build gate as P1; flag only, no action.

#### R-SURAH-ENGLISH-ONLY — surah-name heuristic flagged 'ibrahim'
- **File:** content/Islamic/degrees-of-excellence/chapters/ch01a-the-fatimid-world-and-al-naysaburi.txt
- **Context:** The token 'ibrahim' matched the surah-name detector.
- **Note:** FALSE POSITIVE. 'Ibrahim' here is the author's patronymic — "Ahmad b. Ibrahim al-Naysaburi" — not a Quranic chapter reference. No surah is named in the chapter. Flag only; no action.

#### F25-APPARATUS-TABLE — 99-show-notes.md missing the Name and Title Preservation Table
- **File:** content/Islamic/degrees-of-excellence/_system/episode-drafts/EP01-the-fatimid-world-and-al-naysaburi/99-show-notes.md
- **Note:** 99-show-notes.md is outside the challenger's editable scope and does not flow to NotebookLM audio. Resolved by the framing/show-notes generator, not by this agent. Flag only.

#### CS8 / P8 — book-scope duplication with ch03a (the-imamate-pole-and-foundation-of-religion)
- **File:** content/Islamic/degrees-of-excellence/chapters/ch01a-the-fatimid-world-and-al-naysaburi.txt:59
- **Context:** ch01a and ch03a share 6 distinct 12-word passages. Sample: "the earth is never left without one who stands for God with a proof…" — the Father of Imams' saying that the earth is never without a proof (line 59 here).
- **Note:** This is the treatise's own load-bearing doctrinal formula, the kind CS8 nominally excludes as a liturgical formula; the n-gram scanner caught it anyway. Likely acceptable recurrence of a signature saying. Book-scope authoring judgment: the author may vary the wording or trim the quotation in one of the two chapters. Does not affect the ch01a per-chapter verdict.

### P2 (advisory)

#### CS6 / P6 — cross-book name bleed (2 tokens)
- **File:** content/Islamic/degrees-of-excellence/chapters/ch01a-the-fatimid-world-and-al-naysaburi.txt
- **Context:** 'al-Hakim bi-Amr Allah' and 'al-Sijistani' also appear in book kitab-al-riyad's mangle-map.
- **Note:** FALSE POSITIVE — both are shared Islamic historical figures (the Fatimid imam-caliph al-Hakim; the Ismaili philosopher al-Sijistani) that legitimately appear across multiple books on Fatimid thought. Advisory; never auto-stripped.

#### B2-semantic — mild forward-reference / series language in the SOURCE
- **File:** content/Islamic/degrees-of-excellence/chapters/ch01a-the-fatimid-world-and-al-naysaburi.txt:3, :13, :17, :65, :75
- **Context:** "the book this series is built around", "the later episodes have a map", "as we will see next", "that is the machine we will spend this series inside".
- **Note:** Not caught by the authoritative META_PROSE_TELLS list (build B1/B2 clean). This is the authored voice of an explicit framing/doorway episode. The AUDIO risk is mitigated: EP01's framing `## Do not` block directs the hosts to "not pre-announce what comes next or reference other installments." Advisory only — the framing overrides the source-level phrasing; no chapter edit recommended.

## Deliberate non-actions (superseded checks — NOT applied)

- **B5 (em-dashes):** 31 present. The agent-spec B5 auto-fix predates this book's TTS-safe prose architecture; the authoritative build gate permits em-dashes and the pipeline produces them intentionally as authored voice. Auto-stripping would corrupt the prose. Not applied (consistent with the ch07e / 12:50 runs).
- **N6 (Arabic script required):** chapter contains 0 Arabic characters and the book has no glossary.yml. This conflicts with the F20 R-NO-ARABIC-TRANSLITERATION doctrine the build gate actively enforces. Per the Category-U tradition-precedence rule, TTS-safety wins. Not flagged P0.
- **A3 (translator provenance):** Quran is rendered in plain accurate English with no translator apparatus, per this book's tone_constraints and R-SURAH-ENGLISH-ONLY. Naming a translator would violate the book-wide enforced contract. Design-accepted (INFO), not P0.
- **A1 hadith citation tail:** the Prophet's saying (line 51) and the Father of Imams' saying (line 59) carry speaker attribution but no bibliographic collection/number tail. Under this book's TTS-safe architecture (NZ-REFERENCE-TAIL) bibliographic tails are chapter noise; speaker attribution alone is the correct form. Design-accepted, not flagged.

## Health metrics

| Chapter | Words | H2 sections | Blockquotes | Quran refs | Honorific gaps | Arabic-script (N6) |
|---|---|---|---|---|---|---|
| ch01a the-fatimid-world-and-al-naysaburi | 5,976 | 4 | 3 | 2 (both plain-English form — R-QURAN-CITATION-FORMAT satisfied) | 0 | 0 (N/A under F20) |

Word count 5,976 is above the 4,500–5,500 dead zone and within the enforced soft band (1,000–11,000) / hard band (500–12,000); no E1 issue.

## Content-quality notes

Strong concrete curiosity hook opens the chapter (the gold bar, the unburnable ruby, the noon sun — V1 satisfied); clear beginning/middle/end arc (doorway → Ismaili century → the scholar of Nishapur → shape of the argument → what-this-lands, E3 satisfied); steelman-then-answer on the administrative-necessity view (no strawman, V4 satisfied); Aquinas comparison and reason-as-servant analogy bind to the framing's named tensions (D3 satisfied); multi-tier enrichment (Quran, Prophet's saying, Father of Imams' saying, modern historians — D1 satisfied); no invented dialogue, no meta-prose tells, honorific and host-parity clean. No P0. All remaining P1s are design-accepted (author's own name in the source), false-positive (patronymic 'ibrahim'), out-of-editable-scope (show-notes), or book-scope authoring judgment (the shared load-bearing doctrinal saying). Verdict SHIP-WITH-CAUTION reflects the residual build-surfaced P1 flags inherent to a TTS-safe Islamic chapter; nothing here blocks ch01a from upload.
