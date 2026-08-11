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
python3 scripts/podcast/compose_fix.py <slug> --chapters 3 --vowel      # asks a model
python3 scripts/podcast/compose_fix.py <slug> --preface                 # write the missing preface
python3 scripts/podcast/compose_fix.py <slug> --preface force           # re-ask a cached one
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

## The first thing it checks is how the book OPENS

Before any chapter, and whatever `--chapters` was asked for, every run reports whether the
book begins with a preface written **to the reader**: what this is, and what is in it.

Asif's rule, 2026-08-11: **every book is prefaced.** Build it from the original source
where there is one; where there is not, read the content and build one from that.

It is book-level, so it cannot be scoped to a selection — "is there a preface" is not a
property of chapter 3, and a run that checked chapters 3–5 and said nothing about a book
with no opening at all would be reporting on the wrong thing.

| Finding | What it means |
|---|---|
| `spoken-opening` | The book opens with the speaker opening an OCCASION — greeting the room, introducing himself, asking leave to begin. Real, rightly said aloud, and not a preface. This is what the first Sessions book shipped with. |
| `missing-preface` | The book opens straight into its first chapter. |
| `empty-preface` | The heading is there with almost nothing under it. |
| `no-sections` | The book has no `##` sections at all. |

**`--preface` writes one**, from the book's own chapters, through the SAME
`_book_frontmatter.apply_introduction` every other route uses — the 250-word cap, the
honest `## Introduction to the Book` title, the book's own voice, and the rule that every
fact comes from a file. Asked of a model **once per book, ever**; `--preface force` re-asks
it. It never overwrites a preface Asif has written in the Composer — that guard lives
inside `apply_introduction`, so every caller gets it.

The chapter list it works from is `book/book-toc.json` where one exists and the book's own
`##` headings where one does not. That fallback is what makes "build one from the content"
possible at all: the TOC is a compose artifact carrying the source lines each chapter was
translated from, so a route that translates nothing never writes one, and the Sessions lane
is the first such route.

A book whose `series-config.yaml` says `source_medium: audio_lecture` is briefed
differently — a series of talks that were delivered, never a treatise or a dialogue. Only
the shape clause changes; the cap, the prohibitions and the register are identical.

## What else it checks — twelve defects

Nine come from `_book_defects`, which the compose apparatus's `defect-scan` step and the
recorded-defect tests also read. There is no second copy of the rule.

| Defect | Repair |
|---|---|
| `duplicated-arabic` — a blockquote repeats the Arabic its lead-in already gave | automatic |
| `prophet-wrong-honorific` — the Prophet carries `(ع)`, the honorific of the Imams | automatic |
| `honorific-overuse` — a figure's compact honorific after every occurrence | automatic |
| `stale-provenance` — the record of which Arabic is scripture no longer matches the page | `--refresh-provenance` |
| `romanized-arabic` — a whole Arabic saying in the English character set | `--resolve-romanization`, and it chooses between two cures |
| `english-rtl` — an English translation set in the Arabic face | **none — fixed at the renderer** |
| `translation-outside-card` — the English rendering prints below the card, not inside it | automatic |
| `translation-leads-a-paragraph` — the rendering opens the paragraph, a whole sentence follows | automatic |
| `translation-fused-with-prose` — separating the rendering would leave prose that no longer parses | none — reported |
| `bare-arabic` — an Arabic passage still carries no vowel marks | `--vowel`, which ASKS rather than searches |
| `quote-card-rules` — part of the approved four-card design is no longer on disk | none — reported |
| `orphaned-quote-kind` — a person's declaration of a quotation's kind matches nothing | none — reported |

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

### The last two guard the four quotation cards themselves

A quotation is drawn as one of four cards — Qur'an, prophetic tradition, verse, and the
saying that is the default. Asif converged that design over a sample page before anything
touched the site, and that page is still the approved reference:
`http://localhost:4322/_specimen-quote-tiers.html`. What it shows is what the reading
edition owes its reader, and until 2026-08-09 nothing checked that it still held.

The design is spread over six files that nothing held together — the rules in one
stylesheet, the markup in the two renderers that must agree, the step that inlines the
stylesheet into the PDF, and a per-book JSON in which a person says which quotation is
which. **Every one of them fails silently and in the same direction**: the card degrades
to the default plate, or to no plate at all, and the page still renders. So a chapter
could be reported clean while every quotation in it had lost its card.

`quote-card-rules` (`QC-NNN` in `_quote_cards`) checks the design, not the file. The
specimen's stylesheets are inlined copies taken the day it was approved and they have
already drifted in ways that mean nothing — a gradient reformatted onto one line, a
`.q-cite` rule deleted the same day it was drafted — so a byte comparison would fire on
formatting forever and be switched off within a week. What is checked is what a reader
would see go missing: four cards, four inks, a mark per kind, the two-column verse grid
and its collapse on the CONTAINER rather than the window, and — since 2026-08-11 — the
shape Asif approved on the specimen that day. Every card is a tinted plate inside a 2px
frame in its own ink, and every header is CENTRED between two hairlines. The Qur'an's is
not a header but a filled brown bar heading the panel, its chapter and verse set in white.
The other three name their kind, and a saying or a verse adds the speaker beside it as one
string — `Saying: Hasan al-Basri` — which is why the renderers stamp the kind in a span of
its own. A prophetic tradition never names one: it is already the claim that the Prophet
said it. It is repo-wide, so it prints once.

`orphaned-quote-kind` checks this book. A declaration is filed under its quotation's own
first line, inside its chapter's Composer key; edit either and it stops matching, the
block reverts to the default card and a verse loses its two columns. **This tool is one of
the things that causes that** — `--fix` deleting a duplicated Arabic run off the top of a
blockquote re-keys the declaration under it — which is the argument for checking it here
rather than in a site gate: the repair and the damage are one command apart.

Neither is repaired. A missing CSS rule is a design change and belongs to whoever is
changing the design; re-keying a declaration means choosing which quotation a person
meant, and on a religious edition an inferred attribution is a claim nobody made.

### Bare Arabic is ASKED about, never searched for

Arabic in these editions always carries its marks (Asif, 2026-07-29), and the pipeline puts
them there at compose time. So a bare passage on the Compose tab is not a missing feature —
it is a compose that did not finish, and until 2026-08-11 that happened routinely and
invisibly. A model normalising ONE letter while vowelling correctly around it had its whole
answer discarded by the marks-only gate, and the run stayed bare with nothing but a line in
`_system/book-vowelling.json` to say so. Across the seven composed books that was 71 of 75
refusals.

**The root fix is in the pipeline, not here.** `_vowelling.transfer_marks` now carries the
model's MARKS onto the source's own LETTERS whenever every difference is one letter in two
shapes — the alif that gained a hamza, the Perso-Arabic yeh, kaf, heh and teh marbuta the
Urdu-set passages use. The result's skeleton is source-identical by construction, so the
gate's guarantee is strengthened rather than relaxed. It runs in the compose-time pass, in
the Composer's Diacritics button, and here, from one definition pinned across the mirror
pair by `vowelling.fixtures.json`.

**This check is the second line.** `--vowel` asks the same engine the pipeline uses. It
does NOT hunt the scan, the OCR or the knowledge base the way `--resolve-romanization`
does, and the difference is not an oversight: a spelling is written down somewhere to be
found, a vocalisation is not. It is asked for, from a model told to read the passage as the
Ismaili tradition reads it — the vocabulary of the da'wa as the tradition's own scholars
give it, names and titles as the Ismaili sources have them, and classical Islamic
scholarship where the tradition is silent — under the gate that admits marks and nothing
else. Scripture is never asked at all: `_mushaf` answers a Qur'anic run out of the
canonical text in the repo.

A passage that still refuses after all that is a real one — the source spells the word a
way the model will not vowel without changing it — and it is reported and left bare rather
than rewritten.

### The English rendering belongs INSIDE the card, and only half of them can be moved

Asif reported it from the Compose tab on 2026-08-09: the verse drew as a card and its
translation printed underneath, outside the panel. It is a CONTENT defect — `book.md`
carries the rendering as the next paragraph of body prose — and there are 100 of them
across all seven books.

**There are three shapes and only the third needs a person.** The line between them is
where the repair stops being a move and starts being authorship — because carrying the
author's prose inside a quotation panel on a religious edition would be a worse defect
than the one being repaired.

1. **The paragraph is the rendering and nothing else.** It folds into the blockquote
   whole: nothing reworded, nothing deleted, the same sentence one level in.
2. **The paragraph OPENS on the rendering and continues into a sentence of the author's
   own** — *"…(Al-Hijr: 56). The Quran's assurances of mercy come fully alive in…"*. The
   rendering moves in and the sentence stays where it is. Nothing is decided: the boundary
   is punctuation the author already placed, and the test for "a sentence of its own" is
   deliberately blunt — it must begin on a capital and run to at least four words.
3. **What follows is not a sentence.** It is a connective the author's own sentence
   depends on — *"…encompasseth all things" (Al-Araf: 156), and* — where he strung two
   verses together across two blockquotes, or an interjection between two halves of one
   verse. Moving the rendering out leaves prose that no longer parses, so the repair would
   have to WRITE something. Reported as `translation-fused-with-prose` and left standing.

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
4. **`--vowel` is the only flag here that spends money, and it is never implied.** Plain
   `--fix` will not vowel anything, for the same reason it will not resolve a romanization:
   both need a model, and a check must stay free and instant.
5. **No prose is rewritten by a model here.** For a chapter that reads badly rather than
   one carrying a defect, the tool is `rearticulate_chapter.py` under the
   `book-articulation` skill — a different job with a different contract.
6. **Verify in the Composer, not the PDF** (`/studio/<slug>/compose`), per the standing
   rule. Show the repaired passage on screen.
7. **Cite rule ids, never restate them.** `REQ-BA-NNN` for articulation,
   `BK-*` for the challenger's probes.

## After a run

Report per chapter: what was found, what was repaired, what remains and why. A defect left
standing is not a failure of the run — for `romanized-arabic` it is the correct outcome,
and saying so is part of the report.
