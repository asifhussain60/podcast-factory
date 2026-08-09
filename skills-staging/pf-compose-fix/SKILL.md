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

## What it checks — six defects

Five come from `_book_defects`, which the compose apparatus's `defect-scan` step and the
recorded-defect tests also read. There is no second copy of the rule.

| Defect | Repair |
|---|---|
| `duplicated-arabic` — a blockquote repeats the Arabic its lead-in already gave | automatic |
| `prophet-wrong-honorific` — the Prophet carries `(ع)`, the honorific of the Imams | automatic |
| `honorific-overuse` — a figure's compact honorific after every occurrence | automatic |
| `stale-provenance` — the record of which Arabic is scripture no longer matches the page | `--refresh-provenance` |
| `romanized-arabic` — a whole Arabic saying in the English character set | `--resolve-romanization`, and it chooses between two cures |
| `english-rtl` — an English translation set in the Arabic face | **none — fixed at the renderer** |

### The sixth is a RECORD, not a string

`stale-provenance` lives in `_book_arabic_audit.provenance_drift`, not in `_book_defects`,
because that module holds read-only detectors over chapter TEXT and this one asks whether
a FILE still describes that text. Its repair writes `_system/`, never `book/book.md`, so
it needs no Composer guard and records no Composer edit.

Why it matters more than it reads: `_system/book-arabic-audit.json` decides the Arabic
face, the Arabic ink, the panel a quotation is drawn in and the face of its English
rendering. It is written by a COMPOSE and read at RENDER time, and everything this skill
does in between edits the book underneath it. On 2026-08-09 all seven books had drifted,
and fifteen Qur'anic passages across three of them were filed as somebody's words —
harmless while provenance chose only a typeface, a doctrinal misstatement the moment it
chose a colour. Deterministic and free: no model, no network.

### A romanized saying has TWO cures, and the engine picks between them

`--resolve-romanization` asks, before it writes anything, whether the page ALREADY prints
this saying's Arabic beside the bracket — the display line under the lead-in, or the same
sentence. If it does, the romanization is a duplicate and it goes. If it does not, the
ladder in `_book_romanization` finds the script and puts it in.

The check is `compose_fix._already_in_script`, and it compares consonantal skeletons over
the paragraph and its two neighbours. It has to fold Perso-Arabic letters first: the
shared `normalize_arabic` keeps only U+0621–U+064A, so it DROPS a farsi yeh rather than
folding it, and Spiritual Ethos prints the same saying of the Prophet once in Arabic
letters and once in Persian ones. Without the fold the first repair run read them as two
different sayings and printed the Arabic twice on one line.

Deleting is safe ONLY under that condition. Nine of the eleven findings in Spiritual Ethos
had Arabic within a line or two that belonged to a DIFFERENT saying; deleting on mere
adjacency would have erased the only record of the wording the romanization carries.

Bare `--fix` still never touches this defect — the two cures both need the ladder or the
adjacency test, and neither is a string transform.

### Why `english-rtl` is never repaired

It was a renderer defect and it is fixed there. A content repair would be a workaround for
a bug that is gone.

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
