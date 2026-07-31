# Podcast Challenger Report

**Book:** degrees-of-excellence
**Run:** 2026-07-31 12:35 (challenger v2.6)
**Scope:** per-chapter prophets-as-symbols-and-the-first-caliphs (ch07e / EP07)
**Iterations:** 1 (of 5 max — converged; no auto-fixes available, findings stable)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  ← default (no _system/series-config.yaml on disk)

## Gate results (deterministic, authoritative)

| Gate | Script | Result |
|---|---|---|
| Build (chapter SOURCE + framing) | build_episode_txt.py | EXIT 0 — validated; episode txt emitted (749 words) |
| Doctrinal T1–T5 | _doctrinal.run_doctrinal_checks | 0 findings |
| Chapter-set CS (this chapter) | check_chapter_set.py | 0 findings for this chapter; 0 P0 book-wide |
| Quran citation format A1 | plain-English (chapter N, verse M) | 9 refs, 0 terse variants |
| Honorific discipline O1 | per-form count | clean (1× "peace be upon him", 1× "may God bless him", first-mention only) |
| Host role parity Q1–Q4 | framing scan | John (male, scholar) / Hannah (female, seeker) — in canonical pools |
| Host parity book-wide Q3 | sibling EP04 framing | consistent (EP04 declares the same pair) |
| Framing post-author validators | _validators_framing.py | gate-clean (deny block, recurring thesis, honorific-bounded, pronunciation-imperative, analogy-cap, dramatic-arc, name-discipline all satisfied) |

## Auto-fixes applied (iteration-by-iteration)

None. No auto-fixable finding was present. See "Deliberate non-actions" below for checks that are superseded by this book's TTS-safe (F20/F25) architecture and were correctly NOT applied.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION — chapter SOURCE carries 2 transliterations
- **File:** content/Islamic/degrees-of-excellence/chapters/ch07e-prophets-as-symbols-and-the-first-caliphs.txt
- **Context:** Detector sample: "Abu Bakr", "al-Naysaburi". F20 doctrine prefers English audio labels.
- **Note:** Design-accepted at source level — "Abu Bakr" is explicitly permitted by the framing name-discipline (caliphs may be named), and "al-Naysaburi" is the author's name in the written SOURCE (the framing steers the AUDIO to say "the author"). Surfaced by the build gate as P1; not challenger-auto-fixable (content-authoring decision). Author may leave as-is given the framing handles the audio layer.

#### R-NO-ARABIC-TRANSLITERATION — framing CUSTOMIZE PROMPT carries 2 transliterations
- **File:** content/Islamic/degrees-of-excellence/_system/episode-drafts/EP07-prophets-as-symbols-and-the-first-caliphs/00-framing.md
- **Context:** Detector sample: "Abu Bakr", "al-Naysaburi". Both appear inside the name-discipline block that MAPS them to English audio labels, so this is the framing doing its job; the heuristic flags the tokens regardless.
- **Note:** Design-accepted. Flag only.

#### F25-APPARATUS-TABLE — 99-show-notes.md missing the Name and Title Preservation Table
- **File:** content/Islamic/degrees-of-excellence/_system/episode-drafts/EP07-prophets-as-symbols-and-the-first-caliphs/99-show-notes.md
- **Context:** No "## Name and Title Preservation Table" header. F25 doctrine: each episode's show-notes carries the written-layer apparatus (preserved Arabic / transliterations + audio-label crosswalk) the TTS-safe audio omits.
- **Note:** 99-show-notes.md is outside the challenger's editable scope and does not flow to NotebookLM audio. Resolved by the framing/show-notes generator, not the challenger. Flag only.

### P2 (advisory)

None.

## Deliberate non-actions (superseded checks — NOT applied)

- **B5 (em-dashes):** 79 present. The agent-spec B5 auto-fix predates this book's TTS-safe prose architecture. The authoritative build gate permits em-dashes and the pipeline produces them intentionally as authored voice; auto-stripping 79 would corrupt the prose. Not applied.
- **N6 (Arabic script required):** chapter contains 0 Arabic characters and the book has no glossary.yml. This directly conflicts with the F20 R-NO-ARABIC-TRANSLITERATION doctrine the build gate actively enforces (it flags transliterations for REMOVAL). Per the Category-U tradition-precedence rule, TTS-safety wins. Not flagged P0.
- **A3 (translator provenance):** Quran is rendered in plain accurate English with no translator apparatus, per this book's tone_constraints and R-SURAH-ENGLISH-ONLY. Naming a translator would violate the book-wide enforced contract. Design-accepted (INFO), not P0.
- **Old-architecture framing clauses (H/I/K/M/N/R):** the compact v2.6 framing format is enforced by _validators_framing.py, which the framing passes. Hand-injecting the older verbose clauses would fight the current generator. Not applied.

## Health metrics

| Chapter | Words | H2 sections | Blockquotes | Quran refs | Honorific/phonetic gaps | Arabic-script (N6) |
|---|---|---|---|---|---|---|
| ch07e prophets-as-symbols-and-the-first-caliphs | 6,083 | 5 | 5 | 9 | 0 | 0 (N/A under F20) |

Content-quality notes: clear beginning/middle/end arc (argument-pickup → Adam/Noah → qibla-as-sign → virtues/caliphs → what-this-establishes); cross-tradition citation (Noah's-ark hadith) explicitly annotated as "transmitted by his opponents" (A6 satisfied); curiosity hook opens the chapter; modern-relevance signal present; steelman-then-refute structure (no strawman). Doctrinal lineage and naming clean.
