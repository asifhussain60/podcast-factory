# Continuation prompt — book.md articulation

Paste the block below into a new session, from the repo root.

---

We are on branch `Islamic/the-master-and-the-disciple-augmented` (clean, pushed
through `b63fe4d`). The Book Composer work is finished and green; what remains
is a **content** problem in `content/Islamic/the-master-and-the-disciple/book/book.md`.

## The finding

Two of the eight chapters were never re-voiced into the author-companion
register and are still the literal faithful base. Together they are **21,675 of
the book's 37,205 words — 58% of it.**

Measured by comparing each chapter in `book.md` against its own faithful-base
chunk in `book/_chunks/translation/` with `difflib.SequenceMatcher.ratio()` on
whitespace-normalised text (lower = more re-voiced):

| Chapter | Words | Similarity to faithful base | State |
|---|---|---|---|
| Preface — How to Read a Conversation Made of Doors | 854 | 30.2% | re-voiced |
| 1. The Persian Who Was Dead and Revived | 865 | 13.1% | re-voiced |
| 2. A Stranger in the City | 1,109 | 46.3% | re-voiced |
| 3. The Boy at the Door | 3,848 | 14.1% | re-voiced |
| 4. How the World Was Made | 1,596 | 76.6% | weakly re-voiced |
| 5. The World, the Hereafter, and the Speech | 3,684 | 29.3% | re-voiced |
| 6. Three Layers of Knowledge | 3,574 | 23.3% | re-voiced |
| **7. The Five Shares and the Long Road to the Shaykh** | **7,258** | **100.0%** | **UNVOICED** |
| **8. Homecoming, the Father, and the Debate with Abu Malik** | **14,417** | **98.6%** | **effectively UNVOICED** |

Corroborating evidence, all independently checked:

- `_system/book-voice-report.json` records `{"revoiced": 8, "reverted": 1}`.
  Chapter 7 is that revert. Chapter 8 is counted as re-voiced but is 98.6%
  identical to its base, so the pass did not actually change it.
- Chapters 7 and 8 are the **only** two sections with **zero em-dashes**
  (others carry 6–50 each) — a register tell, since the companion voice uses
  them heavily.
- Chapter 7 opens on raw transcription — `The boy said: "Praise be to God…"` —
  where chapter 6 opens in narrator voice: `He put it to me plainly.`
- `_book_voice.py:219` reverts a chapter to base on any fidelity-gate failure
  and logs it, so this is the designed behaviour firing, not corruption.

Book-wide prose stats (for whatever re-voicing is done): mean sentence 29.8
words, p90 53 words, **189 sentences over 45 words** — 125 of those 189 are in
chapters 7 and 8. Zero archaic vocabulary anywhere, so the problem is sentence
length and register, not diction.

## What to do

1. Re-run the author-companion voice pass over **chapters 7 and 8 only**. Do not
   re-run the whole book: chapters 1–6 and the preface are correctly voiced and
   re-voicing them again would compound. Entry point is
   `apply_author_companion_voice` in `scripts/podcast/_book_voice.py`; it already
   works per chapter and reverts per chapter on gate failure.
2. Chapter 7 hit the fidelity gate last time — **find out which gate and why
   before re-running**, or it will simply revert again. Chapter 8 is 14,417 words
   and may be hitting a window/truncation limit rather than a gate; check that
   separately.
3. Chapter 4 sits at 76.6% (weakly voiced) — decide whether it needs a pass too.
4. After voicing, re-run the render and re-check with the numbers above so the
   improvement is measurable, not impressionistic.

Costs a model pass. Ask before spending.

## Do not re-attempt

Writing Composer saves into `book/_chunks/` as a durability mechanism. It was
tried and reverted in `b63fe4d`; the reasoning is recorded inline in
`plan-dashboard/src/pages/api/studio/book-md.ts`. Short version: that cache holds
the faithful base, and `compose_book_v2` re-applies fluency/augment/voice on top
of it every run, so seeding it with already-voiced human-edited prose compounds.
Durable human edits need a sidecar re-applied *after* compose — the pattern
`_book_bridges.py` uses with `_system/comprehension-bridges.json`.

Also note `book/_chunks/book/` is a **dead** cache from the retired
`_book_compose.py`. It holds a June 11 literary compose that reads more
articulately than today's output. It is not what the pipeline produces now — do
not mistake it for a newer version, and do not restore from it without deciding
deliberately, since it predates the "Sharia" standardisation (`3ace3dc`) and the
full augmented re-run (`2af5241`).

## Repo state

All gates green as of `b63fe4d`: pytest 1523 · ruff clean · astro check 0 errors
· `lint:views:strict` 0/0 · eslint 0 errors · prettier clean · 16 JS tests ·
smoke 32/32. 90 eslint *warnings* remain (44 no-explicit-any, 22
exhaustive-deps, 13 set-state-in-effect, 11 refs) — all pre-existing, all in
files untouched by this work, and the pre-commit hook classifies warnings as
non-blocking.
