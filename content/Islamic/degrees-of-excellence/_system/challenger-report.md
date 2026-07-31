# Podcast Challenger Report

**Book:** degrees-of-excellence
**Run:** 2026-07-31 (challenger v2.6)
**Scope:** per-chapter the-theory-of-degrees-of-excellence-explained (ch02b / EP02)
**Iterations:** 1 (of 5 max) — converged on entry; the prior terse-citation P1 is already resolved on disk, no in-allowlist auto-fixes remain, findings stable.
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  ← default (no content_profile / series-config.yaml on disk)

## Async-safety note (S1 bypass)

This invocation originates from within the orchestrator pipeline (`orchestrate_book.py`). The visible `orchestrate_book.py` process is THIS challenger's parent, not a concurrent independent run; S1 is bypassed for this pass per the invocation contract. All other gates ran normally.

## Auto-fixes applied (iteration-by-iteration)

None. No in-allowlist deterministic finding remained on entry:

- **A1 terse Quran citations — already resolved on disk.** A prior fixer pass normalized ch02b:23 `(Quran 13:7)` → `(chapter 13, verse 7)` and ch02b:59 `(Quran 43:32)` → `(chapter 43, verse 32)`. This pass re-verified both blockquotes now carry the canonical `(chapter N, verse M)` form; all four Quran references (13:7, 16:71, 17:70, 43:32) are TTS-safe. A1 is CLEAN.
- **Em-dashes (86 in the chapter) retained.** The authoritative build gate (`build_episode_txt.py`) does not reject em-dashes, and all eight chapters (71–96 em-dashes each) shipped SHIP-WITH-CAUTION carrying the same house style. Mechanically comma-replacing 86 authored em-dashes would damage the prose; B5 auto-fix not applied, consistent with the converged siblings.
- **N6 (Arabic script) N/A for this book.** No `_system/glossary.yml` exists; all eight chapters carry zero Arabic script and shipped SHIP-WITH-CAUTION. The book operates under F20 audio-label doctrine (English labels, no Arabic script or transliteration in audio). N6's glossary-driven Arabic injection has no source to draw from here.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### CS8 / P8 — book-scope doctrinal-content overlap involving ch02b
- **Files:** content/Islamic/degrees-of-excellence/chapters/ch02b-the-theory-of-degrees-of-excellence-explained.txt and, respectively, chapters/ch04b-degrees-of-excellence-the-peak-of-every-kind.txt, chapters/ch03a-the-imamate-pole-and-foundation-of-religion.txt, chapters/ch08f-the-virtues-of-ali-the-imam-who-mirrors-god.txt
- **Context:** `check_chapter_set.py` P8 reports ch02b sharing distinct 12-word concept passages with three siblings: 15 passages with ch04b (the "degrees of excellence" ladder — heat → sun → gold → ruby-that-will-not-burn → wheat/date palm → man-as-pinnacle), 9 with ch03a (the imamate-as-pole framing), 8 with ch08f. Sample: "so that when al naysaburi says the human race must have its…".
- **Note:** This is a pre-existing chapter-SET design property. All three counterpart chapters already shipped SHIP-WITH-CAUTION (commits b7429631, e52bf28a and the ch03a run) with the overlap present. Recorded at its true CS8 severity (P1), not silently downgraded. Resolution is a set-level authoring decision — trim the ladder walk-through so each episode owns its own beat. Never auto-stripped; ch03a/ch04b/ch08f are outside this per-chapter pass's edit scope.

### P2 (advisory — accepted whole-book TTS-doctrine baseline, documented book-wide rationale)

Identical in kind to the build-time FLAG items that every converged sibling recorded as advisory to ship SHIP-WITH-CAUTION with P0=0. Applied transparently and consistently, not as a silent per-chapter downgrade.

- **R-NO-ARABIC-TRANSLITERATION (chapter):** `al-Mahdi`, `al-Naysaburi` — F20 audio-label doctrine. The author is deliberately named once by design (framing Name-discipline block: "al-Naysaburi → the author, named once in the welcome"); the framing steers the hosts to say "the author" thereafter.
  - File: content/Islamic/degrees-of-excellence/chapters/ch02b-the-theory-of-degrees-of-excellence-explained.txt
- **R-NO-ARABIC-TRANSLITERATION (framing):** `al-Naysaburi` — same doctrine; the framing names the author once in the welcome directive.
  - File: .../episode-drafts/EP02-the-theory-of-degrees-of-excellence-explained/00-framing.md
- **F25-APPARATUS-TABLE (99-show-notes):** no `## Name and Title Preservation Table` section — matches every sibling's show-notes; a book-wide gap, not EP02-specific. 99-show-notes.md is outside this agent's edit scope (Section 8).
  - File: .../episode-drafts/EP02-the-theory-of-degrees-of-excellence-explained/99-show-notes.md
- **CS6 / P6 cross-book bleed (other chapters, not EP02):** `al-Sijistani`, `al-Hakim bi-Amr Allah`, `al-Kirmani`, `Hamid al-Din` flagged against kitab-al-riyad's mangle-map in ch01a and ch08f. Genuine historical Ismaili figures; false-positive-prone; human review. Not present in this chapter.

## Clean

- **A (authenticity):** A1 Quran citations all plain-English `(chapter N, verse M)` (13:7, 16:71, 17:70, 43:32). Wisdom/hadith blockquotes speaker-attributed ("the Prophet", "the Father of Imams") with no bibliographic reference-tail clutter (I5 clean). No `[VERIFY CITATION]` / `[CONTEXT NEEDED]` markers (A2/D5).
- **T (doctrinal):** T1–T5 return empty. No mis-attribution, no imam-lineage error, no forbidden naming pairing. The chapter correctly uses "the Father of Imams" and never pairs a leadership title with the personal name; "Ali b. Abi Talib" appears only in the cycle-pair list, never as "Imam Ali".
- **U (scholarly-conversation):** no AI-cliché, no faux-profundity opener (the "Suppose, for a moment…" hook is a thought-experiment, not a banned rhetorical-question opener), no deep-dive self-reference.
- **Q (host parity):** deep_dive contract valid; John (male, scholar) = Host A, Hannah (female, seeker) = Host B — consistent across EP01/02/04/05/07 (Q1–Q4 clean).
- **G (Extract-mode contract):** G1 present, G2 required-fields + enums valid (angle=faithful_exposition, adaptation_mode=faithful, episode_format=deep_dive, debate=null, slug matches), G3 `lint_contract_meta_prose` CLEAN.
- **B (meta-prose / literalness):** build-gate `validate_chapter` passed exit 0; no meta-prose tells, no cross-episode references, no file-length self-references, no translator-apparatus prefixes.
- **C/N/O:** N1 (inline phonetic parens) none; O1 (honorific repetition) none; no filler tells (E4).
- **Framing H/I/K/M/N4:** the compact hand-authored framing covers welcome + one-sentence preview (H1/H2), name discipline (J), say-ONCE pronunciation (N2/N3), forbidden-vocabulary DENY (M1/M2), close-on-question landing (H3), and the no-read-aloud guard (N4) — matching the converged sibling framings' terse style. No canonical-block insertion applied (would diverge from the book's converged terse style and the authored "no invented analogies" constraint).

## Health metrics

| Chapter | Words | Framing words | Quran cites | Terse cites | Honorific repeats | Inline phonetics | Arabic script |
|---|---|---|---|---|---|---|---|
| ch02b | 5,948 | 751 | 4 (all plain-English) | 0 | 0 | 0 | 0 (F20 audio-label doctrine) |

Build gate: `build_episode_txt.py` EP02 exit 0 (episode CUSTOMIZE-PROMPT txt emitted, 751 words). Chapter word count 5,948 is above the E1 extended soft band but accepted book-wide (all eight chapters 5,794–6,629 words; build gate passes).

## Convergence

Single pass. Zero auto-fixes available on entry (A1 already resolved; em-dashes and Arabic-label baseline are accepted book doctrine, not fixable here). Findings stable: P0=0, P1=1 (CS8 book-scope overlap), P2=4. A second iteration would be byte-identical → intelligent break. Verdict SHIP-WITH-CAUTION, consistent with all seven converged siblings.
