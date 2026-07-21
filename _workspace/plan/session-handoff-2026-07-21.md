# Continue: Book Composer + the-master-and-the-disciple reading edition

Paste the block below as the first message of a new session.

---

## Prompt

I'm continuing work on **podcast-factory**, branch `develop`, on the book
`content/Islamic/the-master-and-the-disciple/`. Everything below is already
committed and pushed — start by reading this file
(`_workspace/plan/session-handoff-2026-07-21.md`) and confirming the state
matches before you change anything.

**Verify in the Book Composer at `localhost:4322/studio/the-master-and-the-disciple/compose`,
not by rendering the PDF.** That is where I test. Render only if I ask, or if the
printed page itself is the subject. Note the Composer autosaves — a stale open tab
can overwrite a running pipeline, so treat "is that tab open?" as pre-flight.

### Where things stand

`book/book.md` was restored from commit `1b750a3` — the last pipeline-authored
version, already challenger-converged and publication-review APPROVED — and three
DETERMINISTIC text passes were applied on top, in this order:

1. `_translit.simplify_transliteration` — plain house transliteration. Ayn/hamza
   apostrophes are dropped BY DESIGN (Quran, duat, Bayt al-Mamur). Apostrophes
   survive only for English clitics (God's, don't), plural/name possessives
   (brothers', Moses') and o'clock.
2. `_book_inline_arabic.apply_inline_arabic` — 68 annotations of the form
   `Transliteration (عربي)`, first mention per chapter, every glyph from the
   curated `arabic_script` field in `_system/glossary.yml`. Nothing model-recalled.
3. `_american_spelling.to_american` — American spelling throughout.

All three now run inside `compose_book_v2` so a future compose reproduces them.
All 8 Book Composer edits were cleared from `_system/composer-edits.json`
deliberately — nothing from the 2026-07-21 session carries forward.

Current numbers: 36,978 words, 9 sections, 68 inline Arabic annotations, 823
Arabic runs across a 125-page PDF, zero British spellings, no apostrophe
transliterations.

### The one open thread

A `book-challenger` run was launched against this manuscript at the end of the
last session, focused on: Arabic-script accuracy across all 68 annotations,
programmatic-insertion damage (mid-sentence landings, split proper names,
annotations inside blockquotes/headings), and terminological collisions created
by the transliteration fold. **Its findings were not yet reviewed or fixed.**
Re-run it if the report is not on disk:

```
Task → book-challenger: "the-master-and-the-disciple"
```

Fix P0s first. Do not mutate `book.md` from the challenger directly — it surfaces,
you fix.

### Known issues worth picking up

- **Stale worktree blocks the orchestrator.** `~/PROJECTS/podcast-factory-worktrees/the-master-and-the-disciple`
  holds branch `Islamic/the-master-and-the-disciple` at an old commit with
  unmerged "v2 matrix" experiments. The orchestrator's pre-flight refuses to run
  pipeline phases on `develop`, so book phases had to be driven directly via
  `phases.book_driver._drive_book_branch`. Reconcile or remove that worktree
  before the next orchestrated run. This is repo surgery — agree the approach
  with me first.
- **A Composer edit replaces the WHOLE chapter body on replay** (`_book_edits.py`
  line ~188), not just the changed words. That is why 8 of 9 chapters silently
  reverted during the 2026-07-21 rebuild, discarding the fresh compose. Worth
  deciding whether that is the behaviour we want, or whether replay should be a
  merge.
- **Nothing stops the Composer saving over a running compose.** Proposed guard:
  the save route refuses while the book's phase status says a compose is running.
- **Google Drive copy fails** with "Operation not permitted" every time; Finder is
  opened for a manual drag. Known and expected — do not try AppleScript.
- `book-render-checks.json` and the comprehension report flag one name collision:
  "father" points at more than one person from p25. Advisory — the fix is a
  bridge sentence, never a reorder.

### Ground rules that bit me last session

- Only prose the pipeline AUTHORS may be respelled or reformatted:
  `book/book.md`, `chapters/`, `episodes/`, `slide-decks/`. NEVER OCR records
  under `_system/source/`, the shared source library, third-party `research/`, or
  the transcribed lectures under `augmentation/*/chapters/`. A sweep caught 78 of
  those transcripts before it was reverted; the boundary is pinned by
  `scripts/podcast/tests/test_normalize_spelling_scope.py`.
- Any pipeline phase run needs the book's own branch, or drive the phase module
  directly and say so.
- TS↔Python mirrors must move together: `_translit.py` ↔ `src/lib/translit.ts`,
  pinned by `plan-dashboard/scripts/translit.test.mjs`.

### Gates before any commit

```
python3 -m pytest scripts/podcast/tests -q          # 1680 passing
cd plan-dashboard && npm test                        # 47 passing
npx tsc --noEmit && npm run lint:views && npm run smoke   # clean / 0 / 32 routes
.venv/bin/ruff check scripts/podcast/ && .venv/bin/ruff format scripts/podcast/
```

Recovery point if anything goes wrong:
`git tag pre-rebuild/the-master-and-the-disciple-2026-07-21` (at `0e75f56`).
