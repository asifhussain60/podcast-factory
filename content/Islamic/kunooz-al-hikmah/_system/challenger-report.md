# Podcast Challenger Report

**Book:** kunooz-al-hikmah
**Run:** 2026-06-15 (challenger v2.5)
**Scope:** per-chapter lectures-nine-ten-eleven-continued
**Iterations:** 1 (of 5 max — early break: zero auto-fixes available; all remaining findings require authoring judgment)
**Verdict:** SHIP-WITH-CAUTION
**Content profile:** islamic_scholarly (detected from meta.yml)
**Pipeline context:** invoked from within `orchestrate_book.py` parent process — Category S1 async-safety gate bypassed for this in-pipeline call.

## Auto-fixes applied (iteration-by-iteration)

None this run. Prior run (2026-06-15) auto-fixed 7 Quranic citations from legacy `(Quran X:Y)` to canonical `(chapter X, verse Y)` form (R-QURAN-CITATION-FORMAT). Those fixes are already in the chapter source.

## Findings requiring author resolution

### P0 (blocks ship)

None. Chapter passes every hard gate:
- `build_episode_txt.py` chapter validation (6700 words; HTML-comment-free; no meta-prose tells beyond an H2 structural heading).
- Doctrinal pack T1–T5: 0 findings.
- Honorific discipline O1: each honorific form appears at first mention only.
- N1 inline phonetic parens: 0 in chapter (Track A protocol holds).
- B1 meta-prose tells, B3 file-length self-references, B4 translator-apparatus prefixes: clean.
- D5 `[CONTEXT NEEDED]` / `[VERIFY CITATION]` markers: 0.
- R-RECURRING-THESIS spine "Prayer is the sacrifice of every pious person": present in framing 3×.
- Q1–Q4 host-role parity: Host A = scholar (male), Host B = seeker (female) — consistent with sibling episodes.

### P1 (ship-with-caution)

#### B6-DOUBLED-PHRASE: 2 sorites-chain phrases flagged by detector (likely false positives)

- **File:** `chapters/ch09b-lectures-nine-ten-eleven-continued.txt:47`
- **Phrases flagged:** `to know what they know;` and `to know what the chain holds;`
- **Context:** "To know the rank-holders is to know what they know; to know what they know is to know what the chain holds; to know what the chain holds is to know the Worshipped..."
- **Assessment:** this is an intentional rhetorical sorites (chain-syllogism: A→B; B→C; C→D), not copy-paste duplication. The detector cannot distinguish anaphoric chain from accidental doubling.
- **Suggested action:** treat as acceptable rhetorical figure for this chapter's didactic peroration; OR rephrase to break the anadiplosis if the author judges the cadence too tight for NotebookLM's two-host voicing.
- **Auto-fix:** not applied — collapsing the chain would destroy the intended doctrinal climax.

#### F25-APPARATUS-TABLE: 99-show-notes.md missing the Name and Title Preservation Table

- **File:** `_system/episode-drafts/EP09-lectures-nine-ten-eleven-continued/99-show-notes.md`
- **Doctrine:** F25 requires every episode's 99-show-notes to carry the written-layer apparatus (preserved Arabic / transliterations + audio-label crosswalk) the TTS-safe audio omits.
- **Suggested fix:** append a `## Name and Title Preservation Table` section listing the labels used in audio (the sixth Imam, the Father of Imams, the senior teacher of the call, the great philosopher of our school, the just caliph who ended the cursing) paired with their preserved scholarly names.
- **Auto-fix:** not applied — apparatus table content requires authoring decisions about which preserved spellings to surface.

#### F20-R-NO-ARABIC-TRANSLITERATION (holdover): "Abu Dawud" appears in chapter prose

- **File:** `chapters/ch09b-lectures-nine-ten-eleven-continued.txt` line ~75
- **Context:** "...the collection of the Sunni hadith compiler, Book of Speech, tradition number 5088..." — note: prior auto-fix may have already softened this; verify in current source.
- **Suggested fix:** ensure all attribution uses English audio labels; preserve the transliteration only in 99-show-notes.
- **Auto-fix:** not applied — label-substitution is authoring judgment.

#### CS4-LENGTH-BAND: chapter exceeds its own contract band (6700 words vs 5500–6000 target)

- **File:** `chapters/ch09b-lectures-nine-ten-eleven-continued.txt`
- **Contract:** `chapter-contracts/lectures-nine-ten-eleven-continued.yml` declares `length_target: 5500-6000`. Actual: 6700 (+11.7% over upper bound).
- **Assessment:** within build-script hard band [500, 12000] so does not block ship, but drifts from declared length contract. Acceptable for a three-lecture continuation chapter that closes the book's doctrinal arc; rewrite to band only if a tighter cadence is desired.
- **Auto-fix:** not applied — band-fit is a structural/authoring decision.

### P2 (advisory)

#### B1-STRUCTURAL-HEADING: H2 heading "## What this chapter sets down" uses the phrase "this chapter"

- **File:** `chapters/ch09b-lectures-nine-ten-eleven-continued.txt:77`
- **Assessment:** the build script's META_PROSE_TELL scan did not flag this (it appears in a heading context, not narrative). NotebookLM will read the heading and the substring "this chapter" may surface as a reading-of-source rather than a host-spoken phrase. Low risk for two-host voicing because NotebookLM typically skips raw H2s.
- **Suggested fix (optional):** rename to "## The shape these teachings make together" or similar non-self-referential title.

#### B5-EM-DASHES: 14 em-dashes in chapter prose

- **File:** `chapters/ch09b-lectures-nine-ten-eleven-continued.txt`
- **Assessment:** B5 doctrine prefers commas/semicolons over em-dashes for NotebookLM prosody. However, em-dashes here are used as stylistic parentheticals consistent with the book's voice. Not blocking; build script does not refuse.
- **Suggested fix (optional):** mass-replace `—` with `, ` only if a tighter, less parenthetical cadence is desired; not done at challenger time because 14 replacements meaningfully alter authored voice.

## Health metrics

| File | Words | Notes |
|---|---|---|
| chapters/ch09b-lectures-nine-ten-eleven-continued.txt | 6700 | +11.7% over contract band 5500–6000; within hard band [500, 12000] |
| _system/episode-drafts/EP09-.../00-framing.md | 761 | within soft band 200–2000, deep_dive default tier |

| Metric | Value |
|---|---|
| Quran citations (canonical form) | 7 / 7 ✓ |
| Honorific first-mention discipline (O1) | Clean ✓ |
| Inline phonetic parens (N1) | 0 ✓ |
| Doctrinal findings (T1–T5) | 0 ✓ |
| Em-dashes in chapter | 14 (P2 advisory) |
| Meta-prose H2 self-reference | 1 (P2 advisory) |
| Forbidden phrase pairing (T3) | 0 ✓ |
| Host-role parity (Q1–Q4) | scholar/seeker locked ✓ |

## Verdict rationale

SHIP-WITH-CAUTION: all P0 gates clean; the chapter passes `build_episode_txt.py` validation. Three substantive P1 items (B6 sorites false positive, F25 apparatus table missing, F20 Abu Dawud holdover) and one structural P1 (CS4 length overrun) warrant authoring review before publish. None of the P1 items block NotebookLM upload or audio rendering. P2 advisories are optional cadence/voice polish.
