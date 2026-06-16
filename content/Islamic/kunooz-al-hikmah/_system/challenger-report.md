# Podcast Challenger Report

**Book:** kunooz-al-hikmah
**Run:** 2026-06-15 (challenger v2.5)
**Scope:** per-chapter particular-doctrines-drawn-out
**Iterations:** 1 (of 5 max — early-break: zero auto-fixes, no new findings vs prior pass)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  ← detected from meta.yml (series-config absent; default applied)

## Auto-fixes applied

None. The chapter and framing are clean on every deterministic auto-fix detector — no repeated honorific expansions, no inline phonetic parens, no abbreviated work titles, no meta-prose tells, no cross-episode references, no banned formal transitions, no forbidden naming pairings.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### R-NAMEDISCIPLINE: Name discipline block has no rotation set
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP12-particular-doctrines-drawn-out/00-framing.md
- **Context:** The `## Name discipline` block lists alias rules but does not provide a 3+ alias rotation set (`Rotation: a / b / c` or `→ a / b / c`).
- **Status:** Systemic — same pattern across every shipped EP in this book. Authoring decision; not chapter-specific.

#### R-DRAMATIC-ARC: 3-beat structure rather than 6-beat
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP12-particular-doctrines-drawn-out/00-framing.md
- **Context:** `## Three-part focus` carries 3 beats; the R-DRAMATIC-ARC default expects 6 (crisis / failed answer / pivot / stakes).
- **Status:** Systemic — every shipped EP in this book uses the 3-beat shape consistent with the author's "gathering, not advance" exegetical mode.

#### F25-APPARATUS-TABLE: 99-show-notes.md missing Name and Title Preservation Table
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP12-particular-doctrines-drawn-out/99-show-notes.md
- **Context:** The written-layer apparatus table (preserved Arabic / transliterations + audio-label crosswalk) is absent.
- **Status:** Systemic across this book; 99-show-notes is published-library apparatus, not consumed by NotebookLM audio. Does not affect the audio episode.

### P2 (advisory)

None.

## Health metrics

| File | Words | Notes |
|---|---|---|
| chapters/ch12-particular-doctrines-drawn-out.txt | 5,982 | Within contract.length_target 5500–6000 |
| episode-drafts/EP12-particular-doctrines-drawn-out/00-framing.md | 691 | Within framing soft band |

| Check family | Result |
|---|---|
| Doctrinal (T1–T5) | 0 findings on chapter; 0 findings on framing |
| Honorifics (O1) | No repeated expansions |
| Abbreviations (O2) | None |
| Inline phonetic parens (N1) | None |
| Meta-prose tells (B1–B6) | None |
| Quran citation format (R-QURAN-CITATION-FORMAT) | Plain-English form (chapter N, verse M) throughout |
| Forbidden naming pairings (T3) | None — uses "the Father of Imams" / "the Commander of the Faithful" |
| Modernization deny (M1/M2) | DENY blocks present in framing |
| Contract validation (G1–G6) | Contract present, slug parity OK, length_target honored |
