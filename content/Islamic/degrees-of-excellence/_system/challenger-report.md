# Podcast Challenger Report

**Book:** degrees-of-excellence
**Run:** 2026-07-31 2:39 PM EST (challenger v2.6)
**Scope:** per-chapter worship-alms-and-war-void-without-the-imam (EP06 / ch06d)
**Iterations:** 1 (of 5 max)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  (no series-config.yaml; default applied — full check catalog)

> **No P0 anywhere; the chapter is upload-ready.** Doctrinal gate clean (T1–T5 = 0 findings), the build gate writes the episode txt (exit 0), the contract validates (exit 0), chapter-set has no P0, and host-role parity holds book-wide. The only open items are systemic, by-design conditions shared by all eight episodes and already accepted in the five shipped siblings — none is a defect unique to this chapter, and EP06 is in fact cleaner than EP05/EP08 (its framing carries no Arabic-transliteration flag).

## Category S — async-safety
S1 bypassed by pipeline directive: the visible `orchestrate_book.py` is THIS run's parent, not a concurrent orchestrator. S2–S6: no journal/_shared write paths in chapter or framing; no scope-out writes. Clean.

## Auto-fixes applied
None. No deterministic auto-fix condition fired:
- Em-dashes (96 in chapter) are NOT enforced by the current rule modules / build gate and are a consistent authorial device across all 8 chapters and the 5 shipped episodes. Auto-stripping would corrupt the book's voice and diverge from shipped work. The catalog's B5 entry is stale relative to code authority (Section 0: "the Python rule modules ARE the contract").
- No inline phonetic parens (N1), no repeated honorific expansions (O1/C3: "peace be upon him" appears once), no cross-episode references (B2), no exact-match filler tells (E4).

## Findings requiring author resolution

### P0 (blocks ship)
None.

### P1 (ship-with-caution)
None unique to this chapter.

### P2 (advisory — systemic, book-wide, by-design; carried, not auto-fixed)

#### F25 — apparatus table missing in 99-show-notes.md (book-wide)
- **File:** _system/episode-drafts/EP06-.../99-show-notes.md
- **Context:** build gate flags no `## Name and Title Preservation Table`. Confirmed MISSING in ALL 8 episodes — a systemic gap in the show-notes apparatus, not this chapter. 99-show-notes.md is out of the challenger's editing scope (Section 8). The five shipped siblings carry the same gap and shipped SHIP-WITH-CAUTION.
- **Resolution:** flag for the pipeline/author to backfill the apparatus table book-wide.

#### F20 — Arabic transliterations in the SOURCE chapter (contract-permitted)
- **File:** chapters/ch06d-...txt
- **Context:** build gate names al-Naysaburi, al-Shafi, Abu Hanifa. These are the author's name and the four jurists the contract's `tone_constraints` EXPLICITLY permit ("al-Shafi'i, Abu Hanifa, Malik, and Ahmad b. Hanbal may be named, as the source names them"). This is the intended written-source-vs-audio-label split (F25): the framing instructs hosts to say "the author" / "the four Sunni school-founders", so the audio stays TTS-safe while the written source keeps the names. Accepted by design.

#### E1 — chapter length 5,985 words (above the 4,500 soft-band ceiling)
- **Context:** `length_target: extended`; all eight chapters run ~5,500–6,000 words by design. The build gate accepts it (exit 0). Consistent extended-tier book design; long-chapter handling is a known pipeline path. Advisory only.

#### CS8/P8 — recurring saying shared with the imamate-pole chapter
- **Context:** shares 4 distinct 12-word passages with `the-imamate-pole-and-foundation-of-religion` — the "earth is never empty of one who stands for God with a proof" saying of the Father of Imams, a liturgical/recurring citation quoted in both. Book-scope authoring decision; CS is never auto-fixed.

## Category-by-category
- **A (authenticity):** Quranic citations all in canonical plain-English `(chapter N, verse M)` form (7 verses, all correct). al-Shafi'i quote and the Father-of-Imams sayings named inline with speaker, NO bibliographic reference tails (A1 clean). No `[VERIFY CITATION]`, no fabricated hadith. Clean.
- **B (literalness):** meta-prose gate passed; no cross-episode refs; all quotes attributable to the source treatise. Clean.
- **C/N (pronunciation/phonetics):** no inline phonetics; framing `## Pronunciation` uses the current-correct list form (`- qibla: prayer-direction`) with an explicit say-ONCE guard — the catalog's N2 imperative-form text is inverted by the newer R-PRONUNCIATION-DOUBLE rule, which the build gate enforces. N6 Arabic-script-required does NOT apply: this book runs the F20 English-only TTS-safe audio doctrine (no glossary.yml; build gate authoritative and passing). Clean.
- **D (enrichment):** faithful single-treatise exposition (`angle: faithful_exposition`); no quote-stacking, no `[CONTEXT NEEDED]`. Clean.
- **E (shape):** strong curiosity hook open, pressure-building middle, landed close on the worshipper's turn. One-sentence summarizable. E1 length advisory above.
- **F (framing integrity):** framing exists, 4-part structure, concrete audience, 3 named tensions, steering present. Clean.
- **G (contracts):** contract present, fully populated, validates via extract_chapter --force (exit 0), meta-prose clean, no derived_from. Clean.
- **H/I/K (welcome/anti-repetition/interruption):** welcome + one-sentence preview + landing-on-question all present; R-RECURRING-THESIS governs repetition intentionally; host dynamic names challenges/concession and forbids bare affirmations. Clean.
- **M (modernize/surprise):** `## Do not` names Twitter, social media, algorithm, "wow", "right?", "deep dive", "today we'll discuss", faux-profound openers. Clean. No transcript present — empirical loop not run.
- **O (honorifics/abbrev):** one honorific expansion; no abbreviated work titles. Clean.
- **Q (host-role parity):** John (male, scholar) / Hannah (female, seeker) — matches HOST_A/HOST_B pools; verified identical across all 8 framings. Clean.
- **R (choreography):** `## Do not` covers surprise/modernize; R4 formal-transition list and R5 modern-analogy permission intentionally absent (this book forbids modern framings and caps analogies at 3 source images — R5 would contradict the design). Advisory only.
- **T (doctrinal):** 0 findings (chapter + framing). "Imam Ali" forbidden pairing absent; first imam referred to as the Commander of the Faithful / the Father of Imams. Clean.
- **U (scholarly-conversation):** no AI-clichés (the "deep dive"/"today" strings appear only inside the framing DENY list), no faux-profundity opening, no deep-dive self-reference. Clean.
- **V (interest):** opens on a genuine curiosity hook; challenge-defeat arc (opponents steelmanned then refuted on their own principles); no strawman. Strong.
- **CS (chapter-set):** no P0; 6 P1 + 4 P2 at book scope, only one P1 touches this chapter (the recurring saying above).

## Health metrics
| Chapter | Words | Quran citations | Format | Honorific reps | Inline phonetics | Arabic script |
|---|---|---|---|---|---|---|
| ch06d | 5,985 | 7 (all canonical form) | deep_dive | 0 | 0 | 0 (F20 English-only audio doctrine) |

## Verdict rationale
SHIP-WITH-CAUTION with zero P0 and zero chapter-unique P1 — identical baseline to the five shipped siblings, whose systemic F20/F25 advisories hold the whole book at CAUTION rather than READY. EP06 carries no defect its siblings did not, and its framing is cleaner than EP05/EP08.
