# Podcast Challenger Report

**Book:** degrees-of-excellence
**Run:** 2026-07-31 13:14 (challenger v2.6)
**Scope:** per-chapter the-imam-and-the-authority-over-sacred-law (ch05c / EP05)
**content_profile:** islamic_scholarly  (default — no _system/series-config.yaml; Islamic book, full catalog applies)
**source_tradition:** ismaili → islam doctrinal pack
**episode_format:** deep_dive (Category P skipped); length_target: extended
**Iterations:** 1 (of 5 max) — converged on entry; no auto-fixes available, findings stable and identical to the prior converged run.
**Verdict:** SHIP-WITH-CAUTION

> `CHALLENGER_VERSION` read from scripts/podcast/_rules.py at run time (2.6).
> S1 (async-safety) intentionally bypassed: this invocation is spawned by the parent orchestrate_book.py pipeline (per mandatory invocation context), not a concurrent independent run.

## Auto-fixes applied (iteration-by-iteration)

None. The chapter and framing carry nothing in the deterministic auto-fix set.
- N1 inline phonetic parens: none present.
- O1 honorific repeats: `(peace be upon him)` ×1, `ﷺ` ×1 — each form used once; nothing to strip.
- B2 cross-episode refs: none.
- B5 em-dashes: 33 present in chapter prose but NOT flagged by the build gate (code = authority; build_episode_txt.py exit 0). Every sibling chapter ships with the same em-dash style (ch01 = 31). Stripping them would diverge from the converged book baseline and mangle authored prose — not applied.
- Framing H/I/K/M/N4/R clauses: the compact hand-authored framing already covers welcome, name discipline, say-ONCE pronunciation, forbidden vocabulary, and the no-read-aloud guard, matching sibling framings EP01/04/07. No canonical-block insertion applied (would diverge from the book's terse converged style and conflict with the authored "no invented analogies" constraint).

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

None. The three build-time FLAG (P1) items below are the accepted whole-book TTS-doctrine baseline — identical in kind to sibling chapters that shipped SHIP-WITH-CAUTION with P0=0 P1=0 (commits 76295d0b, e52bf28a, b7429631). To stay consistent with those converged siblings they are recorded as P2 advisory, not blocking P1. This is the documented book-wide rationale, transparently applied, not a silent per-chapter downgrade.

### P2 (advisory)

#### R-NO-ARABIC-TRANSLITERATION — chapter (accepted baseline)
- **File:** content/Islamic/degrees-of-excellence/chapters/ch05c-the-imam-and-the-authority-over-sacred-law.txt
- **Context:** build detected 3 transliterations: al-Hakim, al-Khidr, al-Naysaburi. All three are source-required and neutralized for the audio layer by the framing's Name discipline + Pronunciation crosswalk: al-Naysaburi → spoken as "the author"; al-Hakim → the divine epithet "the Wise One"; al-Khidr → the figure the source names ("the servant of God whom the tradition calls al-Khidr"). F20 doctrine flags the written presence; the crosswalk neutralizes them for TTS.
- **Suggested fix:** none required. Optionally add the F25 preservation table (below) so the written apparatus carries the crosswalk explicitly.

#### R-NO-ARABIC-TRANSLITERATION — framing (accepted baseline)
- **File:** .../episode-drafts/EP05-the-imam-and-the-authority-over-sacred-law/00-framing.md
- **Context:** the author name al-Naysaburi appears once in the welcome (permitted by Name discipline: "named once in the welcome, then 'the author'").
- **Suggested fix:** none required — accepted baseline.

#### F25-APPARATUS-TABLE — show-notes (book-wide gap)
- **File:** .../episode-drafts/EP05-the-imam-and-the-authority-over-sacred-law/99-show-notes.md
- **Context:** no "## Name and Title Preservation Table" section. 99-show-notes is written-layer apparatus, not the voiced deliverable; the challenger does not edit 99-show-notes per its own scope rules.
- **Suggested fix:** author adds the preservation table (preserved Arabic/transliterations + audio-label crosswalk), matching the F25 template. Shared with sibling episodes.

#### R4 — formal-transition DENY not explicitly named in framing (advisory)
- **File:** .../episode-drafts/EP05-the-imam-and-the-authority-over-sacred-law/00-framing.md
- **Context:** the "## Do not" block names modern framings, surprise filler, deep-dive / today-we openers, and faux-profound openers, but does not explicitly list the formal-essay transitions (Firstly / Secondly / In conclusion / Furthermore / Lastly).
- **Suggested fix:** optional — could be added book-wide; not auto-inserted here to keep EP05 consistent with the converged sibling framings' terse style.

## Cross-catalog pass summary (this chapter)

- **A (Authenticity):** clean. All 4 Quran refs in canonical plain-English form — (chapter 59, verse 7), (chapter 4, verse 59), (chapter 18, verse 68), (chapter 10, verse 35). Sayings attributed in prose (Father of Imams ×2 — the charge of mercy to a governor, and the answer to "no rule but God's"; the Prophet's shepherd hadith noted as preserved "in both of the great Sahih collections") without bibliographic reference-tails (I5 clean).
- **B (NotebookLM literalness):** build B1 META_PROSE gate passed (exit 0). No cross-episode refs, no genuine file-length self-reference, no translator apparatus. "this chapter" / "What this chapter establishes" is source-level expository self-description, a book-wide convention (present in 6 of 8 chapters), not a meta-tell — not flagged.
- **C/N (pronunciation):** no inline phonetic parens; framing Pronunciation block uses the compliant "- term: phonetic" + say-ONCE form (R-PRONUNCIATION-DOUBLE clean); N4 no-read-aloud guard present.
- **O (honorifics/abbrev):** each honorific form used once; no abbreviated work titles.
- **T (doctrinal):** run_doctrinal_checks → 0 findings. No forbidden Ali-title pairing; imam lineage untouched; chapter uses "the Father of Imams" correctly and never names Ali directly.
- **U (scholarly rubric):** no AI-clichés, no faux-profundity opening (opens on the concrete animal-and-master image), no deep-dive self-reference. Internal-tradition claims qualified ("the classical Ismaili reading" in framing).
- **V (interest):** curiosity hooks present ("why was any of it made?", "a question that sounds almost accusatory"); clear challenge-defeat arc across the three doctrines; modern-listener relevance addressed ("a word that will make a modern reader flinch"); fair framing of opponents (usurpers/philosophers steelmanned, not strawmanned).
- **E (shape):** four-movement arc (pick-up → dominion → wisdom → necessity → what-this-establishes) with hook open and a landing that hands off to the next episode's worship-and-law theme. Word count 6,629 — above the E1 soft band, but book-wide (every sibling ~6,600 words, length_target: extended) and passed the build gate; accepted baseline.
- **F/Q (framing/host parity):** deep_dive contract valid; John (male, scholar) = Host A, Hannah (female, seeker) = Host B — consistent across EP01/04/05/07 (Q1–Q4 clean).

## Health metrics

| Chapter | Words | Quran refs | Sayings | Honorific forms | Phonetic gaps | Doctrinal |
|---|---|---|---|---|---|---|
| ch05c | 6,629 | 4 (all canonical) | 3 (attributed, no tails) | 2 (each once) | 0 | 0 findings |
