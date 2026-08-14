> Template from: Betsy Beyer, Chris Jones, Jennifer Petoff, and Niall Richard Murphy. [“Site Reliability Engineering.”](https://landing.google.com/sre/book/chapters/postmortem.html).

# A chapter's Composer edit and three images disappeared from Surah Al-Fateha (incident #2026-08-14-01)

### Date
2026-08-14

### Authors
Claude Sonnet 5 (session working on the quote-card merge feature)

### Status
Open — root cause not confirmed. This document records what was ruled out, what the
timeline shows, and the live hypothesis, rather than asserting a cause that isn't proven.

### Summary
While verifying a new quote-card feature on `content/Sessions/surah-al-fateha`, a
`git status` check (part of this session's own end-of-work review, not triggered by any
specific suspicion) showed `book/book.md` and `_system/composer-edits.json` as modified,
with no action in this session's own record that should have touched either file. The
diff showed one chapter's entire stored Composer edit — including three real image
references (`images/103/eca60cad-…`, `1b30e423-…`, `5a272c60-…`, all present on disk) —
removed from `composer-edits.json`, and the corresponding section of `book.md` rewritten
without those images. Caught before being called "done," reverted with
`git checkout -- book.md composer-edits.json`. No content was actually lost.

### Impact
None that reached a reader or a commit — the working tree was dirty, not the repo. Cost:
the time to detect it, plus this investigation. Confirmed the images and the edit are
back on disk exactly as committed.

### Root Causes
**Not confirmed.** Two candidate mechanisms were investigated and ruled OUT:

1. **This session's own script-based writes.** Every write this session made to
   `_system/quote-kind.json` and `_system/quote-groups.json` went through
   `writeQuoteKind`/`writeQuoteGroup` in `plan-dashboard/scripts/lib/quote-kind.mjs` /
   `quote-groups.mjs`, both read directly — neither function touches `book.md` or
   `composer-edits.json` in any way.
2. **The "Generate PDF" button**, which this session did click on this book. Traced
   the full call path: `book-composer.ts`'s click handler → `POST
   /api/studio/generate-book-pdf` → `build_book_pdf.py`, which spawns a Node render
   script and, per its own docstring, "book.md is never mutated." Read the function
   body (`build_book`, `_pick_book_md`) directly — no call to `apply_composer_edits`,
   `compose_book_v2`, or anything else that writes `book.md` or the composer-edits
   sidecar. This mechanism does not fit.
3. **`recordComposerEdit`** (`composer-edits.ts`), the normal autosave path — checked
   because it's the only writer of that sidecar found by a repo-wide grep. It always
   filters out the old entry for a chapter and pushes a fresh one; it cannot produce a
   bare deletion with nothing pushed back. Doesn't fit the observed diff shape either.

**Live, unconfirmed hypothesis:** another Claude session was concurrently active on
this same repo and branch throughout this work — confirmed via `git status` showing
unrelated, substantial changes to `scripts/podcast/intelligence/translate_kashkole.py`
(247 insertions) and `content/knowledge-base/mirror.db` (grew ~1.5MB) that this session
never touched, plus an untracked `_workspace/plan/kashkole-binder-first-translation-corpus-plan.md`.
This repo's own CLAUDE.md already documents a near-identical incident on 2026-08-11
("Two [sessions] did... and both wrote `podcast-factory.css` and `book.md`... a parity
test failed mid-write") under the standing rule "Never run two Claude sessions on this
branch at once." Whether that other session (or some other process) specifically wrote
to `content/Sessions/surah-al-fateha` is not confirmed — its visible diff was in
unrelated files — but it is the only candidate left standing after ruling out this
session's own actions.

### Trigger
Unknown. See Timeline — the mutation's timestamp sits closer to unrelated activity in
this session (an unrelated cleanup edit two minutes earlier) than to the Generate-PDF
click five minutes earlier, which argues against Generate PDF as the trigger despite
that being the first hypothesis reached for.

### Resolution
`git checkout -- content/Sessions/surah-al-fateha/book/book.md
content/Sessions/surah-al-fateha/_system/composer-edits.json`. Verified afterward: all
three image references are back in `book.md`, and the stored edit is back in
`composer-edits.json`. The regenerated PDF that had been produced from the
briefly-damaged content was NOT redistributed — it was left stale on disk with an
explicit note to regenerate it after this review, rather than silently treated as
current.

### Detection
Not a monitor, not a test — a plain `git status` read as a matter of course before
calling a multi-file session's work finished. This is worth naming as a practice:
nothing in this repo's automated gates would have caught a working-tree mutation that
was reverted before commit.

## Action Items

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Determine what the concurrent session (or process) was doing between ~11:12 and ~11:15 AM EST on 2026-08-14, specifically whether it touched `content/Sessions/surah-al-fateha` | Asif | Open |
| 2 | Consider a session-start lock/advisory check for this repo (a `.claude-session-lock` or similar) so a second session gets a loud warning rather than silent collision, per the standing "never run two at once" rule | Asif | Open |
| 3 | If action 1 identifies the real mechanism, replace this document's "not confirmed" root cause with the real one and close the incident | whoever finds it | Open |

## Lessons Learned

### What went well
- The damage was caught by a routine `git status` check before declaring work done,
  not by luck or a later discovery.
- Reverting was clean and complete — `git checkout` on the two specific files, verified
  by grepping for the restored image references afterward.
- The stale PDF was not silently presented as current; it was flagged for regeneration.

### What went wrong
- This session initially wrote up the incident assuming "Generate PDF" was the cause
  without first tracing the actual code path — a plausible-sounding but unverified
  claim. The timeline built afterward argues against that specific mechanism. Naming a
  cause before reading the code it implicates is exactly the kind of claim this repo's
  own conventions ask to be grounded in inspection first.
- No log from the concurrent session (or whatever process this was) is available to this
  session, so the investigation hit a hard wall: every mechanism internal to what this
  session could see was ruled out, and what's left is unprovable from here.

### Where we got lucky
- The images were never actually deleted from disk — only their *references* in
  `book.md` were dropped, so nothing was unrecoverable even before the git revert.
- Nothing was committed in the damaged state.

## Timeline
All times EST, 2026-08-14, reconstructed from file mtimes observed during this
session (the two damaged files' mtimes were overwritten by the later `git checkout`,
so they are inferred from a `find -newer` sweep run before the revert):

- **~11:07:30 AM** — `_system/book-render-checks.json` written (this session running
  the deterministic PDF-render probe).
- **~11:09:10 AM** — `book/Surah Al-Fateha.pdf` regenerated (this session's "Generate
  PDF" click completing).
- **~11:12:03 AM** — `_system/quote-groups.json` edited (this session's own cleanup of
  a stale test declaration).
- **~11:12:41 AM** — `_system/quote-kind.json` edited (same cleanup, other file).
- **~11:14:43 AM** — `book/book.md` AND `_system/composer-edits.json` BOTH change —
  the incident. Two minutes after this session's own cleanup edits, five minutes after
  Generate PDF finished. This gap is why Generate PDF was reconsidered as the trigger.
- **later, exact time not logged** — `git status` (part of this session's own final
  review) surfaces the two files as modified; diff read; reverted immediately.

## Supporting information
- `plan-dashboard/src/pages/api/studio/generate-book-pdf.ts` — the Generate PDF route,
  confirmed to spawn only `build_book_pdf.py --json`.
- `scripts/podcast/build_book_pdf.py` (`build_book`, `_pick_book_md`) — confirmed no
  write to `book.md` or `composer-edits.json` anywhere in the render path.
- `plan-dashboard/src/lib/reader/composer-edits.ts` (`recordComposerEdit`) — the only
  other writer of the sidecar found by grep; always replaces, never bare-deletes.
- CLAUDE.md, "Never run two Claude sessions on this branch at once (CRITICAL)" — the
  standing rule this incident's live hypothesis would be another instance of.
