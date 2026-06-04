# Podcast Challenger Report

**Book:** ayyuhal-walad
**Run:** 2026-05-31 09:30 (challenger v2.3)
**Scope:** per-book (3 chapters + 3 episode framings — canonical 3-episode set)
**Iterations:** 1 (of 5 max — intelligent break: sole auto-fix produced no new findings)
**Verdict:** SHIP-WITH-CAUTION

Canonical set confirmed: ch01/ch02/ch03 + EP01/EP02/EP03 with slugs
frame-and-the-problem-of-knowledge, the-disciplines-of-the-path,
the-guiding-shaykh-and-final-counsels. The archived 5-episode original under
_archive/ is out of scope and was ignored.

## Prior-run P0s (read-aloud apparatus) — RESOLVED

The previous run BLOCKED on 3 P0s: raw-extraction apparatus NotebookLM would
read aloud. All cleared this run, verified by direct scan over all 3 chapters:

| Prior P0 | Status |
|---|---|
| `[GHAZALI — core text]` / `[SCHOLARLY COMMENTARY]` / `[COMMENTARY]…[/COMMENTARY]` / `[NARRATOR NOTE]` markers | CLEARED — 0 found |
| Translator footnote apparatus (folio / MSS / Hammer-Purgstall) | CLEARED — 0 found |
| "Wisdom enrichment:" labels | CLEARED — 0 found |
| `*Episode N of 3 · N words*` metadata header | CLEARED — 0 found |

De-labeled enrichment prose ("A parallel counsel from the tradition notes…",
"This teaching echoes…") was correctly retained as normal paragraphs and reads
as authored prose, not apparatus.

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | B6/read-aloud-orphan | ch03-the-guiding-shaykh-and-final-counsels.txt:60 | Removed orphan "None." line — a de-labeling residue that NotebookLM would have read aloud as the word "None" (same read-aloud class as the prior P0s). Deterministic deletion; not verbatim source, not enrichment prose. |

## Findings requiring author resolution

### P0 (blocks ship)

None. (No unresolved P0 remains.)

### P1 (ship-with-caution)

None.

### P2 (advisory)

#### Q2/Q4: Title length (chapter-set, advisory)
- **Files:** chapter-contracts/frame-and-the-problem-of-knowledge.yml, chapter-contracts/the-guiding-shaykh-and-final-counsels.yml
- **Context:** Both titles are 7 words (>6-word INVARIANT-6 soft target; both under the 60-char hard cap). Acceptable as-is.

#### Q4 (band-label mismatch — reclassified P2 from checker P0)
- **File:** chapter-contracts/frame-and-the-problem-of-knowledge.yml
- **Context:** ch01 measures 3,037 words; contract carries stale `word_count: 4456` (pre-strip value) and no explicit `length_target`, so the checker defaulted to the `default_deep_dive` band (1800–2800) and flagged 3,037 as over-band P0. This is a band-LABEL mismatch, not a content/read-aloud defect: 3,037 is comfortably inside the build-script hard chapter bound [500, 5500] and inside the challenger E1 soft band (1500–4500). The agent does NOT escalate this to a shipping blocker — it is a contract-metadata staleness item. Recommended fix (authoring, not auto-fixed per Category-Q policy): update `word_count` to 3037 and add `length_target: longer` (band 2800–4500) so the label matches the post-strip content. ch02 (2,441) and ch03 (2,709) sit inside default_deep_dive cleanly.

#### Host-role label canonicalization (advisory)
- **Files:** all 3 episode framings (## Host dynamic)
- **Context:** Host A = "Curious Mind", Host B = "Patient Teacher" — consistent across all 3 episodes (parity HOLDS, no swap). "Patient Teacher" maps to the scholar pool ("teacher"); "Curious Mind" is a seeker-equivalent but not a literal `_rules.py` HOST_B_ROLES_SEEKER token. No P0 parity violation (assignments are stable book-wide). Optional: align labels to canonical pool tokens for tooling consistency.

#### Q4 voice/gender declaration absent (advisory)
- **Files:** all 3 episode framings
- **Context:** No explicit `notebooklm_voices` / Host-A-male / Host-B-female declaration block. NotebookLM's default pair (Hannah=female, John=male) will apply. Optional hardening: add the voice-gender pairing block so role-to-voice mapping is explicit.

## Structural / build gate

- Apparatus markers: 0 (chapters + framings).
- HTML comments: 0. Cross-episode `EP##` refs in chapter content: 0.
- Inline phonetic parens (N1): 0. Legacy passive pronunciation lists (N2): 0.
- Framing meta-prose matches at EP##:16/32 are framing DIRECTIVES ("Do not open with 'in this episode'") and steering language, not spoken chapter content — not violations.
- Em-dashes in chapters appear only in (a) `## Section N — Title` headers and (b) verbatim Ghazali/Quran source quotes; B5 prose auto-fix is NOT applied to verbatim scripture (would collide with A4 verbatim integrity). The build script does not gate on em-dashes. No blocker.
- All 3 episode framings carry: welcome clause (H1), episode-summary (H2), Do-not block with modernize-deny (M1) + surprise-deny (M2), no-read-aloud guard (N4), four named tensions (F4), conversation discipline (K1), imperative Pronunciation block (N2/N3).

## Health metrics

| Chapter | Words | Band fit | Apparatus | Orphans | Phonetic gaps |
|---|---|---|---|---|---|
| ch01 | 3,037 | over default_deep_dive label (in hard bound) | 0 | 0 | 0 |
| ch02 | 2,441 | in default_deep_dive | 0 | 0 | 0 |
| ch03 | 2,709 | in default_deep_dive | 0 | 0 | 0 |

| Episode framing | Words | Welcome | Do-not | No-read guard |
|---|---|---|---|---|
| EP01 | 1,689 | yes | yes | yes |
| EP02 | 1,873 | yes | yes | yes |
| EP03 | 1,828 | yes | yes | yes |

## Per-chapter verdict

- ch01 / EP01 — SHIP-WITH-CAUTION (P2: band-label staleness)
- ch02 / EP02 — SHIP-READY
- ch03 / EP03 — SHIP-READY (orphan "None." auto-fixed this run)
