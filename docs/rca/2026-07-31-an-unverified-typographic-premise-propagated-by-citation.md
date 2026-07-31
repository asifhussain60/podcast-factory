> Template from: Betsy Beyer, Chris Jones, Jennifer Petoff, and Niall Richard Murphy. ["Site Reliability Engineering."](https://landing.google.com/sre/book/chapters/postmortem.html).

# A typographic premise no one could check spread through four stylesheets (RCA-006)

### Date

2026-07-31 (premise introduced 2026-07-17 3:50 PM EST, reported 2026-07-31 ~9:35 AM EST)

### Authors

Claude (investigation + fix), reported by Asif

### Status

RESOLVED 2026-07-31. The descriptor is removed from every stylesheet that
carried it except the Urdu face, deliberately (see Root Causes 3). Open
corrective actions: AI-2, AI-3.

### Summary

For two weeks every Arabic run in this repo printed and displayed about 35%
larger than it should have. In the published reading edition of *The Master and
the Disciple* — rendered, delivered to Google Drive, and read — the Arabic base
letter stood taller than an English capital before a single vowel mark was
stacked on it, and a fully-marked quotation occupied 43px of ink where a whole
Latin line from ascender to descender occupies 18.8px.

The cause was one sentence, written once and never testable: "Arabic faces render
~35% smaller than Latin at the same point size." It entered as a fix to a UI card,
was generalised the next morning to every surface including print, was copied into
a second print lane citing the first, and was extended to two more faces citing
the original. Six stylesheets ended up sizing Arabic against a claim that measured
false of all four faces this repo ships.

Nobody could have caught it by reading the code. The claim is about font metrics;
the code contains no font metrics.

### Impact

Every Arabic run on every surface, from 2026-07-17 to 2026-07-31: the reading
edition PDF, the Book Composer's Read and Edit views, the book reader, the
companion cards, the Arabic reveal panel, and the compose print route.

One published book was affected in a form that left the building — *The Master
and the Disciple*, whose PDF was copied to Google Drive. Nothing was factually
wrong on the page and no text was lost; the edition simply set its scripture and
hadith at a size that made them shout over the prose they belong to. For a
reading edition prepared for publication, that is a defect of the same kind as a
typo, and it survived every gate.

The supplication lane carried the same defect but has never rendered anything —
no content declares `islamic_supplication` and no `units.json` exists — so its
correction changed a default rather than a document.

### Root Causes

**1. The premise was stated as measured, and the measurement was not kept.**
The originating commit says "measured 1.35x". It may well have been, on the
surface in front of its author: a 17px UI card in the compose editor, where the
comparison would have been against Lato or Inter, possibly against unvowelled
Arabic, possibly against a system fallback rather than Amiri at all. That
measurement cannot now be reconstructed, and this RCA does not claim it was
fabricated. What matters is that only the CONCLUSION was recorded. A number with
its derivation deleted cannot be re-checked when the surface changes — and the
surface changed the next morning.

Measured 2026-07-31 against the print body (Source Serif at 19.2px, x-height
9.16px, cap 12.86px), base letter ب, UNADJUSTED:

    Scheherazade New   11.44px   1.25x the x-height, 0.89x the cap
    UthmanicHafs       10.58px   1.16x              0.82x
    Amiri              12.52px   1.37x              0.97x
    Amiri Quran        12.52px   1.37x              0.97x

Each already sits between the Latin x-height and cap height with no adjustment
at all, which is the proportion Arabic beside Latin wants. There is no face here
that renders 35% small.

**2. It spread by CITATION, and each citation read as corroboration.**
The 135% did not get re-derived four times. It got copied, each time with a
comment pointing at the previous copy as its justification:

  - `supplication-print.css`: "Matches the 135% already used by the reading
    edition (book-print.css) so the two deliverables set Arabic at the same
    optical size."
  - `theme-tokens.css`, on Scheherazade and UthmanicHafs: "size-adjusted on the
    same 135% basis as Amiri above, for the same reason."

Both are true statements about consistency and neither is evidence about font
metrics. But a reader auditing `supplication-print.css` finds a citation to a
sibling stylesheet, checks that the sibling really does use 135%, and moves on
having verified nothing. Five more stylesheets then sized their Arabic *against*
the adjusted result and wrote comments explaining that the sizes read level
because of it — so by the end, six files agreed, and their agreement was the
only support any of them had.

**3. A correction for one script was applied to another on the same authority.**
The Urdu Nastaliq face got its own `size-adjust: 108%` in the same family of
changes. Nastaliq is a cascading script: most of a word's height is vertical
travel between letters rather than letter body, so the single-letter metric that
condemns the Arabic does not transfer to it. That value was deliberately LEFT in
place — measured and recorded (1.11x the Lato cap unadjusted, 1.20x at 108%) but
not changed, because no Urdu content exists to judge it against and changing a
number blind is precisely how the 135% arrived.

### Trigger

Asif reading page 8 of the printed edition, with the English and the Arabic in
one column where the size difference is unmissable. The defect had been visible
on screen for two weeks in surfaces he uses daily; the printed page is what made
it obvious.

### Detection

A human, on the finished artifact. Not by `lint:views`, `astro check`, the
smoke suite, `book-challenger`, `book-render-challenger`, or the site's visual
QA agent — none of which assert anything about relative type size, and none of
which could have, since the assertion needs font metrics that no gate computes.

### Resolution

The descriptor is removed from `theme-tokens.css` (every screen surface) and
`book-print.css` (the PDF) in one change, and from `supplication-print.css` in a
second. Screen and print had to move together: the Composer is where the page is
verified, and a PDF that disagrees with the Composer is worse than either being
wrong alone.

No `font-size` was touched. Shrinking the sizes instead — about 0.78rem for the
same pixels — would have left the false premise in place for every surface added
afterwards. Removing the descriptor makes the numbers already in the codebase
mean what their own comments claim. The `*Sized` family names are kept, since
every Arabic stack in the repo names them first; they are now plain aliases.

The measurement itself is written into `theme-tokens.css` as a table, so the next
person to wonder whether Arabic needs enlarging can read the answer instead of
re-deriving it — the thing the original commit did not do.

Two dependent numbers moved with it: `supplication-print.css` had
`line-height: 2.45` justified *by* the adjust, which would have left nearly 50%
headroom over the real ink where it was built to leave 10%; it is now 1.9, the
reading edition's own display-Arabic leading. Four comments in other stylesheets
asserting the disproved premise are corrected rather than left to mislead.

### Timeline

All times EST.

| When | What |
|---|---|
| 2026-07-17 3:50 PM | `809a75d` — 135% enters, for the compose editor + etymology card at 17px. "Arabic faces render ~35% smaller than Latin at the same point size… (measured 1.35x)." |
| 2026-07-18 5:05 AM | `1e9679b` — generalised to "editor, reader, and PDF". Thirteen hours from one UI card to the print deliverable, with no re-measurement on the new surface. |
| 2026-07-18 10:56 AM | `de788e5` — the stylesheet split carries it into `theme-tokens.css`. |
| 2026-07-19 8:40 AM | `02dd575` — copied into the supplication lane, citing the reading edition. |
| 2026-07-21 | `9ac904f` — extended to Scheherazade New and UthmanicHafs, "on the same 135% basis as Amiri above, for the same reason". |
| 2026-07-31 ~9:35 AM | Asif, from page 8 of the printed edition: "The Arabic script font is too big compared to the English font size." |
| 2026-07-31 10:05 AM | Measured in Chromium against the real font files; premise false for all four faces. |
| 2026-07-31 10:20 AM | `2161e91` — removed from screen + book print, verified live in the Composer. |
| 2026-07-31 10:55 AM | `52948f8` — removed from the supplication lane; leading corrected with it. |

## Action Items

| ID | Action | Type | Owner | Status |
|---|---|---|---|---|
| AI-1 | Remove the descriptor everywhere it was unfounded; record the measurement in the stylesheet rather than the conclusion alone | Fix | Claude | **DONE** 2026-07-31 |
| AI-2 | A metrics gate: assert in a test that each Arabic face's base letter falls in a stated band against the Latin body it sits beside, measured in headless Chromium the way this RCA measured it. Turns "someone will notice on a printed page" into a failing test | Detect | — | OPEN |
| AI-3 | Revisit the Urdu 108% once real Urdu content exists to judge it against | Verify | — | OPEN |

## Lessons Learned

### What went well

The removal was one descriptor in three files, because the spread was by copy of
a single value rather than by re-derivation into many. A premise that had been
re-expressed differently in each stylesheet would have taken far longer to pull
out, and would have left survivors.

Every stylesheet stated its reasoning in a comment. Those comments are what made
the propagation traceable in an afternoon — including the ones that were wrong,
which is the argument for writing them even when they turn out to mislead.

### What went wrong

A claim about the world was recorded as a number without its derivation, and then
travelled by citation until six files agreed with each other and nothing else.
"Matches the value already used by X" reads like corroboration and is not: it is
one source counted twice.

A correction validated on one surface at one size was promoted to a global font
descriptor in under a day. The generalising commit's own title — "size Arabic
consistently across editor, reader, and PDF" — describes the risk exactly:
consistency was achieved, correctness was never re-checked on the new surfaces.

Two weeks of every gate passing, on a defect visible to anyone who looked at the
page. Gates that read source cannot see rendered type; the visual QA agent that
does look at pixels is not asked about relative type size.

### Where we got lucky

The supplication lane copied the defect but had not yet rendered anything, so
correcting it cost nothing. Had a devotional text been typeset and delivered from
that lane first, the same wrong proportion would have shipped in a facing-column
layout where it is worse — 1.86x the English x-height — and in a document class
where a reprint is not a re-render.
