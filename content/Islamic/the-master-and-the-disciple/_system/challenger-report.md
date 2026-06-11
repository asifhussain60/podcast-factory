# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-06-10 (challenger v2.5, re-verified)
**Scope:** per-chapter purifying-possessions-and-parting (EP11)
**Iterations:** 2 (of 5 max — intelligent break on steady state)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly (resolved from _system/series-config.yaml)

## Auto-fixes applied

None this run. Em-dash usage in chapter prose (21 occurrences) matches the established style across all prior shipped chapters of this book (ch09b: 12, ch10c: 15) — treated as book-convention prose, not stripped. The build script's hard gate (`build_episode_txt.py --check`) accepted the chapter at 2,688 words and the framing at 765 words without P0 violation.

## Findings requiring author resolution

### P0 (blocks ship)

None. Doctrinal gate clean across chapter + framing + show-notes (0 T-findings). No HTML comments, no inline phonetic parens, no forbidden honorific repetition expansions, no abbreviated work titles, no modernization tells, no surprise-noise tells, no cross-episode references, no meta-prose tells, no fabricated atom risks.

### P1 (ship-with-caution)

#### R-NAMEDISCIPLINE — name discipline section lacks rotation set
- **File:** _system/episode-drafts/EP11-purifying-possessions-and-parting/00-framing.md (Stable role-labels section, lines 8–13)
- **Context:** The framing intentionally pins single labels ("the scholar", "the disciple", "the elder Master") with explicit `Never rotate` discipline. The validator expects a 3+ alias rotation set.
- **Recommendation:** Accept as a deliberate book-wide design — the role labels are stable by author choice across all 14 chapters; rotation would break the recurring-thesis steering. No fix needed unless the book-wide convention is reversed.

#### R-DRAMATIC-ARC — three-part focus is 3 beats not 6
- **File:** _system/episode-drafts/EP11-purifying-possessions-and-parting/00-framing.md (Three-part focus section, lines 26–29)
- **Context:** The Three-part focus declares three beats (rule + surprise; refusal + redirection; journey begins) and the validator wants 6. This is the closing episode of the scholar/disciple dialogue — a dialogue closure, not a tension arc.
- **Recommendation:** Authoring decision. The 3-beat shape mirrors the chapter's natural movement (rule → refusal → parting). Restructuring to 6 beats would force artificial subdivision.

#### R-HONORIFIC-BOTH-BOUNDS — "peace be upon him" appears 0× in framing
- **File:** _system/episode-drafts/EP11-purifying-possessions-and-parting/00-framing.md (Name discipline section, line 16)
- **Context:** The validator expects exactly one "peace be upon him" for first mention of the Commander of the Faithful. He is not mentioned in this episode — the dialogue does not reference the Father of Imams here, only the Prophet (handled with the full "peace and blessings of Allah be upon him and his family" on first mention).
- **Recommendation:** Validator false-positive for this chapter. The honorific bound applies when the figure is mentioned; he is not. No fix needed.

#### F25-APPARATUS-TABLE — missing "Name and Title Preservation Table" in 99-show-notes
- **File:** _system/episode-drafts/EP11-purifying-possessions-and-parting/99-show-notes.md
- **Context:** Show-notes lacks the F25 apparatus crosswalk (preserved Arabic / transliterations + audio-label crosswalk). The show-notes file is not part of the NotebookLM upload pair (chapter + customize prompt) — it is published-library apparatus.
- **Recommendation:** Add the apparatus table to 99-show-notes for archival completeness; does not affect audio render. Authoring decision.

### P2 (advisory)

#### B5 — em-dashes in chapter prose (21 occurrences)
- **File:** chapters/ch11d-purifying-possessions-and-parting.txt
- **Context:** Em-dashes are the established style across this book (ch09b: 12, ch10c: 15). NotebookLM TTS treats them as natural pauses for this register. Not auto-stripped per book-convention override.

## Health metrics

| Chapter | Words | Framing words | Doctrinal P0 | Build P0 | P1 count |
|---|---|---|---|---|---|
| ch11d-purifying-possessions-and-parting | 2,688 | 765 | 0 | 0 | 4 |

Both files in band: chapter 2,688 ∈ [1,800, 2,800] (default_deep_dive); framing 765 ∈ [200, 2,000].

## Convergence trace

- iter 1: 0 P0, 4 P1, 1 P2; auto_fixes=0
- iter 2: identical (intelligent break — no new auto-fixes, identical P0/P1 counts)

Stop reason: steady state on iteration 2.

> Fixer note (2026-06-10): All 4 P1s require author judgment and cannot be auto-fixed within allowed scope — R-NAMEDISCIPLINE / R-DRAMATIC-ARC / R-HONORIFIC-BOTH-BOUNDS are deliberate book-wide design choices or validator false-positives per the report's own recommendations; F25-APPARATUS-TABLE targets `99-show-notes.md`, which is outside the fixer-allowed edit set (chapter `.txt` + `00-framing.md` only). No edits applied.
