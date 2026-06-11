# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-06-11 (challenger v2.5)
**Scope:** per-chapter three-levels-of-knowledge
**Iterations:** 1 (of 5 max)
**Verdict:** SHIP-WITH-CAUTION

## Auto-fixes applied

None this iteration. Build script validation passed cleanly on the chapter source and emitted the customize-prompt episode txt without errors.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### F25: 99-show-notes apparatus table absent
- **File:** content/Islamic/the-master-and-the-disciple/_system/episode-drafts/EP08-three-levels-of-knowledge/99-show-notes.md
- **Context:** build_episode_txt.py flagged F25 — no `## Name and Title Preservation Table` section. Doctrine: every episode's 99-show-notes.md carries the written-layer apparatus (preserved Arabic / transliterations + audio-label crosswalk).
- **Out of agent auto-fix scope** (Section 8 — 99-show-notes.md is published-library apparatus, never edited by this agent). Author resolves.

### P2 (advisory)

#### CS2: Chapter title length
- **File:** chapters/ch08a-three-levels-of-knowledge.txt
- **Context:** Working title is 9 words ("Three Levels of Knowledge — Angels, Humans, and Beasts"), exceeds the 6-word soft target from INVARIANT 6. Under the 60-char hard cap. Advisory only.

## Health metrics

| File | Words | Notes |
|---|---|---|
| ch08a-three-levels-of-knowledge.txt | 2,332 | In-band (1,800–2,800 default deep dive). Citations: Corbin, Schimmel, Peak of Eloquence saying 147, Quran 7:26 + 3:103. Em-dashes (16) used in normalized narrative form. |
| EP08-three-levels-of-knowledge/00-framing.md | 693 | In-band (200–2,000 default soft band). All R-* blocks present: Name discipline, Pronunciation (imperative), Do not (DENY-modernize + DENY-surprise), R-RECURRING-THESIS spine. |

## Gate summary (per-category)

- **A (citations):** clean — Quran 7:26, 3:103, *Peak of Eloquence* saying 147 (full publication data), Corbin + Schimmel with page ranges. Tradition firewall observed (Ismaili tafsir distinguished from Sufi / Sunni overlap).
- **B (meta-prose):** clean. Build script validated chapter + framing.
- **C (phonetics):** clean — Arabic terms (zahir, batin, taqwa, Hujja, Bab, alim rabbani, al-amal al-salih, la hawla wa la quwwata illa billah) all glossed inline in chapter; framing carries imperative `Pronounce` block with "say ONCE" directive.
- **D (enrichment):** multi-tier (Tier 2 Quran, Tier 3 Peak of Eloquence Shi'i collection, Tier 6 Corbin + Schimmel academic).
- **E (shape):** beginning/middle/close arc present. One-sentence summarizable.
- **F (framing integrity):** four-part structure intact (Opening directive, Three-part focus, Pronunciation, Do not). Audience+tensions implicit through spine.
- **N (phonetic-as-content):** zero inline phonetic parens. Imperative Pronunciation block in framing.
- **O (honorifics):** "(may Allah be pleased with him)" appears once. No abbreviation tells.
- **Q (host parity):** Host A male scholar / Host B female seeker — matches book-wide pattern across EP02–EP13.
- **T (doctrinal):** no forbidden naming-convention phrases. Father of Imams referenced via "Commander of the Faithful". Ismaili lineage intact.
- **U (scholarly rubric):** no AI-cliché / faux-profundity / premature-closure / deep-dive-self-reference / essentialism tells.
- **CS (chapter-set):** ch08 title 9 words (P2 advisory). No name/slug bleed into ch08.

