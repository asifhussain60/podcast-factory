---
name: pf-compose-articulator
description: >
  Install a hand-off articulated chapter (e.g. a ChatGPT/Gemini rewrite of a
  Sessions-lane lecture chapter) into a book's Compose tab, through the SAME
  save path a human Composer edit uses. Sessions-lane ONLY — a book with a real
  Arabic source (a translation edition) is out of scope; this never checks
  source-faithfulness, only that the hand-off is faithful to the English
  already in book.md. Checks the SAME deterministic fidelity gates
  (`revoice_gates`) the automated articulation pass uses before writing
  anything, refuses on a finding unless overridden, resolves the chapter by
  its EXISTING heading in book.md (never the hand-off file's own heading,
  which can drift in casing), and records the edit into
  `_system/composer-edits.json` with `sessions-articulation.json` marked
  adapted. TRIGGER: "pf-compose-articulator", "install this chapter",
  "add this to the compose tab", "I articulated this chapter myself, put it
  in the book". Engine: scripts/podcast/compose_articulate.py.
---

# pf-compose-articulator

Built 2026-08-12, the night the automated `sessions/articulate.py` pass kept
timing out and reverting on Surah Al-Fateha's denser chapters — one crashed
outright on a runaway response, the fix for that landed, and the very next
chapter still needed two separate 15-minute-timeout-then-retry cycles just to
get through. Asif tested a GPT-articulated version of that chapter against
this pipeline's own fidelity gates by hand; it passed clean. He chose to
hand-author the rest of the book himself rather than keep paying for retries,
and needed a way to get each hand-off chapter into the book *correctly* —
which turned out to have real, specific failure modes of its own the first
time it was done by hand (see "What went wrong doing this manually" below).

## The one-line contract

> Same fidelity gates the automated pass runs. Same save path a human Composer
> edit uses. Sessions-lane books only — never a translation edition.

## Invocation

```
python3 scripts/podcast/compose_articulate.py <slug> --list
python3 scripts/podcast/compose_articulate.py <slug> "<chapter>" <md-file>                    # check only
python3 scripts/podcast/compose_articulate.py <slug> "<chapter>" <md-file> --install
python3 scripts/podcast/compose_articulate.py <slug> "<chapter>" <md-file> --install --force
python3 scripts/podcast/compose_articulate.py <slug> "<chapter>" <md-file> --json
```

**Check is the default.** `--install` writes nothing unless the gates pass, or
`--force` is given. `<chapter>` is a heading or a distinguishing fragment of
one — never a number (an unnumbered `## Introduction to the Book` section
means counting sections is unsafe, the same reason `rearticulate_chapter.py`
bans it). Run `--list` first whenever you are not certain of the exact
heading text; a match against more than one chapter, or none, prints the full
list and writes nothing.

## Why Sessions-lane only, and why that boundary is load-bearing

A translation-edition book (Kitab al-Riyad, the Master and the Disciple,
every book with a `book/source-crosswalk.json`) carries a real Arabic source
its English must stay faithful to — paragraph-level alignment, a crosswalk
that ties each rendered passage back to a source line. A hand-off rewrite
tested only against this tool's gates would prove *nothing* about that,
because there is no source in play here to check it against. The Sessions
lane's own chapters ARE the source — a lecture transcript being polished into
better English — which is a genuinely easier, fully self-checkable problem:
did the rewrite keep the same teachings, the same Arabic, the same speaker
attributions as the English already on the page. That is exactly what
`revoice_gates` checks, and why it is sufficient here and would not be for a
translation.

The engine refuses outright on any book without
`_system/sessions-articulation.json` — the file `sessions/ingest.py` writes
only for a Sessions-lane book. Point it at a translation edition and it exits
before touching anything, naming `rearticulate_chapter.py` (under the
`book-articulation` skill) as the tool for that different job.

## What the gate check actually verifies

The SAME `revoice_gates` function `_book_voice.py` runs on every automated
articulation window, called with the book's own declared `narrative_frame`
and `narrator_subject`:

- **Length**: the rewrite must land between 0.6x and 3x the original's word
  count — not a summary, not a runaway (the exact symmetric pair that fixed
  the 2026-08-12 crash: too-short was already gated, too-long was not).
- **Teaching loss**: every source `## `/`### ` heading survives verbatim, and
  no large word-count drop.
- **Arabic retained**: the rewrite's Arabic-script run count must not be
  lower than the source's.
- **Narrative frame**: grammatical person held throughout, no speech tag
  added/removed/re-pointed, no new lecture-hall address introduced under a
  frame that forbids it.
- **No new doctrinal P0s**, no leaked internal markers.

A finding refuses the install by default. `--force` overrides — a human
reviewer may know a finding is a false positive in a way the gate cannot; the
first real run hit exactly one (a heading came back "Stages **of** Love"
against the book's own "Stages **Of** Love" — a title-casing difference, not
a content defect). `--force` does NOT mean skip the check: the findings are
still printed, so an override is always a documented, visible decision, never
a silent one.

## What went wrong doing this manually, and why every step below exists

The first installation (done by hand, before this tool existed) got three
things wrong that are now structural:

1. **Trusted the hand-off file's own heading.** It didn't match the book's
   heading exactly, which would have failed the pipeline's own
   heading-survival check. The fix: the heading is ALWAYS resolved from
   book.md itself (`resolve_chapter`); the hand-off file's own `## ` line, if
   it has one, is read only to know where its body starts, then discarded.
2. **No check that this hand-off content matches the book's OWN articulated
   register** — bare word-count comparison was the only thing looked at.
   Fixed by running the actual `revoice_gates` the pipeline trusts, not a
   hand-rolled approximation of it.
3. **No guard against a live Composer autosaving the same file underneath the
   write.** `pf-compose-fix` already carries this exact guard
   (`composer_is_open`); this tool imports it rather than keeping a second
   copy. `--allow-composer-open` exists for the case where the dev server is
   open on a different book.

## Non-negotiables (mirrors `pf-compose-fix`)

1. **Every install is recorded as a Composer edit**, quoting the fingerprint
   the pipeline stamped — never one this tool computes. That is what makes
   the chapter survive a re-compose and marks it as one the automated pass
   may not regenerate.
2. **It refuses to write while the Book Composer is running**, unless told
   otherwise. A live Composer has clobbered a chapter before.
3. **The Sessions articulation ledger is updated in the same breath**
   (`sessions.articulate._record`, marked `adapted`) — the same function the
   automated driver uses, so the status card and a future `--resume` see this
   chapter as genuinely done, not still queued.
4. **A gate finding refuses by default.** `--force` is a human decision,
   made visible, never an implicit skip.
5. **No prose is rewritten here, by a model or otherwise.** This tool
   installs what it is handed; it does not improve it. A chapter that reads
   badly is `rearticulate_chapter.py`'s job, a different tool with a
   different contract.
6. **Verify in the Composer, not the PDF**, per the standing rule — though
   see the open finding below before trusting that page for a Sessions-lane
   book specifically.

## Known gap, not yet fixed: the Compose tab route for a Sessions-lane book

Found 2026-08-12 while building this: `/studio/<slug>/compose` is answered
by the OLDER 4-step workflow page (`[step].astro`, its `intake|review|edit|
publish` cockpit) rather than the newer Book Composer (`compose.astro`) —
reproducible even against a freshly restarted dev server, confirmed by the
redirect target changing correctly for a nonexistent slug (`/studio`) versus
a real one (`/studio/<slug>/edit`), which matches `[step].astro`'s own logic
exactly. `compose.astro` exists, is feature-complete, and reads book.md the
right way — it is just not currently reachable at its own URL. This tool's
writes (book.md + the Composer sidecar) are correct and ready for whichever
page eventually reads them; the route conflict is a separate, deeper Astro
routing question that needs its own look before "open the Compose tab" is a
reliable instruction for a Sessions-lane book.

## After a run

Report per chapter: the word-count ratio, every gate finding (clean or not),
whether it installed, and — once the routing gap above is resolved — the
exact URL to verify it on screen.
