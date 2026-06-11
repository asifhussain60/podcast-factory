# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-06-11 (challenger v2.5)
**Scope:** per-chapter union-of-inner-and-outer
**Iterations:** 2 (of 5 max — intelligent break: no new auto-fixes after iter 1)
**Verdict:** SHIP-WITH-CAUTION

## Auto-fixes applied

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | B5 | chapters/ch10c-union-of-inner-and-outer.txt | Replaced 36 em-dash instances (` — `) with `, ` |

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### R-NAMEDISCIPLINE: Name discipline section lacks rotation set with 3+ aliases
- **File:** _system/episode-drafts/EP10-union-of-inner-and-outer/00-framing.md
- **Context:** Name discipline lists single English labels per character (the scholar, the disciple, the Father of Imams) but no `Rotation: a / b / c` or `→ a / b / c` line with 3+ aliases. Build-script flag.
- **Suggested fix:** Add a rotation line under Name discipline, e.g. `the scholar → the master / the teacher / the scholar`; `the disciple → the seeker / the student / the disciple`. Authoring choice — pick aliases consistent with prior episodes in this book.

#### F25-APPARATUS-TABLE: 99-show-notes.md missing Name and Title Preservation Table
- **File:** _system/episode-drafts/EP10-union-of-inner-and-outer/99-show-notes.md
- **Context:** F25 doctrine requires every episode's show-notes to carry the written-layer apparatus (preserved Arabic / transliterations + audio-label crosswalk) the TTS-safe audio omits. No `## Name and Title Preservation Table` heading found.
- **Suggested fix:** Append the apparatus table listing every transliteration in the chapter (fasiq, fisq, kafir, mu'min, shari'a, al-fikr, dhikr Allah, al-sunna, zakat al-abdan, la hawla wa la quwwata illa billah) with their Arabic-script form and the spoken audio label.

### P2 (advisory)

None.

## Health metrics

| Chapter | Words | Em-dashes (post-fix) | Honorifics expanded | Modernize/surprise tells |
|---|---|---|---|---|
| ch10c-union-of-inner-and-outer | 2500 | 0 | 0 (chapter) | 0 |

| Framing | Words | DENY-modernize block | DENY-surprise block | No-read-aloud guard |
|---|---|---|---|---|
| EP10-union-of-inner-and-outer | 755 | present | present | present |

## Notes

- Doctrinal pack (Category T): chapter passes `_doctrinal.py` cleanly. No forbidden naming-convention phrases; Father of Imams + thirsting-woman narrative correctly attributed.
- Build script (`build_episode_txt.py --check`) exits clean. No P0 gates fire.
- Honorific discipline (O1): chapter contains zero PBUH/SAW/RA expansions; the only honorific expansions are inside the framing's Name discipline block (first-mention-only as designed).
- Phonetic discipline (N1/N2): chapter contains zero inline phonetic parens; framing's `## Pronunciation` block uses the imperative `- term: gloss` form per book convention.
- Word-count band E1: chapter 2500 (within default deep-dive 1800–2800); framing 755 (within default soft band 200–2000).
