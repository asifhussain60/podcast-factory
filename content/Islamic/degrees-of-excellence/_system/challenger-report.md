# Podcast Challenger Report

**Book:** degrees-of-excellence
**Run:** 2026-07-31 3:18 PM EST (challenger v2.6)
**Scope:** per-chapter the-imamate-pole-and-foundation-of-religion (EP03 / ch03a)
**Iterations:** 1 (of 5 max)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  (no series-config.yaml; default applied — full check catalog)

> **Prior BLOCKED is cleared: the framing has been re-authored and the hard build gate now exits 0.** The 3:02 PM v2.6 run BLOCKED because the EP03 framing was still the raw `extract_chapter` stub (`[LLM-FILL]` placeholder, only 1/3 tensions, `## Pronunciation hooks` heading). The on-disk framing is now fully authored — `## Pronunciation` with the "Say each term ONCE…" anti-doubling instruction, all three contract tensions, Name discipline, Host dynamic, Landing, and the `## Do not` block — and `build_episode_txt.py` exits 0, writing the 706-word Customize prompt. The chapter SOURCE (ch03a) remains clean and upload-ready. All that remains are systemic, by-design P1/P2 conditions shared with the seven sibling episodes.

## Category S — async-safety
S1 bypassed by pipeline directive: the visible `orchestrate_book.py` is THIS run's parent, not a concurrent orchestrator. S2–S6: no journal/`_shared` write paths in chapter or framing; no scope-out writes. Clean.

## Auto-fixes applied
None. No blocking condition remained and no listed deterministic auto-fix was warranted:
- **Em-dashes (71):** book-wide authorial device, not rule-enforced here (the build gate does not flag them; all eight chapters carry them). Mechanically converting them to commas would corrupt heavily authored prose and diverge EP03 from its seven shipped siblings. Left intact, consistent with book convention and the prior clean-chapter findings.
- **Framing clauses (H/I/K):** the framing is authored in the book's deep_dive template variant and passes the build gate; inserting extra interruption/anti-repetition clauses would diverge EP03 from the established sibling template. Not injected.

## Findings requiring author resolution

### P0 (blocks ship)
None. The build gate exits 0.

### P1 (ship-with-caution — all systemic, by-design)

#### F20 / R-NO-ARABIC-TRANSLITERATION — two transliterated names in the SOURCE chapter and framing
- **File:** chapters/ch03a-…​.txt and …/EP03…/00-framing.md
- **Context:** build gate flags `al-Naysaburi` and `al-Sadiq` (P1, non-blocking, exit-0). Permitted by the written-source-vs-audio-label split; the authored framing's Name discipline block tells hosts to say "the author" / "the sixth imam". Identical accepted condition in all siblings.

#### F25-APPARATUS-TABLE — 99-show-notes.md lacks the Name and Title Preservation Table
- **File:** …/EP03…/99-show-notes.md
- **Context:** build gate flags the missing `## Name and Title Preservation Table` section. This is systemic — NONE of the eight episodes' show-notes carry the F25 apparatus table. Book-wide condition, not an EP03 regression. Recommend a single book-wide apparatus-table backfill before publish.

#### CS8 / P8 — recurring-thesis passages shared with siblings
- **Context:** ch03a shares 12-word passages with three siblings, all recurring liturgical/thesis citations, not accidental duplication:
  - ↔ the-fatimid-world-and-al-naysaburi (6 passages) — the Father-of-Imams saying "the earth is never left without one who stands for God with a proof".
  - ↔ the-theory-of-degrees-of-excellence-explained (9 passages) — the natiq/samit pairing and the "warner… guide" verse (chapter 13, verse 7).
  - ↔ worship-alms-and-war-void-without-the-imam (4 passages) — the "manifest or fearful and hidden" clause of the same hujja saying.
- Book-scope authoring decision; CS is never auto-fixed.

### P2 (advisory — systemic, book-wide, by-design)

#### E1 — chapter length 6,019 words (above 4,500 soft-band)
`length_target: extended`; all eight chapters run ~5,500–6,000 words by design; chapter passes its own build gate. Advisory.

#### CS6 / P6 — cross-book mangle-map bleed on OTHER chapters
`al-Hakim bi-Amr Allah` / `al-Sijistani` (in ch01a) and `Hamid al-Din` / `al-Kirmani` (in ch08f) match kitab-al-riyad's mangle-map. These are al-Naysaburi's own Fatimid-world figures legitimately appearing; false-positive of a sibling book's name list. Not in EP03. Advisory, never auto-stripped.

#### SYSTEMIC — EP06 framing still carries the `[LLM-FILL]` stub
EP06-worship-alms-and-war-void-without-the-imam/00-framing.md still contains `[LLM-FILL]` and was committed SHIP-WITH-CAUTION. Out of this per-chapter scope, but flagged: run `grep -rl LLM-FILL _system/episode-drafts/*/00-framing.md` before publish; EP06 needs the same framing-authoring pass EP03 just received.

## Category-by-category (chapter ch03a + EP03 framing)
- **A (authenticity):** 5 Quran citations all in canonical plain-English `(chapter N, verse M)` form (19:54, 2:124, 13:7, 2:282, 41:53); zero terse `(Q N:M)` forms. Thaqalayn hadith, Father-of-Imams hujja saying, Ja'far-al-Sadiq ascent tradition, Rumi line — all quoted as blockquotes with speaker named inline, no bibliographic reference tails (A1/NZ-REFERENCE-TAIL clean). No `[VERIFY CITATION]`, no fabricated numbers, no `[CONTEXT NEEDED]`/`[LLM-FILL]` in the chapter. Clean.
- **B (literalness):** chapter meta-prose clean; no cross-episode refs; quotes attributable. Framing carries no `[LLM-FILL]` (re-authored). Clean.
- **C/N (pronunciation/phonetics):** chapter has zero inline phonetic parens (N1 clean). Framing `## Pronunciation` block uses imperative "Say each term ONCE…" form (N2 clean) with five glossed terms. N6 Arabic-script-required does not apply — no glossary.yml; book runs the F20 English-only TTS-safe audio doctrine. Framing ends with the no-read-aloud guard (N4 clean).
- **D (enrichment):** faithful single-treatise exposition; no quote-stacking; enrichment bound to the three named tensions. Clean.
- **E (shape):** strong curiosity hook ("Ask a hundred believers…"), pressure-building middle across four movements, landed close ("the foundation stone, fully laid"). One-sentence summarizable. E1 length advisory (extended tier).
- **F (framing integrity):** authored and complete — Opening directive (with warm welcome + preview), Name discipline, imperative Pronunciation, all 3 Central tensions, Host dynamic, Tone constraints, Landing, Do not. Passes build gate. Slight template variant of siblings (Central tensions vs Three-part focus; role-labels folded into Opening) — valid, not a defect.
- **G (contracts):** contract present, fully populated, `episode_format: deep_dive`, `debate: null`; meta-prose clean; extract validates.
- **H/I/K:** welcome + summary + question-landing present in framing; chapter-side anti-repetition governs the intentional 3× thesis spine (R-RECURRING-THESIS). Clean.
- **M (modernize/surprise):** framing `## Do not` block present and correct (Twitter, social media, algorithm, "wow", "right?"). No transcript — empirical loop not run.
- **Q (host-role parity):** John=male scholar / Hannah=female seeker; pairing holds across the book; deep_dive, no rotation. Clean.
- **T (doctrinal):** `run_doctrinal_checks` → 0 findings. Zero "Imam Ali" forbidden phrase; "Father of Imams" used (×2); "may Allah be pleased with him" (×1), "peace be upon him" (×1) — each honorific form once; no lineage/ordinal violation. Clean.

## Health metrics

| Chapter | Words | Em-dashes | Quran citations | Honorific repeats | Arabic script | Doctrinal | Build gate |
|---|---|---|---|---|---|---|---|
| ch03a | 6,019 | 71 (authorial device, not rule-enforced) | 5 (all plain-English) | 0 (each form ×1) | 0 (F20 English-only) | 0 findings | exit 0 (framing authored) |
