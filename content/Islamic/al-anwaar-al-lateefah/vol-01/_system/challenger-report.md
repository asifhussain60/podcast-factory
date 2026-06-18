# Podcast Challenger Report

**Book:** al-anwaar-al-lateefah/vol-01
**Run:** 2026-06-18 (challenger v2.5)
**Scope:** per-chapter `naming-the-unnameable` (chapter `ch03c-naming-the-unnameable.txt` + framing `EP03-naming-the-unnameable/00-framing.md`)
**content_profile:** islamic_scholarly (default — no series-config.yaml on disk)
**Iterations:** 2 (of 5 max)
**Verdict:** SHIP-WITH-CAUTION

## Build gate (authoritative — `build_episode_txt.py`)

Exit 0. Chapter validated (3385 words, uploaded as-is). Episode customize-prompt emitted (725 words). Two P1 flags, both systemic across the whole book; neither blocks ship.

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | (none) | — | The on-disk chapter already carried the canonical Quran citation form (`chapter N, verse M`) and contained no cross-episode references; no mechanical auto-fix was required. |

Note: an exploratory `extract_chapter.py --force` during iteration 1 regenerated the bundle from the contract and transiently overwrote the hand-authored framing with a generic stub. The authored framing (Opening directive with welcome + verbatim spine, Name discipline, Pronunciation block, six-beat Three-part focus, Host dynamic, Tone constraints, Landing, Do-not block) was restored verbatim before the report was written. Final on-disk framing == authored framing (725 words). The chapter file's git-tracked baseline is stale (`Quran 3:18 (Al Imran)` form, "the previous lesson" cross-episode phrasing); the working-tree chapter is the corrected canonical version and is what ships.

## Findings requiring author resolution

### P0 (blocks ship)
None.

### P1 (ship-with-caution)

#### F20 / R-NO-ARABIC-TRANSLITERATION: 7 Arabic transliterations in chapter SOURCE
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch03c-naming-the-unnameable.txt (lines 3, 27, 53, 85)
- **Context:** all 7 are proper-name fragments inside scholarly citation apparatus, not freestanding doctrinal terms: the book title `Al-Anwaar al-Lateefah` (l.3); `Nahj al-Balagha (compiled by al-Sharif al-Radi)` (l.27); `Hibatullah ibn Musa al-Shirazi` and `Mawlana Sayyidna Mu'ayyad al-Din` (l.53); `Lady Fatima al-Zahra` (l.85).
- **Severity rationale:** P1 advisory (TTS-safety). The framing already directs the hosts to cite the Quran by verse content and to use English audio labels for figures (Name discipline block), which mitigates the read-aloud risk. This pattern is systemic — every chapter in the book carries 3–10 such fragments (this chapter has the second-fewest).
- **Suggested fix (author decision — NOT auto-fixed):** these sit inside citations where the transliteration is the scholarly reference; either accept as written-layer apparatus or substitute English audio labels per F20. Resolve book-wide, not per-chapter.

#### F25-APPARATUS-TABLE: 99-show-notes.md lacks the Name and Title Preservation Table
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/_system/episode-drafts/EP03-naming-the-unnameable/99-show-notes.md
- **Context:** no `## Name and Title Preservation Table` section. The show-notes carry `## Related episodes` and `## References` only.
- **Severity rationale:** P1 advisory. Show-notes are written-layer apparatus and do NOT flow to NotebookLM audio. Systemic — applies to all episodes' show-notes.
- **Suggested fix:** add the F25 crosswalk table (preserved Arabic / transliterations + audio-label mapping). Best resolved by the show-notes generator book-wide.

### P2 (advisory)

#### Chapter-set P8 (within-book passage overlap)
- The book-scope chapter-set check reports `naming-the-unnameable` shares 12-word passages with sibling chapters (12 with `the-unknowable-originator-and-the-first-intellect`, 12 with `what-tawhid-really-is`, 6 with `the-refined-mukathir-house-of-allah`, 6 with `outer-and-inner-gnosis-and-the-mukathir`, 3 with `the-ladder-of-tawhid`). These are largely shared liturgical/doctrinal formulae and recurring cosmological vocabulary intrinsic to a single-source lecture series. Surfaced for author awareness; this is a book-scope finding, not specific to this chapter under per-chapter scope.

#### Chapter-set P10 (density)
- `naming-the-unnameable` has 6 concept sections vs the ≤3 target (advisory; systemic — 10 of 11 chapters exceed the target). Re-split is an authoring decision via Phase 0d.

## Health metrics

| Chapter | Words | Citations | Blockquotes | Cross-ep refs | Honorific exp. | Doctrinal (T) | Quran cite form |
|---|---|---|---|---|---|---|---|
| ch03c-naming-the-unnameable | 3385 | 5 (3 Quran + 1 Nahj + 1 Sahih Muslim) | 5 | 0 | 1 (PBUH, once) | 0 findings | canonical (chapter N, verse M) |

Category passes: A1–A6 clean (full citations, translator named, authentic sources, no cross-tradition collision); B1–B6 clean (no meta-prose, no cross-episode refs, no file-length self-ref); D4/D5 clean (no quote-stacking, no CONTEXT-NEEDED markers); E2/E3 strong (single-thread paradox arc, hook open + landed close); T1–T5 clean (0 doctrinal findings; Father of Imams named correctly, never paired leadership-title with personal name); U1/U2/U4/U3 clean. Framing: H1 welcome present, M1/M2 DENY blocks present, Q host-role parity correct (Host A male scholar / Host B female seeker), N4 no-read-aloud guard present, six-beat Three-part focus, R-RECURRING-THESIS spine present.
