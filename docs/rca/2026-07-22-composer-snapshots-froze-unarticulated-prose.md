# Composer snapshots froze un-articulated prose across 8 of 9 chapters (RCA-001)

### Date

2026-07-22 (incident window: 2026-07-19 → 2026-07-22)

### Authors

Claude (investigation + forensics), reviewed by Asif

### Status

RESOLVED 2026-07-22 — book-challenger verdict SHIP-READY after a 3-iteration
convergence on the recovered text. Open corrective actions: AI-6, AI-7
(AI-2 landed from its task session with the develop merge).

### Template

Google SRE postmortem format (Beyer/Jones/Petoff/Murphy, *Site Reliability
Engineering*), via [dastergon/postmortem-templates](https://github.com/dastergon/postmortem-templates).
Analysis pattern: blameless postmortem + 5 Whys + contributing-cause categories.

### Summary

The Master and the Disciple's reading edition shipped through every quality
gate with 8 of its 9 chapters carrying the raw, calqued base translation
instead of the articulated (fluency-adapted) prose. The articulation pass DID
run and DID produce articulated text for all 9 chapters on 2026-07-21 — and
the same compose run discarded 8 of them minutes later by replaying stale Book
Composer snapshots taken the day before, when articulation had produced
nothing. The defect was invisible to every downstream gate and was caught by
the human reader in the Composer.

### Impact

- 8/9 chapters of a publication-bound edition carried un-articulated prose
  for ~24 hours across a SHIP-READY convergence verdict, a publication review,
  and multiple content-curation sessions.
- One full articulation pass (~36K words of model output) paid for and
  discarded in the same run that produced it.
- All curation performed 2026-07-21 → 2026-07-22 (challenger fixes, annotation
  policy, name glosses) was applied to the wrong prose baseline and must be
  re-verified against the articulated text.

### Root Causes

1. **Snapshot-not-delta persistence (design).** A Composer save stores the
   entire chapter body as the durable edit. A one-word human gloss therefore
   freezes ~8,000 words of machine text as "human-authored," and the pipeline
   cannot distinguish the human's sentence from the machine's chapter.
2. **No ordering guard between articulation and curation (process).** Nothing
   prevented whole-chapter Composer saves on 2026-07-20, a day when the
   fluency report read `adapted: 0, reverted: 1, skipped: 8`. The freeze
   predates the milestone it should have depended on.
3. **Pass-level success is reported without deliverable-level survival
   (detection).** The fluency report recorded `adapted: 9` — true of what the
   pass produced, false of what the book kept. No gate compares a pass's
   output against what survives in the final artifact.
4. **The 2026-07-21 fix hardened the wrong invariant (change management).**
   "Composer-authored chapters are never regenerated" stopped the wasted
   model spend — and simultaneously made the frozen chapters permanent and
   silent. It protected staleness because it could not see staleness.

### Trigger

The unified compose of 2026-07-21 2:40 PM EST: articulation pass (all 9
chapters adapted) followed in-run by the Composer-edit replay (8 chapters
overwritten with 2026-07-20 snapshots).

### Resolution

1. Human/editorial deltas vs the frozen baseline extracted to
   `content/Islamic/the-master-and-the-disciple/_system/articulation-recovery/`
   (19 hunks across 8 chapters — includes one doctrinal fix that existed
   nowhere else).
2. Stale composer-edits archived alongside; live sidecar cleared.
3. Full re-compose. NOT cache-cheap as first planned: the chunk-cache
   freshness rule counts the gate/prompt modules as governing inputs, so the
   July 19 chunks were deliberately stale (they predate the narrative-frame
   gates) — the recovery was a full fresh base translation + articulation.
   Three launches: two were killed by a false-positive enumeration gate
   (fixed at root twice — final rule: a consecutive ascending numeric marker
   run starting above 1 is section-numbering apparatus; the second launch's
   retry had "satisfied" the gate by writing section numbers into the prose,
   caught by the live log monitor within a minute). Third launch completed:
   9/9 chapters de-calqued, 0 reverted, 0 copied-not-revoiced.
4. Punchlist re-applied to the articulated prose. The green-ears doctrinal
   fix proved unnecessary — the fresh translation renders "causes" correctly
   from source, confirming the old error was model-introduced. Name glosses
   and bridges re-applied/re-anchored by hand.
5. book-challenger iteration 1 on the recovered text: BLOCKED with 4 P0 /
   5 P1 / 6 P2 (incl. model chatter that had been snapshotted into a fresh
   Composer edit, a seam double-telling, and a book-wide naming regression
   against Asif's locked one-name ruling). All P0s/P1s + 3 P2s fixed;
   iteration 2 verification sweep run before the edition is called done.
   All six curated chapters saved as fresh Composer edits protecting the
   fixed, articulated text.

### Detection

Human. Asif read the chapters in the Composer and recognized calqued
translation ("original bad English"). Confirmed forensically: every flagged
chapter is 98–100% byte-identical to its 2026-07-20 pre-articulation
snapshot; the post-compose commit of 2026-07-21 already matched those
snapshots exactly.

## Action Items

| # | Action | Type | Status |
|---|---|---|---|
| AI-1 | Recover: re-articulate 8 frozen chapters, re-apply deltas, re-gate | mitigate | done 2026-07-22 — SHIP-READY at challenger iteration 3; 4 P0 / 7 P1 / 3 P2 found-and-fixed on the way; only advisory P2s remain (apparatus pass) |
| AI-2 | Fluency/compose honesty: report `adapted-and-kept` vs `adapted-then-overwritten`; compose warns loudly when replay discards adapted text | prevent | done 2026-07-22 — `reconcile_reports_after_replay` (`_book_pass_reports.py`) re-stamps discarded chapters after the replay, `merge_records` can no longer resurrect a stale `adapted` for an edited chapter, compose warns loudly; schema `podcast.book-fluency/v4` + `podcast.book-voice/v4` (additive: `overwritten_by_replay`, `pre_replay_status`) |
| AI-3 | Composer save guard: warn when a save would freeze a chapter whose current base never passed articulation | prevent | done 2026-07-22 — advisory banner + confirm-before-first-save in the Book Composer, driven by `lib/reader/articulation.ts` over `_system/book-fluency-report.json` |
| AI-4 | RCA practice: `docs/rca/` process + template + standing memory rule | process | done (this session) |
| AI-5 | Compose-run interference watch: heartbeat monitors the composer-edits sidecar for mid-run saves (open Composer tab autosave is a live clobber vector) | detect | done for this run (tab closed + monitored); durable fix is AI-3's save guard |
| AI-6 | Strengthen the compose prompt's no-headings instruction — 6 of 9 fresh windows drew a model-owned-heading retry (each costs a full window recompose). NOTE: prompt modules govern the chunk cache, so land this WITH a planned re-compose, never casually | prevent | open |
| AI-7 | Enumeration gate refined twice during recovery (section-numbering apparatus vs argument lists — see commits d009943, 3160738); watch one more book's compose before considering it settled | verify | open |

## Lessons Learned

### What went well

- Everything was committed; the entire failure was reconstructable from git
  history to the minute.
- The base translation chunk cache made recovery cheap — only the
  articulation windows need re-spending.
- Human deltas were small (19 hunks) and mechanically extractable.

### What went wrong

- "Human-authored" was inferred from the existence of a save, not from what
  the human actually changed.
- Four independent quality gates (challenger, publication review, render
  checks, Arabic audit) all judged the end-state against the source — none
  asks whether each pipeline stage's contribution survived to the end-state.
- A report that says a pass succeeded stays true forever, even after a later
  step in the same run reverses the work.

### Where we got lucky

- The one doctrinal correction (green ears) lived only in the frozen text;
  had recovery been attempted by naive re-compose without delta extraction,
  it would have silently reverted.
- The reader caught it before publish.

## Timeline (EST)

| When | Event |
|---|---|
| Jul 19, ~9:24 AM–10:27 AM | Base translation compose writes calqued chapter chunks (translation route) |
| Jul 20, 12:16 PM | De-calque articulation route lands; first run: 0 adapted, 1 reverted, 8 skipped — book remains calqued |
| Jul 20, 1:21–1:29 PM | Composer saves freeze 6 whole chapters as durable edits (pre-articulation bodies) |
| Jul 21, 12:17 PM, 1:52 PM | 2 more chapters frozen the same way — 8 of 9 now carry edits |
| Jul 21, 2:40 PM | Unified compose: articulation adapts all 9 chapters, then in-run replay overwrites 8 with the Jul 20 snapshots; report reads `adapted: 9` |
| Jul 21, 5:46 PM | "Composer is authoritative" rule ships — passes now skip edited chapters; freeze becomes permanent and silent |
| Jul 21–22 | Challenger convergence (SHIP-READY), annotation policy, name glosses — all curate the frozen prose |
| Jul 22, ~3:30 PM | Asif reads the Composer, reports "original bad English"; forensic diff confirms 8/9 chapters ≥98% identical to the Jul 20 snapshots |

## Supporting information

- Frozen-baseline deltas + manifest: `content/Islamic/the-master-and-the-disciple/_system/articulation-recovery/`
- Key commits: `581a512` (de-calque route, 0-adapted run), `748c126` (the
  triggering compose), `0b52991` (skip rule), `bcd7558`/`2a0c8c6` (curation on
  the frozen baseline)
- Fluency reports: `_system/book-fluency-report.json` at `581a512` (0 adapted)
  vs `748c126` (9 "adapted", 8 discarded)
