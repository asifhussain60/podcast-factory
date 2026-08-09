---
name: pf-compose-fix
description: >
  Check and repair one book's chapters on the Book Composer's Compose tab, using the
  SAME rules the pipeline's post-articulation gate applies, WITHOUT re-running the
  podcast-factory pipeline. Takes a book (slug) and chapter numbers (one, several, a
  range, a title, or all). Scope is strictly the reading edition — book/book.md and the
  Composer's edit sidecar; never the podcast chapter sources, the episode framings or
  the slide decks. MUST be loaded for any request to fix a defect Asif saw on the
  Compose tab. TRIGGER: "pf-compose-fix", "fix chapter N of <book>", "check the compose
  tab for <book>", "the Arabic is duplicated / romanized / the honorifics are everywhere".
  Engine: scripts/podcast/compose_fix.py. Rule source: docs/standards/book-articulation.md
  (REQ-BA-NNN) and the book-challenger probe catalog (BK-*) — cite by id, never restate.
---

# pf-compose-fix

The gap this fills, in one sentence: the agent that runs the final checks after
articulation — `book-challenger` — states in its own spec that it never mutates the book
and the only safe remediation is a Worker re-compose. That is the cost Asif does not want
to pay to delete a bracket. **This skill keeps the challenger's rules and swaps its cure.**

## The one-line contract

> Same checks the pipeline runs. Repair through the Composer, never through a re-compose.
> Anything that needs judgment is proposed, never applied.

## Invocation

```
python3 scripts/podcast/compose_fix.py <slug>                     # check every chapter
python3 scripts/podcast/compose_fix.py <slug> --list              # the chapter list
python3 scripts/podcast/compose_fix.py <slug> --chapters 1,3,9
python3 scripts/podcast/compose_fix.py <slug> --chapters 3-5 --fix
python3 scripts/podcast/compose_fix.py <slug> --chapters "Kumayl" --fix --only honorific-overuse
python3 scripts/podcast/compose_fix.py <slug> --json
```

**Check is the default.** `--fix` is never implied, and `--fix` without `--chapters`
operates on the whole book — say so before running it.

## Chapter numbers are safe HERE, and nowhere else in the pipeline

`rearticulate_chapter.py` bans printed chapter numbers in its own docstring: the
introduction is an unnumbered `##` section, so counting sections makes "chapter 3" land on
section 4. **The ban is on counting.** This engine reads the number off the heading, which
is a different operation — verified across all seven books with a reading edition: each
numbers every chapter heading and leaves exactly one section (the introduction)
unnumbered. A book that ever numbers inconsistently gets the chapter list printed and no
write. Never hand-resolve a number yourself; call `--list`.

## What it checks — five defects, one module

Every check comes from `_book_defects`, which the compose apparatus's `defect-scan` step
and the recorded-defect tests also read. There is no second copy of the rule.

| Defect | Repair |
|---|---|
| `duplicated-arabic` — a blockquote repeats the Arabic its lead-in already gave | automatic |
| `prophet-wrong-honorific` — the Prophet carries `(ع)`, the honorific of the Imams | automatic |
| `honorific-overuse` — a figure's compact honorific after every occurrence | automatic |
| `romanized-arabic` — a whole Arabic saying in the English character set | **proposed only** |
| `english-rtl` — an English translation set in the Arabic face | **none — fixed at the renderer** |

### Why two of them are never repaired automatically

- **`romanized-arabic`.** The honest fix is the Arabic, and the script has to come from
  somewhere. For two of the fourteen live instances it exists nowhere on disk — not in the
  book, not in the source scan, not in the hadith corpus — so supplying it would mean a
  model recalling scripture onto the page of a religious edition. Deleting the
  romanization satisfies the rule locked 2026-08-02 and costs the reader nothing, because
  the English translation always sits beside it — but that is Asif's call, so the engine
  proposes and stops.
- **`english-rtl`.** It was a renderer defect and it is fixed there. A content repair
  would be a workaround for a bug that is gone.

## Non-negotiables

1. **Every repair is recorded as a Composer edit**, quoting the fingerprint the pipeline
   stamped — never one this skill computes. That is what makes the change survive a
   re-compose AND marks the chapter as one the model may not regenerate. A direct write to
   `book.md` loses both, silently.
2. **It refuses to write while the Book Composer is running.** On 2026-08-09 a live
   Composer autosaved a truncated Arabic quotation into a shipped book while a script was
   working on the same file. `--allow-composer-open` exists for the case where the server
   is up on a different book; using it on the same book is how that incident repeats.
3. **A repair is chapter-scoped; the apparatus is not.** The honorific convention's "first
   use", the glossary harvest and the paragraph alignment are properties of the whole
   book. After a fix run, offer `apply_book_apparatus.py <slug>` — the pipeline's own
   deterministic tail, runnable standalone — and say plainly that it will touch chapters
   outside the selection.
4. **No prose is rewritten by a model here.** For a chapter that reads badly rather than
   one carrying a defect, the tool is `rearticulate_chapter.py` under the
   `book-articulation` skill — a different job with a different contract.
5. **Verify in the Composer, not the PDF** (`/studio/<slug>/compose`), per the standing
   rule. Show the repaired passage on screen.
6. **Cite rule ids, never restate them.** `REQ-BA-NNN` for articulation,
   `BK-*` for the challenger's probes.

## After a run

Report per chapter: what was found, what was repaired, what remains and why. A defect left
standing is not a failure of the run — for `romanized-arabic` it is the correct outcome,
and saying so is part of the report.
