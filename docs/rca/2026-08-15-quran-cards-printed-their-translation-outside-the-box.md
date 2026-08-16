> Template from: Betsy Beyer, Chris Jones, Jennifer Petoff, and Niall Richard Murphy. [“Site Reliability Engineering.”](https://landing.google.com/sre/book/chapters/postmortem.html).

# Quran/hadith cards printed with no translation inside them, and the existing detector never saw it (incident #2026-08-15-01)

### Date
2026-08-15

### Authors
Claude Sonnet 5 (session working from a Book Composer screenshot Asif provided)

### Status
Resolved. Root cause confirmed and fixed in `_book_translation_cards.py`; the
deterministic repair already built for this defect class (`_book_defect_fixes.py`,
`compose_fix.py`) has been re-run across every affected book.

### Summary
Asif screenshotted the Compose tab on `mukhtasar-ul-asar-1`: a Quran verse ("AL-FURQAN:
48") drew as a card with the Arabic inside a boxed panel and no English translation
anywhere in the box — the translation printed as an ordinary paragraph below it instead.
He read this as a rendering bug and asked for an RCA and a deterministic fix.

The renderer is not at fault. A detector and repair for exactly this defect class already
exist (`_book_translation_cards.py`, built 2026-08-09 for an earlier, structurally
identical report), and the repair moves the stranded translation into the card without
rewording or deleting a single character. But that detector's entry condition —
"the paragraph opens on a quotation mark" — only asks about `text[0]`. Every citation in
`mukhtasar-ul-asar-1` (and several other books) opens on an ATTRIBUTION clause instead —
`God Almighty said: "…"` — so `text[0]` is `G`, not `"`, and all 34 of this book's stranded
translations were invisible to the detector, the `compose_fix.py check` report, and by
extension to anyone reading that report to decide what needed fixing.

### Impact
Every reading edition whose author cites this way (`Attribution: "quote" [citation].`)
carried Quran/hadith cards missing their translation, with no automated signal that
anything was wrong — `compose_fix.py check` reported these chapters clean. Confirmed
live instances, before the fix, across:

| Book | fold | split | fused (needs a person) |
|---|---|---|---|
| mukhtasar-ul-asar-1 | 1 | 8 | 6 |
| mukhtasar-ul-asar-2 | 0 | 2 | 1 |
| surah-al-fateha | 3 | 2 | 2 |
| kitab-al-riyad | 0 | 0 | 9 |
| spiritual-ethos | 0 | 0 | 7 |
| the-master-and-the-disciple | 0 | 0 | 5 |

The `fold`/`split` columns (13 instances across three books) are auto-repairable and have
now been repaired. The `fused` column is a genuinely different shape — a paragraph that
strings a SECOND and THIRD citation onto the sentence after the first, or interleaves
Arabic and English in running prose — which the existing tooling has always, deliberately,
left for a person rather than guess at (see Root Causes). Those are now surfaced in
`compose_fix.py check`, which they were not before this fix, and remain unrepaired
pending Asif's own read of each one.

### Root Causes
`cards_missing_their_rendering` (`_book_translation_cards.py`) is the single reading every
downstream shape classifier shares: a blockquote holding only Arabic, immediately followed
by a paragraph. Whether that paragraph is a CANDIDATE at all was gated on
`opens_on_a_quotation(text)`, which is `text[0] in _QUOTATION_MARKS` — literally, is the
paragraph's first character a quotation mark. That was correct for every example the
2026-08-09 build was shaped against (Spiritual Ethos, which always quotes directly: `"…"
(Al-Qalam: 4)`), and the module's own test suite names the assumption explicitly
(`test_ordinary_prose_after_a_card_is_not_a_rendering`: "Only a paragraph opening on a
quotation mark is a candidate at all").

`mukhtasar-ul-asar-1` cites differently throughout: every verse is introduced by its
speaker — `God Almighty said: `, `The Messenger of God (ص) said: `, `He also said: ` —
before the quotation mark, and the quote itself sits inside markdown italics
(`*"…"*`) with a SQUARE-bracket citation (`[Surah al-Furqan: 48]`) rather than the
parenthesized one (`(Al-Qalam: 4)`) the citation-tail regex was written against. Three
independent gaps, not one — a paragraph shaped this way failed the entry condition before
ever reaching the citation-tail check, so the second and third gaps were also latent and
invisible until the first was closed.

### Trigger
No trigger — this was a static, always-present detection gap in a specific book's own
citation convention, not a regression from a recent change. It surfaced now because Asif
looked at the rendered Compose tab and noticed the missing translation with his own eyes,
which is exactly the failure mode the 2026-08-09 defect class exists to catch — this
instance simply fell outside its coverage.

### Resolution
`_book_translation_cards.py`:
- Added `quotation_start(text)`, which returns the index of the mark that opens the
  rendering: 0 when the paragraph opens directly on one (unchanged, existing behaviour),
  or the offset right after a short attribution clause when one precedes it. The
  attribution match (`_ATTRIBUTION_LEAD_RE`) is deliberately blunt — capped at 60
  characters, must end at a colon immediately followed (allowing an italic marker in
  between) by a quotation mark — so a genuine sentence that merely contains a colon
  somewhere in it can never qualify. Guarded by
  `test_a_long_lead_in_sentence_with_an_incidental_colon_does_not_qualify` and
  `test_a_short_attribution_alone_is_not_enough_without_a_quotation_mark`.
- `_closing_mark` now takes a `start` offset instead of always reading from index 0, so it
  finds the closing mark of the quotation wherever it actually begins.
- `_CITATION_TAIL` now accepts an optional italic-close marker and EITHER bracket style
  (`(...)` or `[...]`) — `mukhtasar-ul-asar-1`'s own convention.
- `only_the_rendering` and `split_rendering_from_gloss` both route through
  `quotation_start`/`_closing_mark(text, start)` instead of assuming index 0. Critically,
  the "rendering" that gets folded or split off is always `text[:cut]` — from index 0,
  attribution included — never `text[start:cut]`. The attribution is who speaks the verse,
  not the author's own aside, so it moves into the card WITH the quotation, character for
  character, exactly as the module's existing "nothing is reworded, nothing is deleted"
  guarantee already required for every other shape.

No change was needed in `_book_defect_fixes.py` — `fold_translation_into_card` and
`split_translation_into_card` already just call the (now-extended) detector functions, so
the existing, already-sanctioned repair path picked up the new shape automatically.

`compose_fix.py <slug> --fix --only translation-leads-a-paragraph,translation-outside-card
--allow-composer-open` was then run against every book the survey above found a `fold` or
`split` count on, through the Composer's own recorded-edit path (`record_edit`), which is
the only sanctioned way to mutate `book/book.md` in this repo. Every diff was read before
and after; nothing was reworded, and the six-plus `fused` instances per book were left
untouched, exactly as designed.

Twenty-two existing tests in `tests/test_translation_card.py` still pass unchanged. Five
new tests cover the attribution shape specifically, including the real paragraph from the
screenshot and the two guard cases above.

### Detection
Asif's own eyes on the rendered Compose tab, screenshotted and reported directly — not a
gate, not a test, not a monitor. Nothing in this repo's automated checks would have caught
this on its own, because the check that exists (`compose_fix.py check`) was blind to this
exact shape until this fix. That is the finding this RCA exists to record.

## Action Items

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Read the remaining `translation-fused-with-prose` findings per book (6 in mukhtasar-ul-asar-1, 1 in mukhtasar-ul-asar-2, 2 in surah-al-fateha, 9 in kitab-al-riyad, 7 in spiritual-ethos, 5 in the-master-and-the-disciple) and decide each by hand — the tooling refuses to guess at these by design | Asif | Open |
| 2 | `compose_fix.py check` now also surfaces `honorific-overuse` drift in mukhtasar-ul-asar-2 chapter 9 (3 instances, unrelated to this incident — reintroduced by the same rearticulation pass that was running concurrently with this session) — worth a look, not urgent | Asif | Open |
| 3 | Consider whether `_CITATION_TAIL`'s new square-bracket support should be extended to any OTHER citation-adjacent regex in the corpus that still assumes parens only | whoever touches that code next | Open |

## Lessons Learned

### What went well
- The existing detector/repair architecture (`_book_translation_cards.py` +
  `_book_defect_fixes.py` + `compose_fix.py`, built 2026-08-09) was exactly the right
  shape for this — extending ONE function's entry condition, with no change needed to the
  repair functions at all, because the repair was already generic over "whatever the
  detector calls a rendering."
- The module's own existing test (`test_ordinary_prose_after_a_card_is_not_a_rendering`)
  documented the exact assumption that turned out to be the gap, which made the root
  cause fast to confirm rather than something that had to be rediscovered from scratch.
- The live-corpus guard test (`test_the_live_corpus_splits_the_way_the_repair_assumes`)
  caught nothing broken — the `fused` bucket, which exists specifically to prove the
  repair never goes greedy, stayed populated after the change.

### What went wrong
- A concurrent rearticulation pass was mutating `mukhtasar-ul-asar-1` and
  `mukhtasar-ul-asar-2`'s `book.md` while this session was investigating (confirmed via
  `cost-ledger.jsonl` timestamps and `composer-edits.json` — not this session's own
  action). This was caught by a `git status`/`git stash` check before any write, per this
  repo's own standing practice after the 2026-08-14 incident of the same shape, and did
  not collide with this session's fix — but it is worth naming again as a live risk this
  repo has now hit twice.

### Where we got lucky
- The concurrent rearticulation pass had already finished (no process found running) by
  the time this session ran `compose_fix.py --fix`, so there was no live race — only a
  need to re-read the file after the unrelated change landed.

## Timeline
All times EST, 2026-08-15:

- **Asif reports the defect**, screenshot of the Compose tab showing "AL-FURQAN: 48" with
  no translation in the card.
- **Investigation** traces the exact markdown shape in `book/book.md`, finds
  `_book_translation_cards.py` and `_book_defect_fixes.py` already exist for this defect
  class, and identifies the `opens_on_a_quotation` entry-condition gap.
- **~4:50–5:00 PM** — `git stash`/`git status` surfaces unrelated, substantial concurrent
  changes to both `mukhtasar-ul-asar-1` and `mukhtasar-ul-asar-2`'s `book.md`; traced via
  `cost-ledger.jsonl` to a `rearticulate` pass (steps `rearticulate-03-part-31` through
  `-34`) that finished at 2026-08-15T20:57:36Z — not this session's action, and no longer
  running.
- **~5:05 PM** — Fix implemented in `_book_translation_cards.py`, five new tests added,
  full existing suite (27 tests) passes.
- **~5:07 PM** — Corpus-wide read-only survey run; 13 auto-repairable instances found
  across three books, 30 `fused` instances surfaced for the first time and left alone.
- **~5:08 PM** — `compose_fix.py --fix` run per book through the Composer's sanctioned
  edit-recording path; diffs read and confirmed character-exact aside from the intended
  move.

## Supporting information
- `scripts/podcast/_book_translation_cards.py` — the detector, now covering four
  attribution/citation shapes instead of one.
- `scripts/podcast/_book_defect_fixes.py` — the repair, unchanged.
- `scripts/podcast/compose_fix.py` — the sanctioned check/fix CLI, the Composer's own
  edit-recording path.
- `scripts/podcast/tests/test_translation_card.py` — 27 tests, 5 new.
- `docs/rca/2026-08-14-generate-pdf-and-a-composer-edit-went-missing-together.md` — the
  prior incident of a concurrent-session collision on `book.md` this repo has now seen
  twice.
