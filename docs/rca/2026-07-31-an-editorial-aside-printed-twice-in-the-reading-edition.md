> Template from: Betsy Beyer, Chris Jones, Jennifer Petoff, and Niall Richard Murphy. ["Site Reliability Engineering."](https://landing.google.com/sre/book/chapters/postmortem.html).

# An editorial aside printed twice, once in the narrator's own voice (RCA-005)

### Date

2026-07-31 (defect introduced 2026-07-29 7:30 PM EST, detected 2026-07-31 ~8:15 AM EST)

### Authors

Claude (investigation + fix), reported by Asif

### Status

RESOLVED 2026-07-31. Both halves of the root cause fixed: fence matching is now
tolerant of the bare-marker form in every pipeline consumer, and the chapter-3
duplicate is removed from `book.md` and the re-rendered PDF. Open corrective
actions: AI-2, AI-3, AI-4.

### Summary

Chapter 3 of the published reading edition of *The Master and the Disciple*
printed the same editorial note twice. Once correctly — a labeled, fenced aside
attributed to the wider tradition. And once absorbed into the narrator's own
closing paragraph, rewritten into the book's voice, with a bare `**Editorial
note**` in the middle of a sentence about the covenant.

The second copy is the serious one. An editorial aside is corpus material drawn
from *another* work; the fence and its label exist precisely so a published
edition never presents it as this book's own teaching. Dissolved into the
narrator's paragraph, it did exactly that.

Root cause: the Composer's editor cannot carry an HTML comment through a
round-trip and serializes a fence marker back as a bare text line. Every fence
consumer on the Python side matched `<!-- editorial:begin -->` and nothing else.
A pass that cannot see a fence does not fail — it silently reclassifies the aside
as prose.

### Impact

One chapter of one published book, in the reading edition only. The duplicated
text is a faithful paraphrase of the aside — nothing false was printed, and no
teaching was lost — but a corpus-derived passage appeared unlabeled in the
narrator's voice, which is the specific failure the editorial fence contract
(BK1007) exists to prevent.

The PDF had been delivered to Google Drive in that state. The podcast lane
(`chapters/*.txt`, episode framings, slide decks) was never affected: editorial
asides are a book-route artifact and do not reach those surfaces.

No other book is affected. A sweep of every `content/*/*/book/book.md` for a bare
`**Editorial note**` outside a fence returns nothing after the repair, and no
book.md in the repo currently carries a bare marker line of any fence kind.

### Root Causes

**1. Fence matching was comment-only, in every consumer.**
`_book_voice._EDITORIAL_SPAN_RE`, `_book_companion._EDITORIAL_SPAN_RE`,
`_book_augment._strip_existing_blocks`, `_book_bridges._BRIDGE_SPAN_RE`,
`_book_frontmatter._INTRO_SPAN_RE` and `_self_study._strip_all_fences` each
compiled their own regex over the literal `<!-- kind:begin -->` form. Six
independent copies of the same assumption, and the assumption is false of any
`book.md` that has passed through the Composer's editor between the flattening
and `preserveFences`' restore.

This caused the defect twice over, at two different stages:

- **Protection failed.** An articulation pass takes `asides = findall(body)`,
  sends the remainder to the model, and re-appends the asides verbatim. With the
  markers in bare form the span fell into the remainder, so the model was handed
  a corpus aside as ordinary chapter prose and did what it is asked to do —
  articulated it into the book's register and wove it into the paragraph before.
- **Idempotency failed.** `0book-augment` replaces its prior block rather than
  stacking, and finds that block by its fence. Equally blind, it appended a fresh
  aside on the next compose while the dissolved copy stayed in the prose.

**2. Nothing downstream compares an aside against the chapter it sits in.**
`insert_blocks` is documented as idempotent and is unit-tested as idempotent —
against a *comment-fenced* prior block. No gate asks the simpler question that
would have caught this whatever the fence looked like: does this chapter's prose
already contain the editorial block's own sentences?

### Trigger

A Composer save of chapter 3 on 2026-07-29, in the session that also recorded
vowelling proposals and companion notes (commit `9c5053b`, 7:30 PM EST). Its
parent carries 5 fenced asides and zero inline `**Editorial note**`; the commit
itself carries 5 fenced asides and one inline copy.

### Detection

Asif, reading the book. He pasted the note into a session and asked what it was
and where it came from — the fenced copy, which is working as designed. The
duplicate in the narrator's paragraph was found while answering.

Not detected by: the compose pipeline (all stages reported clean), the render
gate, or the publish gates. `book-challenger` has a passages-narrated-twice
check; whether it would recognise a paraphrase-level duplicate of an aside is
untested and is AI-4.

### Resolution

New shared module [`scripts/podcast/_book_fences.py`](../../scripts/podcast/_book_fences.py):
one matcher that accepts both the comment form the pipeline writes and the bare
line an editor round-trip leaves behind. The bare alternative is anchored to a
whole line under `re.MULTILINE`, mirroring `markerOf` in `book-fences.ts`, so a
chapter that merely *mentions* `editorial:begin` mid-sentence stays prose.

All six consumers now go through it. Writing is deliberately not offered there:
each owning module keeps its own `<!-- <kind>:begin -->` literal, because
`test_fence_kinds_cross_language.py` discovers the live set of fence kinds by
scanning the pipeline for exactly those literals.

The chapter-3 duplicate was excised from `book/book.md` directly rather than
through the Book Composer. The Composer is the singular path for *authored*
changes, and it makes a chapter permanently exempt from every model pass; this
was drift removal, not authorship — the dissolved copy exists in no compose cache
(`book/_chunks/translation/` is clean), so the repaired state is what the next
compose produces anyway. The PDF was re-rendered from the repaired source.

### Timeline

All times EST.

| When | What |
|---|---|
| 2026-07-29 7:30 PM | `9c5053b` — Composer save of chapter 3. First inline copy of the aside enters `book.md`. |
| 2026-07-30 9:47 AM | `5d28425` — a later articulation pass rewords the dissolved copy again. Still invisible to every gate. |
| 2026-07-31 ~8:15 AM | Asif asks what the editorial notes are. |
| 2026-07-31 8:30 AM | Duplicate found; origin traced to `9c5053b` by `git log -S`. |
| 2026-07-31 8:40 AM | Shared fence matcher landed, six consumers converted, 12 new tests. Full suite green (1,881 Python, 356 site). |
| 2026-07-31 8:44 AM | PDF re-rendered from the repaired `book.md` (122 pages). |

### How we know it was the fence and not something else

Two mechanisms could produce a duplicated aside. They are distinguishable by the
*shape* of the surviving fenced block.

`preserveFences` step 3 re-appends a lost span **verbatim** from the original —
which would be `format_editorial_block`'s output, soft-wrapped at 96 characters
over several `> ` lines with no blank lines inside the fence. The block actually
in chapter 3 is one long `> ` line with blank lines on both sides inside the
fence: the editor's serialization, with its markers restored from bare text by
step 1. So the span was never lost and never re-appended.

That leaves only the other path: the aside survived as its own block, and a model
separately produced a second, articulated copy — which it can only have done if
it was handed the aside as prose.

## Action Items

| ID | Action | Type | Owner | Status |
|---|---|---|---|---|
| AI-1 | One tolerant fence matcher, adopted by all six consumers, with the bare-marker regression pinned by tests | Fix | Claude | **DONE** 2026-07-31 |
| AI-2 | Pin `_book_fences` against `book-fences.ts` `markerOf` with shared fixtures, as the other four TS/Python mirror pairs are | Prevent | — | OPEN |
| AI-3 | Compose-time check: no editorial block's prose may also appear in its chapter's body. Catches this class whatever the fence looks like | Prevent | — | OPEN |
| AI-4 | Confirm `book-challenger`'s narrated-twice check recognises a paraphrase-level duplicate of an aside; extend it if not | Detect | — | OPEN |

## Lessons Learned

### What went well

The fence contract itself is sound, and the site side had already reasoned this
through: `book-fences.ts` documents the round-trip hazard in detail and restores
bare markers on the way in. The diagnosis was fast because that comment named the
failure mode before anyone had seen it happen.

The duplicate was a paraphrase, not an invention. The model asked to articulate
prose articulated the prose it was given.

### What went wrong

Six modules each re-derived what a fence looks like. The site side had a single
`FENCE_KINDS` contract and a documented hazard; the pipeline had six regexes and
no shared notion of the marker at all. The cross-language test pinned which
*kinds* exist on both sides — but not what a marker of that kind may *look like*,
which is the axis that broke.

A silent reclassification is the worst failure shape available here: a pass that
cannot find a fence reports success, because from where it stands there was
simply no aside in that chapter.

### Where we got lucky

The augment pass re-ran and appended a fresh fenced copy. That visible duplicate
is what Asif noticed and asked about. Had the aside only ever been dissolved —
one copy, in the narrator's voice, reading perfectly well — nothing in the
pipeline would have flagged it and there would have been nothing to see.
