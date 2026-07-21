# Prompt — Composer authority + honorifics

---

Continuing **podcast-factory** (`develop`) on
`content/Islamic/the-master-and-the-disciple/`. Two decisions are already made —
implement them, don't re-litigate.

**Verify in the Book Composer** (`localhost:4322/studio/<slug>/compose`), not the
PDF. It autosaves, so close that tab before any compose run.

## 1. Honorifics — expand on first use

Asif: *"I'm ok with the short honorific as long as the full form has been used the
first time."*

So: the **first** occurrence in the book prints `(عليه السلام)` in full; every
later one prints `(ع)`. Deterministic, in the pipeline, first-use scoped to the
BOOK not the chapter (it is a convention introduced once). Six `(ع)` sites exist
today with no full form preceding them. Honorific formulas are already recognised
in `_book_arabic_audit._HONORIFIC_FORMULAS` — reuse that set, don't write a second
one.

## 2. Composer authority — the determination Asif pre-approved

His intent: *"Composer is the final editor where all edits related to the pdf
generation and companion tool for Live sessions will take place."*

Taken literally, that settles the open question. **A chapter the human has edited
is not re-composed.** `compose_book_v2` should skip regenerating any chapter with
a saved Composer edit, log that it skipped and why, and spend no model time on
prose it would only discard. Three things follow:

- It removes the silent-overwrite class outright. On 2026-07-21 a rebuild
  regenerated all nine chapters and then replayed edits over eight of them — the
  fresh work was discarded after being paid for, and the book moved 111 words in
  33 minutes.
- Replay stays human-wins, which already matched the intent; it simply stops
  being a race.
- `--force` remains the escape hatch for "actually re-compose everything",
  and must warn that it will overwrite human chapters.

**Fix the conflict signal first — it is currently false.** The Composer writes
`base_fingerprint` from the LIVE `book.md` body (post-bridges, post-introduction,
`composer-edits.ts:95`), but replay compares it against the composed body BEFORE
those steps run (`_book_edits.py:196`). They can never match for any chapter
carrying a bridge or the intro, so CONFLICT fires permanently. All eight
"conflicts" reported on 2026-07-21 were probably noise. Fingerprint the same
bytes on both sides, then a real conflict means something and can be surfaced in
the Composer for the human to resolve.

Note `fingerprint` ↔ `fingerprintBody` is a named TS↔Python mirror pair in
CLAUDE.md and has **no parity test** — add one.

## 3. Remaining audit findings, ranked

Not yet fixed (a repo-surgeon sweep found 14; six are done and pushed in
`41ec913`):

- **`dedupe_seam_paragraphs` deletes paragraphs with no log, count or report**
  (`_translation_seams.py:111-146`), and runs twice per compose. A false positive
  at ratio ≥ 0.62 — a liturgical refrain, a question restated before its answer —
  is removed from the book and nothing records that it existed. Its sibling
  `duplicate_passage_findings` is deliberately report-only for this reason.
- **A corrupt edits sidecar silently discards every prior edit.**
  `composer-edits.ts:70-75` returns `{edits: []}` on a parse failure and the next
  save writes that truncated object back. Both sides write non-atomically, so a
  crash mid-write manufactures exactly the corrupt file that triggers the wipe.
  Temp-file + rename; refuse to overwrite on a parse failure.
- **A misspelled knob silently changes the product** (`_pipeline_flags.py:85-98`).
  `book_voice: fathful` falls through to the default map and a translation edition
  gets a full author re-voice with no warning. Any unrecognised value should log
  loudly or raise.
- **The introduction is injected into the first `## ` section, whatever it is**
  (`_book_frontmatter.py:182-189`). With `toc.preface.include` false that is
  Chapter 1, and a "the book's own opening" heading is manufactured mid-chapter.
- **Render reports `completed` when its own validation gate throws**
  (`book_driver.py:269-308`) — a crash in the gate is indistinguishable from a pass.
- **`_book_compose.author_phase_book_compose` is a live, superseded whole-book
  composer** reachable from its own `main()`. It writes `book/book.md` directly
  and repopulates the stale first-person `book/_chunks/book/` cache. Running the
  CLI clobbers a good compose. Delete the function + `main()`, keep the helpers
  other modules import.
- **Nothing under `plan-dashboard/src/` is tested** — `npm test` only globs
  `scripts/**/*.test.mjs`. That excludes `book-md-write.ts`, the sole writer into
  `book/book.md`, and every `src/pages/api/studio/*` route that mutates
  `content/**`.
- Smaller: `_book_voice` accepts a `force` it never uses; the fluency stage is
  missing from the Arabic stage ledger (and for faithful-voice books it is the
  *only* model pass); `_book_augment` keys blocks by heading text, so two chapters
  with the same title share one body.

## 4. Still Asif's call — do not decide these

- The **stale worktree** at `~/PROJECTS/podcast-factory-worktrees/the-master-and-the-disciple`
  holds `Islamic/the-master-and-the-disciple` on an old commit with unmerged "v2
  matrix" work. It is why the orchestrator's pre-flight refuses to run pipeline
  phases, and why book phases had to be driven directly via
  `phases.book_driver._drive_book_branch`. Repo surgery — agree the approach first.

## Constraints

- Only prose the pipeline AUTHORS may be rewritten: `book/book.md`, `chapters/`,
  `episodes/`, `slide-decks/`. NEVER OCR under `_system/source/`, the shared
  source library, `research/`, or the lecture transcripts under
  `augmentation/*/chapters/` (a sweep caught 78 of those before it was reverted;
  pinned by `tests/test_normalize_spelling_scope.py`).
- Site work follows the Cortex HTML View Quality Standard and gates through
  `html-view-challenger`. Pipeline modules are capped at 600 lines (DR-005,
  enforced pre-commit).
- Gates: `pytest scripts/podcast/tests` (1710), `cd plan-dashboard && npm test`
  (48), `npx tsc --noEmit`, `npm run lint:views`, `npm run smoke`, `ruff check`
  + `ruff format`.
- `book.md` restores from `1b750a3` (challenger-converged, publication-approved)
  plus the three deterministic passes. Recovery tag:
  `pre-rebuild/the-master-and-the-disciple-2026-07-21`.

Background: `_workspace/plan/session-handoff-2026-07-21.md`.
