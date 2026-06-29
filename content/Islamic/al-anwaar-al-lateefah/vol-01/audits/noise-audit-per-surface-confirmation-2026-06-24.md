# Noise Audit - Per-Surface Confirmation Re-Sweep

- `noise_auditor_version`: 1.0
- date: 2026-06-24
- run time: 1:24 PM EST
- book: al-anwaar-al-lateefah / vol-01
- branch: Islamic/al-anwaar-al-lateefah
- scope: AGGRESSIVE (NZ-CIRCULATION + NZ-PROVENANCE in-scope)
- taxonomy: scripts/podcast/_rules.py - R_NOISE_APPARATUS_CATEGORIES / _PROTECT / _PATTERNS
- surfaces swept: chapters/*.txt (11), episodes/*.txt (11), slide-decks/*deck*.txt + *framing*.md (22), book/book.md + book-illustrated.md (2)

## Method

Pass 1 ran the live `R_NOISE_APPARATUS_PATTERNS` plus incident-specific anchors across every formal deliverable source surface:

- `do not email`, `do not store`, `do not share`, `do not circulate`, `do not upload`, `on your computer`
- `copy ... is a sin`, `cold iron`
- `ijazat` to record, treasury deposit, recorded-for-family, twofold authority
- `transcribed/compiled/printed/scanned by`, `this edition`
- soft editorial anchors: `in this lesson we will`, `as recorded above`

Pass 2 read each candidate in context and judged it by the auditor's rule: claims about reality, God, the soul, the path, law, wilayah, imams, doctrine, or the handling of knowledge are teaching/source content and KEEP; claims about this book object's recording, authorization, circulation, storage, or production are STRIP.

## Overall Verdict

**CLEAN.** No P0, P1, or P2 NZ findings across the formal volume-one deliverable surfaces.

The fresh sweep found 17 pass-1 candidates. All 17 adjudicate KEEP:

- 14 citation lines matched `compiled by`; these are source attributions for quoted teachings from *Nahj al-Balagha* or *Ghurar al-Hikam*, not colophon apparatus for this book object.
- 3 knowledge-distribution passages matched circulation-style language; these are inner-law teachings about zakat/khums/fasting as handling knowledge, protected by the doctrine/imam/wilayah teaching rule.

The original incident strings remain absent from the formal surfaces: no do-not-email/store/share-online warning, no cold-iron punishment, no copy-is-a-sin warning, no ijazat-to-record/treasury-deposit chain, and no twofold-authority framing.

## Surface 1 - NotebookLM Upload Sources

VERDICT: CLEAN. 0 NZ findings.

- Files swept: 11 chapter files.
- Pass-1 candidates: 8.
- KEEP reasons: 7 quoted-source citations; 1 inner-law teaching about fasting, alms, khums, knowledge, and Imam al-Zaman.

The chapter-one opener remains re-derived around inherited-science epistemics, the five-fold architecture, wilayah/allegiance, lawful action, and soul-return. The former front-matter apparatus is not present.

## Surface 2 - Episode Framings

VERDICT: CLEAN. 0 NZ findings.

- Files swept: 11 episode files.
- Pass-1 candidates: 0.

Episode one is built from doctrine and listening guidance, not the prior distribution-warning spine.

## Surface 3 - Slide-Deck Bundles

VERDICT: CLEAN. 0 NZ findings.

- Files swept: 22 slide-deck and framing files.
- Pass-1 candidates: 7.
- KEEP reasons: all 7 are quoted-source citations, not production colophon for this book.

The chapter-one deck and framing contain no ijazat, treasury, do-not-circulate, computer-storage, copy-sin, or cold-iron language.

## Surface 4 - Reading Edition

VERDICT: CLEAN. 0 NZ findings.

- Files swept: book.md and book-illustrated.md.
- Pass-1 candidates: 2.
- KEEP reasons: both are the same inner-law passage about fasting as concealing knowledge from the unfit, khums as dispensing unexpectedly received knowledge, and hajj as turning toward Imam al-Zaman.

The preface and chapter-one opener no longer duplicate the original apparatus block.

## Advisory Outside Formal Source Scope

A stale diagram cache still exists under the reading-edition diagram directory. The cached files and manifest contain the removed provenance chain language (`Recorded with ijazat permission`, `Kept for family circle`, `Deposited in Daawat treasury`). The formal reading files do not reference that stale diagram, so it is not counted as a deliverable-surface NZ finding in this identify-only run.

Recommendation: when a Tier-2 cleanup is authorized, remove or regenerate the stale diagram cache so future tooling cannot accidentally re-expose the old provenance artifact.

## Counts

| Surface | Files | P0 | P1 | P2 | Pass-1 candidates | Final findings |
|---|---:|---:|---:|---:|---:|---:|
| chapters/*.txt | 11 | 0 | 0 | 0 | 8 | 0 |
| episodes/*.txt | 11 | 0 | 0 | 0 | 0 | 0 |
| slide-decks/* | 22 | 0 | 0 | 0 | 7 | 0 |
| book/book.md + book-illustrated.md | 2 | 0 | 0 | 0 | 2 | 0 |
| **Total** | **46** | **0** | **0** | **0** | **17** | **0** |

## Open Item

The outstanding NotebookLM EP01 audio regeneration remains outside this identify-only source-surface audit. The cleaned source surfaces are ready for that user action.
