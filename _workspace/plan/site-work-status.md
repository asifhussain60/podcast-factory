# Current work - status

**Last updated:** 2026-08-02 evening (the book lane's four silent-failure defects
are closed; every Islamic edition's Arabic is at the current rules; NO PDF has been
re-rendered yet)

**Newest — the Arabic rule reached the other six books, and four defects came out
with it.**

The 2026-08-02 rule (Arabic terms print in Arabic) had only ever been applied to
`degrees-of-excellence`, because the machinery that applies it lived inside a
compose whose earlier stages re-run models over the prose. It is now
`_book_apparatus.apply_book_apparatus`, called both by `compose_book_v2` as its own
tail and standalone by `apply_book_apparatus.py`. Across seven books: 296 doubly
bracketed honorifics gone, 13 retired `(translit, script)` brackets gone, 24
scholarly diacritics gone, Arabic runs 10,685 → 12,332. No model rewrote a line.

Four defects surfaced by diffing every book sentence by sentence. Three share one
root cause — a byte comparison where only a consonantal skeleton is safe, because
the prose's vowelling and the glossary's were written by different passes. The
worst DELETED an author's own English: `(عُبَيْدُ اللَّهِ, 'little servant of Allah')`
became `(عُبَيْدُ اللّٰه)` in a sentence about what the names mean. A fourth, outside
that family: `simplify_transliteration` destroyed single-quoted speech, because a
closing quote and a word-final ayn look identical. All four fixed with tests; every
book restored to its pre-run text and re-derived clean after each fix.

**Open, and deliberately so.** No PDF has been re-rendered — rendering copies each
file to Google Drive, so it waits on Asif. Two hazards are recorded in
`pending-work.yaml`: al-anwaar and asaas declare no `narrative_frame` and any future
model pass will rewrite them into the wrong grammatical person; and the
zero-transliteration rule and the once-per-book annotation policy disagree about a
term's second mention, which is why ayyuhal-walad still prints *mujahadah* bare.

**Earlier — `(2:24)` reaches the page as `(Al-Baqarah: 24)`.**

Asif: "2:24 should be replaced by (Al-Baqarah: 24). This should be done for all
pdfs moving forward." A bare number is a lookup key, not a reference — it asks a
reader who does not read Arabic to already know which surah 2 is.

- **One house form, `(Name: ayah)`**, and every shape collapses onto it. "Quran"
  goes with the number, because once the surah is named it says nothing the name
  does not. A range keeps both ends: `(Ibrahim: 24-26)`. All 23 citations in
  `degrees-of-excellence` renamed; the rendered PDF carries 23 named and zero
  numeric.
- **The rename is readable by its own pipeline**, which is the whole risk.
  `find_citations` reads BOTH forms, so a re-compose still finds the book's 23
  cited verses instead of reporting a book that cites none and quietly ceasing to
  maintain their Arabic. The named pattern is not a general "word: number" — the
  text must BE one of the 114 names, so `(see: 24)` is never scripture.
- The names are the site's own 114, now **pinned to one shared fixture** and
  declared in the audit contract.

**Q 6:149 was never missing — the page break hid it.**

The scan opens the ornate run at the foot of page 192 and finishes it at the head
of 193, with that page's thirteen apparatus notes, the running header and the
folio number between the halves. A perfect four-word quotation scored 0.02 against
its own span and was discarded. Fixed in the tracked OCR ledger — **brackets only,
not one letter moves** — after two attempts in the alignment were measured and
reverted: a span-gap rule recovered 6:149 but cost Q 17:77 its opening two words,
and preferring the fuller search would have printed twelve words of Q 68:43 where
the scan prints seven. **Coverage is 23 of 23.**

**Two things the re-compose surfaced.**

- **The mirror stores some ayat inside a U+200F … U+200E pair**, and each caller
  was responsible for remembering to strip it. Two did; `_book_compose` did not,
  and put both marks into a printed verse. Stripped at the mirror's boundary now,
  so forgetting is no longer possible.
- **The one chapter without a Composer edit drifted.** Every other chapter is
  human-authored and passes through untouched, but "3. Degrees of Excellence" was
  re-articulated: four `I say` became `We say` against the book's own voice, and
  `Abraham (ع)` lost its honorific — an Arabic-retention miss the revoice gate did
  not catch. Restored from the prior text and the deterministic passes re-applied.
  **It will drift again on every compose until it is saved once in the Composer**,
  which is what pins a chapter.

Gates: pytest 2,138 · site tests 364 · smoke 36 clean · lint:views 0 · astro check
0 errors · repo probe 1 pre-existing P3. PDF re-rendered at 91 pages.

**Newest — the book quoted 23 verses and printed the Arabic of two.**

`degrees-of-excellence` shipped 21 of its 23 cited verses as English with a bare
`(5:13)` after them, and the Arabic audit reported `unverified: 0` the whole time.
Every rule in the audit asks whether the script that IS on the page is right; none
asked whether scripture the book QUOTES reached the page at all.

- **`_book_quran.py`, compose step `5a-quran`.** Zero model spend and zero model
  judgment: the EXTENT of a verse comes from the source scan — what the author
  actually printed — and the LETTERS come from the canonical mushaf in
  `content/knowledge-base/mirror.db`. No model is ever asked to recall scripture.
- **22 of 23 cited verses now carry their Arabic**, plus 5 uncited passages where
  two independent signals agreed the scan is quoting a verse. The one left out is
  `6:149`, whose Arabic the scan does not print: filling it from a whole ayah is
  refused rather than guessed, because it would put Arabic on the page saying more
  than the English beside it. It is reported as `uncovered` for Asif's judgment,
  never substituted.
- **Five citations were written wordlessly** — `(5:13)`, not `(Quran 5:13)` — and
  matched no pattern, so those verses were never anchored into the compose prompt
  in the first place. `_book_compose._QURAN_CITE_RE` reads the bare form now,
  gated on the enclosing parentheses AND a colon so a fiscal quarter cannot reach
  it.
- Position in the pipeline is forced from four directions (after every LLM pass
  and the Composer replay, before the glossary overlay, before the audit, before
  the alignment) — the reasoning is written out at the call site.
- New rule `R-QURAN-ARABIC-PRESENT`; `book-challenger` gains **BK-N8** (P1),
  seeded from `quran_coverage` in `_system/book-arabic-audit.json`. It is a P1 for
  human judgment, never an automatic substitution.

**The LIVE Session is retired.**

It was a second surface doing Read mode's job — a reading column over `book.md`
with the companion explanations beside it. Once Read mode gained the same
read-only cards, the same passage tint and the same follow-the-chapter sync
(2026-07-30), the two were one feature maintained twice; the cross-book picker it
also carried is `/studio` itself.

- `live.astro` + `live-session.ts` + `live-session.css` + `live-index.ts` deleted
  (1,750 lines), replaced by a 302 in `live.ts`. A redirect rather than a plain
  deletion for the reason `arabic-review` records: the path otherwise falls
  through to `[step].astro`, which bounces every unknown step to `/edit` — the
  NotebookLM chapter lane, a different text for a different deliverable. 302 and
  not 301, because a permanent redirect is cached indefinitely and this decision
  is one session old.
- **The runtime gate caught the retirement one line short.** `/live` was kept in
  the route manifest with a comment explaining why, and never added to
  `EXPECTED_REDIRECTS` — so smoke failed it as an undeclared redirect, which is
  exactly what that check exists to say. Declared; 36 routes clean.
- **The prev/next chapter row came across in the retired view's vocabulary** and
  had to be redrawn (Asif: "make these buttons look like buttons similar to the
  buttons on top"). It was a transparent 999px capsule; an inch above it the
  toolbar gives every control a card surface, a 6px corner and a raised hairline.
  Same surface, border token, radius, shadow and press now — hover is surface +
  border only, exactly as `.rte-tool:hover` does it. `--cx-control-border` moved
  from the toolbar block to the view ROOT, because the nav is the toolbar's
  sibling and could not inherit it; that hoist is what stops the two drifting
  apart again.

Gates: pytest 2,114 · site tests 363 · smoke 36 clean · lint:views 0 ·
astro check 0 errors · agent-wrapper parity in sync · repo probe 1 pre-existing P3.

**Previous — the English paragraphing is the Arabic's now.**

Asif (2026-07-30): "I want the English paragraphs to mirror the Arabic." A
translation edition's paragraphing belongs to its source, and articulation had been
choosing its own — splitting long Arabic paragraphs for readability and splitting
speech tags off from the speech, so `قال الغلام: …` (one paragraph in the source)
printed as "The boy said:" on a line of its own.

- **696 English paragraphs became 560**, merging 136 back into the Arabic paragraphs
  they came from — 43 of them speech tags. Verified word-for-word: 37,550 words
  before, 37,550 after, identical sequence. The only things that moved are paragraph
  breaks and the 21 continuation quotation marks that became orphans once the
  paragraphs either side of them joined.
- **514 of 534 groups are now exactly 1:1.** The remaining 20 are runs a verse sits
  inside — merging across a blockquote would carry prose over scripture, so the pass
  refuses and the panel honestly says "the 2 paragraphs below".
- `mirror_paragraphs.py`, wired as step 11 of the compose pipeline AFTER the
  alignment (it is driven by the pairing and rewrites that pairing itself, so no
  fingerprint is left naming a paragraph the merge replaced). No model is called —
  the grouping is already known. Idempotent: a second pass merges nothing.
- Refuses rather than guesses: a chapter whose alignment no longer describes its
  prose is left alone, and so is any chapter the human authored in the Composer.

**The Arabic beside the English is the right Arabic now.**

Asif opened the reveal on "The narrator continued:" and got a nine-paragraph block
that plainly did not translate it, half of it unvowelled. Two independent defects,
and the first one was worse than it looked.

- **A repeated speech tag pointed at the wrong Arabic.** The Composer keyed the
  alignment into a `Map` by paragraph fingerprint, and a Map keeps one entry per
  key. This book repeats its speech tags — one fingerprint occurs THIRTEEN times
  against thirteen different source paragraphs — so all thirteen rendered the last
  one's Arabic. 37 paragraphs book-wide were showing text they did not come from,
  with nothing on screen to say so. The alignment file was right the whole time:
  it is written one entry per composed paragraph, verified monotone across all 696.
  Position is the key now, and the fingerprint went back to being the edit guard
  its own comment always claimed it was.
- **One Arabic paragraph, one English block.** Articulation makes several English
  paragraphs from one Arabic one — up to nine — and the source used to be printed
  in full above each of them. They group now: the Arabic appears once, labelled
  "the N paragraphs below", with a rule bracketing the English it produced. The
  paragraphs are not reparented — their DOM order is persisted to
  `visual-layout.json` and moves figures in the printed book.
- **94 bare runs became 7.** The marks-only gate is all-or-nothing per run, so one
  disputed letter cost the vowelling of everything around it — `ويرثله` in the
  scan against the model's `ويرتله`, almost certainly the right word, took ~120
  characters of good marking down with it. `_vowel_recovery` re-asks a refused run
  sentence by sentence and clause by clause under the SAME gate, so only the
  fragment holding the dispute stays bare. The gate did not move by one character:
  every piece is checked, and the reassembly is checked again.
- Both fixes are pinned by tests that fail when the defect is put back — the
  fingerprint collapse returns `9, 2, 9, 6, 9` where the truth is `1, 2, 5, 6, 9`.

- **The last two came from correcting the SCAN** (Asif approved, 2026-07-30). Both
  were single-dot scanner errors the vowelling gate had surfaced by refusing to mark
  the passages around them: `دعوثكم` for `دعوتكم`, and `الجأهم` for `ألجأهم`. They are
  declared in a tracked ledger beside the scan with their evidence, applied by
  `correct_ocr.py`, which keeps the vowelled sibling in step and re-stamps the
  staleness hash — editing the scan alone would have marked a good vowelling stale
  and sent every reader back to bare text. **Zero bare non-Qur'anic runs remain.**
  The one bare run left is a verse the mushaf declines to align word for word, which
  is the documented behaviour: a verse is left exactly as the book prints it.

Still to do: `book.md` was composed from the pre-salvage source, so the PRINTED
edition does not yet carry the recovered marks. A re-compose picks them up.

**Full-system audit: the dashboard was reporting four confident zeros.**

**Newest — the dashboard stopped lying about the project.**

A full audit of the pipeline and the site. Everything deterministic already passed
— 2,360 Python tests, 349 site tests, 180 route renders across five book fixtures
with no console error, ruff, the repo probe, doc links, agent-wrapper parity. What
it found instead was a whole class of defect the gates cannot see: **snapshot fields
that render a zero nobody computed.**

- **"0 books in flight" — for two months.** Both snapshot generators read
  `content/drafts`, a directory the 2026-06-04 restructure deleted. `readdir` threw,
  the catch returned `[]`, and the dashboard reported the empty list as a fact while
  six books sat mid-pipeline, one failed since June. They walk the buckets now, with
  the legacy trees kept as fallbacks in the same order `_paths.py` uses.
- **"56 / 140 steps done" when 117 were.** plan.yaml says "finished" eight different
  ways; the generator passed each through verbatim and every consumer tests
  `=== "complete"`, so 61 finished steps read as unfinished. One closed vocabulary is
  now imposed in the generator — `complete | in_progress | pending | deferred` — not
  in the four pages that were each getting it wrong separately.
- **"Next Step —" always.** The card looked for status `"ready"`, a value no
  generator has emitted and plan.yaml has never contained.
- **"$0 spend" and "0 books published, 0 episodes".** `metrics` and `books_shipped`
  were never written by anything, while the per-book cost ledgers and the published
  shelf sat on disk. Both are computed now; the 30-day window ends at HEAD's commit
  time, not wall clock, so regenerating at an unchanged commit stays a no-op.
- **Both generators still emit byte-identical files**, verified by running them back
  to back and diffing, and five new tests assert the snapshot AGREES WITH THE
  FILESYSTEM rather than merely parsing — each one fails when its defect is put back.
- **Also:** a dead Google-Fonts `@import` (misplaced after `@font-face`, so the
  browser had always dropped it — a network trace confirms nothing leaves for
  fonts.googleapis.com) removed with its build warning; one dead variable; 21 files
  of accumulated prettier drift reformatted, and prettier added to the pre-commit
  hook, since the repo has declared `format:check` since day one and nothing ever ran
  it.

Still open, needing Asif: `claude-code-training` has been `failed` since
2026-06-02; and Lexend + Cinzel are named in three stylesheets but are not
self-hosted, so they have been silently resolving to Inter and Georgia.

**Book Composer Read mode: reads as a page, Arabic set at the English's size,
source numbers dropped, Companion read-only.**

**Newest — Read mode is a reading surface on both sides of the page.**

- **Read mode is a page now**, not a column of text on the site background: the
  chapter body wears the frame the edit shell already wore — card background, 1px
  rule, 10px radius, the shared card shadow — and the 60ch measure is preserved by
  adding the horizontal padding back into `max-width` rather than letting the
  border box eat it. Narrow screens drop the page margins to 1.1rem.
- **The Arabic source reveal is set at the English's size.** 1.05rem/1.9 — the same
  pair `compose-print.css` sets on a Qur'anic quotation, and for the same reason
  (`--q-ar-face` leads with the size-adjusted aliases). It was 1.45rem/2.15, which
  made the source tower over the translation it exists to support. The ع gutter
  control came down with it, and the provenance label — which was set LARGER than
  the prose it annotates — is now apparatus-sized.
- **The paragraph marker is stripped from the served Arabic.** `(٢٩)` opened each
  block only so the parser could find the boundary; the number survives on the
  record and the panel already states it in words, so printing the Arabic-Indic
  original into the middle of the quotation was scan furniture, like the page
  comments dropped beside it.
- **The Companion panel is read-only in Read mode** (Asif, 2026-07-30) — same
  cards, same tint, same follow-the-chapter sync, no rich-text editor mounted in a
  card and no delete button. Expressed as withholding the write callbacks, because
  `renderExplanationCard` already derives editability from `onSave` and its
  read-only render is the one the public reader ships, with CSS written as paired
  selector lists — so the two cannot look different. A Read/Edit flip rebuilds the
  cards, since editability is decided when a card is built.

**Diacritics, and a reversed rule.**

- **A Diacritics button** sits at the end of the Reshape now row, dark until the
  selection is a predominantly-Arabic run that still lacks its marks. One click
  vowels it in place through `POST /api/studio/vowelling` `action: "run"`.
  Verified end to end on a real run: 34 marks added, consonantal skeleton
  byte-identical.
- **The rule that a model may never supply diacritics is reversed** (Asif,
  2026-07-29). He does not read Arabic; an unvowelled run is unreadable to him, so
  the propose-review-accept gate was making the book worse for its reader. Marks
  are applied on the spot now. The skeleton gate STAYS — it refuses letters
  changing under cover of marking, which was never the thing being relaxed — and
  Qur'anic runs are still skipped because the mushaf already vowels them.
- **Flipped, and done (2026-07-30).** The pipeline-side BK-N5 gate was already
  reversed — `_narrative.supplied_diacritics_findings` is deleted and the
  challenger's BK-N5 now seeds from `_vowelling.rejection_reason` — so what this
  entry listed as pending had in fact landed; corrected on sight. What was still
  missing was the vowelling pass itself, which now exists on BOTH sides:
  `vowel_source.py` marks the Arabic SOURCE stream once (so the glossary and every
  later compose inherit it) and `vowel_book.py` remains the net at compose time.
  Backfilled across the library: 62 bare Arabic runs in finished books went to 1,
  and that one is the gate refusing a candidate that moved letters.

**Newest — the Composer's Companion panel now follows the chapter you are reading,
and the page no longer depends on an unrelated panel to boot.**

- **Companion cards are tied to the tinted passages.** A passage scrolling into
  view opens its card and lights it with an accent ring; the passage leaving view
  shuts the card and takes the ring off. Several on screen means several open, in
  reading order. The previous sync scrolled the list without opening anything, so
  arriving at the right card still showed only its title. The sync skips itself
  entirely while the caret is inside the card list — an open card holds a live
  editor and saves on focusout.
- **The floating buttons sit over the bottom of the right panel**, ordered Ismaili
  Scholar, Tools, back-to-top, and the Companion is the surface the page opens on.
  Each surface scroller already reserved `--cx-fab-clear`, so nothing the buttons
  cover is unreachable.
- **The Arabic drawer surface is gone** (term curation + vowelling review). Its
  components and `/api/studio/arabic-review` still exist; nothing mounts them, and
  the three links still pointing at `/studio/<slug>/arabic-review` now land on the
  Composer with no Arabic panel — see the open item below.
- **A page with no Astro island cannot use React in dev.** Removing those two
  `client:only="react"` panels removed the React Fast Refresh preamble Astro only
  emits for pages that hydrate an island, and `book-composer.ts` — which mounts
  every React surface imperatively — died on its first React import, leaving the
  whole page as inert server HTML. `src/scripts/react-refresh-preamble.ts` declares
  that dependency instead of inheriting it. It must stay SYNCHRONOUS: an awaited
  runtime import only suspends its parent, so the sibling module still evaluated
  first and lost the race exactly as before.
- **Open item:** the "Arabic review" / "Phonetic Map" links in `StudioEditor.tsx`,
  `[step].astro` (x2) and `library-view.ts` now lead nowhere useful. Either remove
  them or give those two panels a new home.

**Previous — a full visual-QA pass over all 36 routes, and the gate can no longer
miss a page.**

- **Route coverage was short by four live surfaces.** `/corpus/morphology` (shipped
  that morning) and three of the four `[step].astro` steps — `intake`, `review`,
  `publish` — were never visited by `npm run smoke`; the miss was invisible because
  `[step].astro` redirects an unknown step to `/edit`. Manifest is 36 routes now, and
  `scripts/site-health-routes.test.mjs` fails in BOTH directions: a page with no
  manifest entry, and a manifest entry with no page (which is how the sentinel spec
  went on naming `/studio/<slug>/style` for nine days after the page was deleted).
  The wisdom leaf is gated only where `content/_shared/wisdom-corpus/` exists.
- **`site-health-shots.mjs --full false`** captures the viewport instead of the page.
  The LIVE reader's full-page PNG is ~105,000px tall; scaled to fit, nothing in it
  can be judged.
- **Five defects fixed**, each measured, fixed at the smallest in-pattern point, and
  re-shot before being called done:
  - Companion cards clipped 871px of an open explanation and the list never scrolled
    — `.xpl` has `overflow: hidden`, which zeroes its flex minimum size, so the CARD
    shrank and the scroller measured no overflow (`flex-shrink: 0`, companion-card.css).
  - Composer FAB row covered four panel controls when the drawer was open
    (`--cx-drawer-w` hoisted to body and added to the offset, book-composer.css).
  - "Tell the AI" clipped its own placeholder by 23px (`min-height` 5rem → 6.5rem).
  - Wisdom empty-state icon sat flush left under centred text — the Icon is a
    `display: block` svg (`margin-inline: auto`, wisdom.css).
  - Editorial asides rendered as scripture display type — 27.8px/52.9px centred
    against 20px/31px body. `markdown.ts` now emits `blockquote.aside`, and the two
    screen rules take `:not(.aside)`; verses keep the exact treatment they had.
    Screen only — `book-print.css` scopes Arabic to `blockquote.quran p.ar` and
    never had the bug.
- **`> >` in composed books**: `_book_augment.format_editorial_block` strips
  model-written blockquote markers before adding its own, and BOTH markdown
  renderers flatten a nested marker, so the five notes already in
  `the-master-and-the-disciple` read correctly without a re-compose.
- **Judged NOT defects** (checked, not assumed): the mobile nav is a deliberate
  scrolling tab strip (`overflow-x: auto`, 32px hidden, not a clip); dark theme is
  not a supported state (`theme.css` declares no dark palette); sr-only labels,
  `text-overflow: ellipsis` truncation, and volume titles inside a collapsed
  `<details>` all read as "clipped" to a naive probe and are not.
- Gates: smoke 36 clean · site tests 331 · pytest 2,303 · lint:views + astro check
  0 errors. A DOM probe across all 36 routes at 1440px and 390px found zero
  horizontal page overflow and zero broken images.
- **Open for Asif:** nothing blocking. The `.mjs` print renderer deliberately does
  NOT emit the aside class (the print CSS has no rule keyed on it); revisit only if
  a print rule ever needs to tell asides apart.

---

**Prior — the Scholar Companion is a synced, one-button, title-only card rail.**

- ONE Explain button: probes the live prose selection first (explains + files a
  Companion note, tints the passage), falls back to the typed concept. The
  "From selection" ghost button is retired (`GemCompanionPanel.tsx`,
  `gem-companion.css`).
- Cards: collapsed = TITLE-ONLY rows in chapter order; whole card is the expand
  target; ONE card (and one etymology accordion) open at a time
  (`explanation-card.ts`, `companion-card.css`).
- Scroll sync both directions: scrolling the chapter drives the panel (capture
  scroll listener + visible-mark sweep in `book-composer.ts` — mode-blind, works
  over read spans AND editor decorations; scroll events/rAF do NOT fire in
  hidden tabs, so verify in a rendering Playwright page); clicking a card
  reveals its passage (revealPassage now targets the visible tint twin — it was
  a silent no-op in Edit mode).
- Deletes (card + etymology entry) go through `confirmDialog` (danger, Cancel
  default) — shipped alongside RCA
  `docs/rca/2026-07-28-automation-deleted-companion-notes.md`: an automated QA
  pass deleted two real chapter-3 notes via the then-unguarded one-click
  delete. Both restored (one from git, one regenerated as `5de6a25d`).
  `site-health-sentinel` spec now hard-forbids operating destructive controls
  in the browser; STANDING RULE (Asif-approved): commit
  `content/*/_system/companion-notes/` at session end and before launching
  browser-QA agents.
- Gates: astro check 0 / lint:views clean / site tests green / smoke 32 clean;
  html-view-challenger PASS twice (advisory: REQ-050 reduced-motion on three
  smooth-scroll call sites, in-pattern); sentinel round re-ran post-RCA.

---

**Prior — the morphology layer is surfaced everywhere (commit 4aa8928).**

- `/corpus/morphology` — new root-first explorer under the Corpus domain
  (nav: Corpus -> Morphology): all 1,642 roots, both-script client-side search
  in the shared fold space (`src/lib/arabic-fold.ts`, fixture-pinned TS mirror
  at `plan-dashboard/scripts/lib/buckwalter.fixtures.json`), per-root family +
  POS + verse peeks (mirror.db) + Lane's meaning, coverage strip with the 313
  meaning gaps listed. Data via `src/lib/db/morphology.server.ts` (per-call
  readonly opens over the committed morphology.db/lexicon.jsonl; degrades to
  an empty state, never crashes).
- Etymology cards (Composer + live reader) are now VERIFIED CORE + persona
  note: companion-notes GET/POST and live.astro attach computed (never
  persisted) `morphology` per etymology row; explanation-card renders the
  corpus block (.xpl-morph) above the persona textarea. gem-explain grounds +
  vetoes generation; api/ai/etymology grounds from local DBs. Python parity:
  `_book_companion.gate_card` vetoes against `load_morphology_reference`.
- Gates: smoke 32 clean; lint:views + astro check 0 errors; site tests 327;
  pytest 2,307. html-view-challenger PASS-WITH-CAUTION (7 CSS fixes applied);
  site-health-sentinel PASS (bdi root line; mirror translation markup stripped).
- Open advisories for Asif (non-blocking): REQ-070 source dates on the
  attribution footer; REQ-004 tool-page deviation note (no numbered sections,
  matches /corpus); .xpl-morph-chip location is title-only (keyboard/touch
  inaccessible, supplementary info).

---

**Prior — the Composer's toolbar is now `@asifhussain/prose-editor`.**
A self-contained npm workspace at `plan-dashboard/packages/prose-editor/`,
framework-free core plus a React wrapper plus a standalone IIFE for hosts with no
bundler. Its defining guarantee is that nothing typable can be lost on save:
every node and mark in the schema must declare how it serializes, enforced at
compile time by a branded type and at runtime by a coverage assertion against the
FINAL schema. The Composer binds it with `attach()`, handing over `docToMarkdown`
unchanged — so adoption changed nothing about what a save writes.

*What the toolbar gained.* Thirteen controls where there were five: undo/redo, a
Body/Section/Subsection format dropdown, bold, italic, inline code, link, bullet
and numbered lists, quote, a Quranic-quotation button registered through the
package's extension point, divider, clear formatting. Plus a selection bubble, a
keyboard-shortcut registry that throws on a duplicate binding, and an allow-list
paste sanitizer that replaces the deny-list-over-a-string approach.

*Four things a keystroke could lose, closed first.* Ordered lists were renumbered
from 1 on every save, destroying the stated ordinals `renderMarkdown` carries as
`value=`. Shift+Enter fused the words either side of it. Underline and Mod-U
discarded silently. And TipTap's `autolink` defaulted on, so typing a bare domain
put a link into `book.md` that nobody authored. All four are now schema-level
impossibilities rather than serializer omissions.

*Two gates were weaker than their green output suggested.* The runtime smoke check
FOLLOWS redirects, so a route that 302s away was reported clean — which is exactly
how a broken `/studio/<slug>/compose` (an unresolvable CSS import, caused by a Vite
string alias matching by prefix) passed. It now compares the landed path with the
one asked for, with legitimate redirects declared per route, and was proven to
catch the original defect. Separately, the view linter's CSS scan cannot see a
single-line rule at all — found while proving the linter reached `packages/`, and
spawned as its own task.

*Known and not mine to fix here.* Round-tripping every chapter of all four books
shows the seed/serialize pair is not byte-exact on real content — multi-line quotes
get joined, and an asterisk used as an ayah separator loses its spacing. Identical
before and after this work (5/0/1/7 chapters), so pre-existing; spawned separately.


**Newest — the audit pass, and the two things it found that a human would have seen.**
`repo-surgeon` (report-only, because a visual-QA agent was writing the same tree)
plus `site-health-sentinel`. No P0. Both agents found that this session's work had
stopped one renderer short, twice, and in both cases the missing renderer was the
one a human actually looks at.

*Lists.* Turning on real list rendering changed `renderMarkdown`, not just its
source profile — and there are FOUR renderers of the same markdown. Two were
fixed, two were not: the reader at `/studio/<slug>/live` (`.bookv-body`) had no
list CSS at all, and `renderMd` — the PDF renderer — had no ordered-list parser
at all, so the next PDF render would have printed the one real enumeration in the
corpus as a run-together paragraph with "1." "2." as literal text. That is faked
numbering in the publication deliverable. `renderMd` now parses ordered lists in
every render (bullets stay self-study-only; no `book.md` uses them) and carries
the source ordinal as `value="N"`, pinned by a cross-renderer test asserting the
print and reader numbering agree on four fixtures.

*The marker-CSS reset has now needed the same fix in FIVE hosts* —
`.src-view-prose`, `.se-prose`, `.cx-podcast-body`, `.bookv-body`, `.cx-body` —
and each was found only after the previous one was repaired. The runtime smoke
check (INV-3) was listing only the hosts already fixed, so it could confirm the
fix and never find the next instance; widened, it immediately reported `.cx-body`.
REQ-015 itself said nothing about `list-style-type`, so the rule as written
reproduced the defect — the standard and its digest now say so, and name the
runtime gate as the enforcement.

*Fences.* Recorded here for the first time: `MACHINE_FENCE_KINDS` in
`book-html.mjs` fixed the print renderer's skip list (it had three of the four
kinds and missed `edition-intro`), `fence-decos.ts` decorates the marker in the
edit canvas instead of removing it (the text is load-bearing —
`preserveFences` reads it back), and `markdown.ts` now skips fence lines in
display renders while the EDIT seed opts back in via `keepMachineFences`. That
last one removed 16 visible grey `editorial:begin` chips from the reader. The
fence-kind contract is now pinned in both directions and registered in
`.repo-audit/profile.yaml`: JS↔TS by a live `deepEqual`, and — the gap the JS pin
structurally cannot see — Python↔TS by a scan of what the producers actually
write. Comparing the two renderer lists to each other stays green when both are
wrong together, which is exactly how the `edition-intro` bug shipped.

*Also fixed:* the lane switch's reload-restore path could never fire —
`location.reload()` queues a navigation rather than halting the task, so the
clear after `leave()` deleted the stash before the reload read it, and a user who
pressed Podcast landed back in the editor. Plus a bounded heading read (336 KB →
40 KB per compose render), two softened test assertions that would have redded on
legacy content rather than on a defect, and one incorrect CSS comment of mine.

*Reported, not fixed:* the Wisdom section is dead two ways —
`source-extractor.ts:21` points at a directory that does not exist, and the Urdu
`raw-extract.md` it wants has never been tracked; `$RefreshSig$` throws on the
Composer route for a book with no composed `book/` (dev-only); fenced code blocks
render their ``` markers as text; `.bilingual-grid` never collapses at mobile.

---

**Composer lane switch + shared list pass (earlier the same day)**

**Real enumerations now render as real lists (superseded above: it was FOUR renderers, not three).**
The read-only source renderer ran with `lists: false`, so a numbered list in a
chapter source rendered as one run-together paragraph with the numbering as
literal text. Asif authorised the shared pass. Flipping the flag ALONE would
have been worse than leaving it off, and the investigation is the point: a blank
line used to flush the list, so a loose `1. / 2. / 3.` — the dominant style in
this corpus — became three separate `<ol>`s that each restarted at 1, and the
ordinal came from the `<ol>` counter, so a list starting at 3 renumbered itself
to 1. Both are the faked numbering REQ-015 forbids. Fixed at root first: ordered
items carry `<li value="N">` reproducing whatever the source states, and a blank
line keeps the list open when the next content is an item of the same kind.

Then a defect only the pixels showed: with padding and `list-style-position` set
but not `list-style-type`, Tailwind's preflight (`list-style: none` on every
ol/ul) left a numbered list with NO NUMBERS — the enumeration gone entirely,
worse than the paragraph it replaced. The DOM read as correct throughout. The
CSS now restores `decimal`/`disc`/`circle` alongside the REQ-015 indentation,
using logical properties so an RTL panel indents from the correct side.

Blast radius, measured rather than assumed: 88 of 170 source files now render
real lists, across THREE surfaces — the chapter/file viewer, the Composer's new
podcast lane, and the Urdu bilingual wisdom view (`bilingual-sections.ts`, which
the original recommendation had not accounted for). Zero numbering mismatches
against the corpus. 13 new renderer tests; 3 of 5 mutants killed and the other
two shown to be behaviourally equivalent rather than coverage gaps. **Not
verified: the Urdu bilingual view** — `/wisdom` exposes no reachable book page,
so the RTL path rests on logical properties by construction, not observation.
Known cosmetic case: a page marker like `- 87` alone on a line in a raw-extract
file now renders as a one-item bullet.

---

**The Composer can now show the podcast source, read-only.**
The Book Composer at `/studio/<slug>/compose` gained a lane switch: "Reading
edition" (book.md, editable — unchanged) vs "Podcast source" (`chapters/*.txt`,
read-only). The original ask was for the same edit to apply to BOTH lanes; that
turned out to be unimplementable and was replaced, with Asif's own agreement in
the handoff, by a read-only flip. Re-verified against the code this session: the
two lanes are independently translated (identical source passage, different
English), independently segmented (9 book chapters vs 20 podcast chapters, no
title correspondence), and the podcast lane deliberately carries narration
framing, teaching commentary and attributed citations (22 of them; book.md has
0) that mirroring would delete. 20 audio episodes already exist from the current
chapter text.

The read-only guarantee is structural, not intentional. `compose-lane.ts` owns
the flip ORDER: it awaits the Composer's own `leaveEditMode` (flush the
debounced autosave, then destroy the TipTap editor) before any pane swap, so an
edit typed a moment before the flip lands in book.md and nothing editable
survives behind the toggle; a declined leave aborts the flip. The podcast body
is a host of its own, never the chapter body the editor seeds from — re-seeding
one shared surface is what would write podcast prose into book.md AND freeze
that chapter in `composer-edits.json` (RCA-001, with prose from the wrong lane).
Flips are serialized so a double-click cannot flush twice. Bodies are fetched on
demand through the read-only `/api/library/file` route and rendered by
`renderSourceMarkdown`, the same path `studio/<slug>/view.astro` uses, so the
lane reads like the existing chapter viewer; the podcast picker is drawn by
`enhanceSelect` like the book picker rather than left as an OS dropdown.

Test harness: 15 node:test cases in `compose-lane.test.ts` driving the REAL
TipTap editor and REAL autosave against a recording transport (only the network
is stubbed), plus 5 content-invariant pytest gates in
`test_compose_lanes_distinct.py` whose content root is env-overridable so they
can be falsified without touching `content/`. All 15 mutants killed — including
"skip the flush", "make the host editable", "bypass leaveEditMode", "mirror book
prose over a chapter source" and "leak an attributed citation into book.md". Two
mutants exposed real gaps that were then closed (an unserialized flip; an
untested picker sync). 12/12 repo-contract gates green before and after;
`content/` byte-identical throughout. Phase 2 (extending
`/api/studio/replace` across both lanes) is NOT built — it needs Asif's separate
approval per the handoff.

---

**RCA-001: the composer-snapshot freeze, found, root-caused, recovered.**
Asif reported "original bad English" in the compose tab; forensics showed 8 of
9 chapters were byte-frozen at their 2026-07-20 pre-articulation Composer
snapshots — the 07-21 compose articulated all 9 chapters and its own replay
discarded 8 in the same run. Standing RCA practice established (docs/rca/ —
SRE postmortem format; RCA-001 written and Resolved). Recovery: human deltas
extracted first, stale sidecar archived, full fresh compose (base + fluency,
9/9 de-calqued, 0 reverted), punchlist re-applied (green-ears proved correct
from source; name glosses + bridges re-applied), then book-challenger
convergence in 3 iterations — 4 P0 / 7 P1 / 3 P2 found-and-fixed (seam
double-telling, one-name-for-the-teacher restored per the locked ruling,
Quran tokens vs canonical mushaf, the العالِم/العالَم garble) — final verdict
SHIP-READY. Six chapters now carry Composer edits whose bodies are the
ARTICULATED text. Pipeline hardening: enumeration gate refined (section
numbering is apparatus — run-shape rule), integrity-retry now names actual
findings, augment notes are "(tradition-grounded)" with an honest-provenance
prompt rule. Composer save-guard (AI-3) shipped from a task chip; AI-2
(articulation-survival reporting) still in its chip session; AI-6 (no-headings
prompt strengthening — must ride with a planned recompose) and AI-7
(enumeration-gate watch) open in the RCA. Advisory P2s for a future apparatus
pass: intro diacritic register, front-matter basmala, two ch5 Arabic slab
openings.

---

## Previous sessions

**Last updated:** 2026-07-27 evening (Rearticulate ships; the flattened chapter is restored)

**Newest — the Rearticulate action, and the contract behind it.**

*A Composer Rewrite had flattened one chapter.* A "clarify" rewrite (Gemini,
generic-editor prompt) had rewritten the boy's opening speech in chapter 3 of
`the-master-and-the-disciple` from 183 words to 139 — imagery abstracted away
("struck the mark" → "effectively"), plus a stray "Sheikh" against the book's
24 "Shaykh". Sat uncommitted; verified against the pipeline's translation
chunks (paragraph-level sweep, all 8 chapters — only ch. 3 was flattened);
restored via git. The companion note added the same day was genuine enrichment
and was kept.

*Shipped in response — the Rearticulate lane:*
- `docs/standards/book-articulation.md` (REQ-BA-010..120) + the
  `book-articulation` skill — the articulation contract (LAL-handbook-grounded:
  simple lucid English, grammar may be rebuilt, meaning/speeches/quotes/imagery/
  Arabic are inviolable).
- `scripts/podcast/rearticulate_chapter.py` — chapter-scoped engine reusing the
  fluency pass's `_run_pass` (windowing, revoice_gates, per-window revert);
  addresses chapters by `anchor_key`, records results in `composer-edits.json`
  like a human save, writes `_system/rearticulate-status.json` (gitignored).
- `POST/GET /api/studio/rearticulate` — detached spawn + poll, single-run lock,
  dead-worker detection.
- Composer Refinement tab: **Rearticulate chapter** button — whole-chapter,
  selection-independent; flushes autosave, locks the editor read-only, shimmers
  (`.cx-rearticulating`, reduced-motion safe), reloads via
  `reloadPreservingChapter()` on success. No live-editor surgery (RCA-002).
- `book-rearticulator` agent (canonical infra/claude-agents/ + synced wrapper) —
  judges results against REQ-BA-*; convergence action is revert, never
  re-prompt-until-pass.
- The Refine panel's Rewrite modes now carry the REQ-BA register/imagery/
  spelling guards, so the original flattening path is constrained too.
- Composer header: **Generate PDF** button beside LIVE Session (flush autosave
  → themed confirm → /api/studio/generate-book-pdf; spinner while rendering,
  reduced-motion safe) and a persistent **Download PDF** link — pre-filled
  server-side from the newest book/*.pdf on load, refreshed with size after
  each render, served via /api/library/file with a download filename.

**Previous — RCA-002, then durable view state across the site.**

*The session opened by finding corruption, not by writing code.* Two Book
Composer autosaves from the previous evening sat uncommitted in the working
tree, and everything in that eighteen-hour delta was damage: the edition
introduction of `the-master-and-the-disciple` stacked THREE times (fence count
1 → 3 in both `book.md` and the sidecar), "The Master here **is is** a teacher
figure", a clause transposed into "grown dear to your fellowship and us has
become sweet to us", and a nested editorial-note blockquote collapsed from ten
lines to one so its inner `>` would render as literal text. No authored content
anywhere in the diff. Dev server stopped first so its autosave could not race
the restore, evidence captured, both files restored, clean tree verified.
Written up as [RCA-002](../../docs/rca/2026-07-27-composer-autosave-wrote-corruption-into-book-md.md)
— the second incident in RCA-001's class, because RCA-001's fixes all pointed
downstream at what the PIPELINE does with a Composer edit and never constrained
what a Composer SAVE may write. Checked and KEPT: the vowelling change swept
into the CSS commit `bff3680` is a correctly-applied entry from the approved
review ledger. Only the commit hygiene was wrong there, not the content.

*The root cause, fixed (AI-1).* `createAutosave` gained an optional
`fingerprint`. It captures the serialized content once at construction and
skips any save that still matches — no `save()` call, no request, no write.
`markDirty()` is wired to the editor's `update` event, which fires for things
that are not edits, so before this a stray keystroke or a pointer-drag that
landed where it started rewrote the whole chapter; and because the markdown
round trip is not byte-exact on real content, reflow of paragraphs nobody
touched went with it. Fingerprinting the SERIALIZED output rather than diffing
against disk is what makes that second case safe — drift sits in both the
baseline and the current value, so it cancels and never reaches disk alone.
Proven in a real browser with the save endpoint stubbed: typing then undoing
inside the debounce window produced ZERO PUTs and settled the pill back to its
previous "Saved 9:36 AM" rather than a new timestamp, while a real edit still
saved and its undo saved the revert. Both Composer autosaves (prose + figure
layout) now carry it. 10 unit tests.

*Then the actual ask: the site remembers where you were.* The app already
persisted PREFERENCES (font, size, paper, zoom, panel width) and always had.
SELECTIONS mostly did not — and where they did it was a one-shot
`sessionStorage` handoff written just before a scripted reload and deleted on
read, so the editor's own refresh kept your place while a plain F5, a new tab,
or the next morning lost it. New `src/lib/view-state.ts` is the one home for
the second kind: storage access guarded (a blocked store degrades to "opens at
its default"), keys namespaced by surface AND book slug so one book's chapter
can never restore into another, every read validated by the caller so a
chapter a re-compose renamed is discarded rather than leaving a blank page, and
a registry that THROWS on a duplicate surface+field instead of letting two
surfaces quietly share a key. `use-view-state.ts` binds it to React and
deliberately does not seed from storage in the useState initializer — several
islands are `client:load`, and a first-render read would trip a hydration
mismatch.

*What now survives a reload:* the Composer's selected chapter, its Read/Edit
mode, its lane (Reading edition ⇄ Podcast source) and the selected podcast
source file; the pre-upload review tab; Edit & Enrich's inspector tab; and the
LIVE Session reading position (throttled to one write a second, restored after
fonts load, re-running the scroll-spy on landing so you are not told you are in
chapter one while sitting in chapter three). The three one-shot keys
(`cx-restore-chapter`, `cx-restore-edit`, `cx-restore-lane:<slug>`) are GONE
rather than left beside the new mechanism — one path, nothing to drift.
Restoring straight into the editor is only safe because of AI-1 above; without
that guard it would arm an editor over `book.md` on every page load.

*Verified in the browser, not assumed:* chapter and mode restored across a real
reload; a stale chapter key falls back to chapter one and still renders; with
every `pf:` key cleared the original defaults return; the LIVE scroll throttle
holds a value for a second then advances; the pre-upload tab reopens where it
was left. `content/` byte-identical throughout, confirmed by git rather than by
a checksum (an unsorted `find` briefly suggested otherwise — git is the
authority). Gates: astro check 0 errors, npm test 317 (315 pass / 2 pre-existing
skips), lint:views clean, eslint 0 errors, prettier clean, smoke 32/32.

*Known harness limits, not defects:* the in-app browser pane does not dispatch
scroll events for `window.scrollTo` and its hidden viewport reports
`innerHeight: 0`, so the LIVE scroll listener was exercised by dispatching the
same `scroll` event the pre-existing `updateActive` handler already depends on,
and pixel-level layout readings from that pane are unreliable.

*Still open from RCA-002:* AI-2 (reproduce and fix the `edition-intro`
tripling), AI-3 (a pre-commit gate refusing a `plan-dashboard/` commit while
`content/` is dirty), AI-4 (make the known round-trip losses fixed or blocking
rather than recorded), AI-5 (session hygiene for a dev server left running).

**Then — the etymology accordion opens one at a time and shows all of itself.**
Asif's ask on the Companion card: no scrollbar inside an expanded entry, and
only one entry open at a time. Both done. The interesting part is what the
conformance gate found in the FIRST version, which looked right and was not:
removing the inner scrollbar and the resize grip took away both escape hatches
from a measurement that goes stale, and in two ordinary situations it did.
Pressing the panel TEXT dial with an entry open reflowed the text to 333px
inside a field still pinned at 173px — 160px of the explanation unreachable,
a WCAG 1.4.4 failure. And a window resize while the card was COLLAPSED measured
a `display:none` field, read `scrollHeight` 0, and wrote a 2px height that
survived into the next expand.

The fix changes WHEN the measurement runs rather than patching each case:
`autoSizeEntry` refuses to measure a hidden field (`offsetParent === null`),
the card's `setOpen(true)` re-measures at the first visible moment, a
width-guarded `ResizeObserver` on `.xpl-etym` replaces the window listener (the
callback's own work changes the container's HEIGHT, so reacting to height would
loop), and `panel-text-size.ts` now exports `PANEL_TEXT_SIZE_EVENT` and
dispatches it from `broadcast()`. That last one is the class fix, not the
instance: the stepper is shared by every panel, so the next surface that
measures its own text gets the notification for free. Height moved to a
`--ety-h` custom property, matching `--pv-zoom` / `--panel-fs` / `--cx-w`
rather than assigning a concrete `height` — the only place in the codebase
that did.

`html-view-challenger` re-audited and passed at Level 1, and its own re-run was
sharper than mine: my collapse-then-resize case went 1440→1100, which does not
move the drawer on this layout, so it would have passed even had the fix been
broken. Its widths (1440→900, 900→390), a dial change while collapsed, and a
six-change resize storm all came back clean with no observer-loop warning.

*Also fixed here:* the LIVE scroll restore was recording its own jump —
`restoreReadingPosition` runs before the listeners are wired but DEFERS into
`document.fonts.ready`, by which time they are attached. Mostly it rewrote the
same number; the case that bites is a position saved on a phone, where the
column is more than twice as tall, which a desktop then clamps to the bottom
AND persists, destroying the phone position. Found by `site-health-sentinel`.

*And a two-byte fix worth recording:* `explanation-card.ts` carried two literal
NUL bytes as a `.join()` separator, which made the file register as BINARY —
`grep` silently returned nothing for it, which is what made the accordion hard
to find at all. Now the `\0` escape: identical to the compiler, text again to
every tool. Worth knowing because parts of this repo's own gates are grep-based.

*Known and NOT taken up* (challenger SHOULDs, carried forward): the accordion's
ARIA is correct but incomplete — no `aria-controls`/`id` on the body, no heading
wrapper per term, the field labelled "Etymology entry N" rather than by its
term, no arrow-key movement between headers, and the single-select collapse is
unannounced. The Composer also prints the term twice (header + first words of
the field) because `etymologyDetail` strips it for the reader only. Two
governance items: `book-composer.css:1771` claims the `--panel-fs` exception is
recorded in `html-view-lint.config.json` and it is not, and `lint:views`
classifies only `.astro`/`.tsx` as code, so SVG built as a string in a `.ts`
file is invisible to the gate.

---
**Composer articulation save guard (RCA-001 AI-3), shipped and
challenger-gated (Level 1).** The Book Composer now warns before a save would
freeze a chapter whose current prose never passed the articulation (fluency)
pass — the exact failure that froze 8 calqued chapters on 2026-07-20. Server
side: `lib/reader/articulation.ts` (pure, 6 unit tests) reads
`_system/book-fluency-report.json` and maps at-risk chapter keys to
plain-language reasons (`adapted` safe; `partial`/`reverted`/`skipped` warn;
`composer-edit` judged by `superseded_status`; unknown chapters warn; no
report = contract doesn't apply, no warnings). Client side: a red advisory
banner tops the edit shell on at-risk chapters, and the FIRST autosave of such
a chapter raises a confirm ("Freeze un-articulated machine text?" — Save
anyway / Don't save, danger variant). Confirm-once-per-chapter-per-session
(sessionStorage, survives autosave reloads); a decline parks the autosave in
its error state and the pill's Retry re-asks. Advisory only — a deliberate
save always proceeds. Verified live in the browser on all three states.
Also fixed in passing: a broken comment in book-composer.css was silently
discarding the `.cx-body .ar-inline, .cx-prose .ar-raw` font rule (inline
Arabic in the Composer rendered in the wrong face).

**Newest — a full Composer UX session, all shipped and challenger-gated.**
(1) Chapter dropdown fixed — option mousedown moved focus to the skip-link
target, whose focusout closed the list before the click committed; standard
combobox preventDefault, guarded to option rows (select-menu.ts). (2) The
candidate palette now filters by chapter — slide-deck anchors quote the deck
NARRATION, so the producer resolves and stamps an explicit `chapter` into
visuals/index.json at emit (`resolve_candidate_chapter` in
_visual_candidates.py, heading rung via the pinned anchor_key); composer.ts
prefers the stamp; this book backfilled 27/29. (3) Palette gestures: CLICK
opens a self-sizing lightbox (image-lightbox.ts, shared modal contract), DRAG
is the ONLY placement path (per-paragraph drop marker); hover-preview deleted.
(4) Actions always visible in their own column (no hover-reveal, no caption
overlap), accent borders >=3:1, shadows; drag ghost, marker pulse, one-shot
arrival flash — all motion behind prefers-reduced-motion. Edit icon is ✏️.
(5) Inspector restructure (Asif-approved plan): tabs are [Artifacts, Refine &
Notes] (Details merged in, detected-citations list included); citation style +
typography moved VERBATIM into a Book-settings dialog behind a tab-bar gear —
forms keep their bindings, saves verified end-to-end. (6) Book content:
Tur/Bayt al-Mamur glossed per Asif ("the Mount"/"the Frequented House", NOT
"House of Light"), plus 4 name-gloss composer edits (Salih 'the righteous',
the Ubayd Allah name-riddle, Abu Salih, Abu al-Khair); 6 chapters now carry
durable composer edits. Gates every ship: astro check, lint:views, npm test
59, smoke 32/32, pytest 1751 (+4 new), html-view-challenger. Standing
advisory: placement is drag-only (no keyboard path) — accepted by design.

**Last updated:** 2026-07-22 9:55 AM EST (annotation policy applied; book SHIP-READY, zero open findings)

**Newest — the annotation policy is live and the book converged to SHIP-READY
with zero open findings.** Asif's rule ("annotations once and intelligently;
commonly-known terms speak English") shipped as the four-class policy
(`_annotation_policy.py` + class-aware `_book_inline_arabic.py`): one model
call classified all 74 glossary terms (22 teach / 23 familiar / 15 name / 14
silent), reviewable + durable in `glossary.yml`; annotations are DERIVED state
(fold back, re-derive), taking the-master-and-the-disciple from 65
parentheticals to 30 — vocabulary now introduced as `(bab, باب)`, cast named
with script at true first mention, familiar terms plain. The final challenger
sweep also caught and fixed a REAL P1 every prior review had inherited: line
567 read the adjective الخضر ("green ears") as the person al-Khidr — corrected
through the Composer path (3 chapters now carry durable composer edits) and
upstream in refined-english.md. Sidecars restamped clean (57 runs, 0
unverified); three sweeps ran today, final verdict SHIP-READY. Gates: pytest
1754, npm test 59, tsc clean, lint:views 0, smoke 32/32, ruff clean.

**Last updated:** 2026-07-22 8:27 AM EST (introduction is apparatus, not a chapter)

**Newest — the fenced edition introduction can no longer be edited as a
chapter.** Its `## Introduction` heading lives inside the `edition-intro` span,
so the Composer offered it as an editable chapter whose edit was orphaned on
every compose — and a save through the editor stripped the unknown markers,
after which `strip_introduction` stopped matching and composes stacked a second
introduction. `edition-intro` joined `FENCE_KINDS` (round-trip survival), the
Composer's chapter enumeration skips headings inside the span, and
`writeChapterBody` refuses a key resolving into it. Dormant on
the-master-and-the-disciple (hand-split front matter, still editable by
design); live for the next book whose preface is excluded. Commit `c1f5146`.

**Last updated:** 2026-07-21 5:46 PM EST (Composer authority + honorifics)

**Newest — a Composer-authored chapter is no longer regenerated, and the
conflict warning finally means something.** Every model stage of
`compose_book_v2` (base compose, fluency, augment, re-voice) consults
`_book_edits.edited_chapter_keys` and passes an authored chapter through
untouched; `--force` still re-composes and warns first. The conflict signal was
structurally false — the Composer hashed the live `book.md` (introduction and
bridges included) while replay hashed the composed body from before either is
injected — so the pipeline now stamps `_system/composer-base.json` and the
Composer quotes that value back as `base_fingerprint`. The TS hash is deleted;
`anchor_key`/`anchorKey` is the only remaining mirror pair. New deterministic
pass `_honorifics.py` spells out the first honorific in the book and abbreviates
the rest. Eight audit findings closed alongside, including a seam de-dup that
deleted paragraphs with no record, a sidecar that discarded every prior edit on
a parse failure, and a superseded whole-book composer that clobbered `book.md`
when run. Site-side: `npm test` now reaches `src/` via a 40-line resolve hook
(`scripts/lib/ts-resolve-hook.mjs`, no new dependency), starting with
`book-md-write.ts` — the sole writer into `book.md`, previously untested.
Gates: pytest 1734, npm test 55, tsc clean, lint:views 0, eslint 0 errors,
smoke 32/32, ruff clean. Commit `0b52991`.

**Last updated:** 2026-07-19 8:20 AM EST (Supplications lane — PDF-only sibling)

**Newest — the Supplications category shipped as a standalone PDF-only lane.**
A fourth content bucket (`Supplications`) plus profile `islamic_supplication`
now produce a facing-column reading PDF (English left, Arabic/Urdu right) with
no episodes, audio, slides, or video. Built as a SIBLING of the podcast
pipeline, not a branch inside it: the ship gate hard-requires paired
`episodes/`, so the lane has its own driver (`scripts/podcast/supplication/`),
its own state file (`_system/supplication-state.json`), its own gates, its own
renderer (`render-supplication-pdf.mjs`), and its own stylesheet
(`supplication-print.css`). Every firewall file — orchestrator, `_progress`,
episode/ship gates, translation-edition composer, `book-print.css`,
`render-book-pdf.mjs`, `_augment_registry` — is byte-untouched, and an existing
Islamic book's PDF re-renders byte-identically (modulo PDF timestamps).
Site-side: four TS mirrors updated in one commit (`content-paths`, `live-index`,
the exhaustive `SHELF_META`, `PROFILE_TO_BUCKET`) plus a shelf accent; new shelf
renders with zero console errors. Integrity design: a unit's source text is
NEVER model-authored — models emit only line groupings and English, and Python
re-derives source from the immutable OCR record, so the verbatim guarantee is
structural. OCR diacritic fidelity was validated on a real vocalised Arabic scan
before building (1,435 tashkeel marks recovered, 1 invalid token in 968).
Gates: pytest 1642, astro 0 errors, lint:views 0, smoke 33/33, eslint 0 errors.

**Last updated:** 2026-07-18 2:20 PM EST (R2 hooks pass COMPLETE + audit fixes)

**Newest — all nine StudioEditor hooks extracted; post-chain audit clean.**
Hooks 4-9 landed one-per-commit (useStageApproval, useAiActions,
useTermCuration, useReplaceTool, useDenoiseTool, useAnnotations), each
byte-diff-verified + smoke 32/32 + browser-driven. StudioEditor
4605 → 2754 lines. Notable: the smoke gate caught a real TDZ constraint on
useAnnotations placement (StudioDecos reads actionsRef during useEditor's
synchronous first pass — hook must precede useEditor; composition order
documented in the file). repo-surgeon end-of-chain sweep: zero P0; its two
P1s + P2 fixed (Node snapshot generator now rebuilds the waves META array —
R0-R3 + Wave K render on the plan page; Wave K rekeyed to id:/name:; infra
librarian mirror no longer cites the deleted augmenter). R2 remaining tail
= R2f: JSX child-component splits + editor-coupled route envelope flips
toward ≤600. R4 go/no-go evidence gathered (277 sys.path files, 0 true
collisions left, the two phases/ import roots confirmed — but run_wave.py
is the R5 deletion candidate, so R5-first may dissolve R4's flagship bug);
decision with Asif. Gates: pytest 1658, astro 0, eslint 0 err, smoke 32/32.

**Last updated:** 2026-07-18 12:35 PM EST (Clean-code hardening R2+R3 tranche)

**Newest — R2+R3 executed on Asif's approval (option A), 16 commits pushed.**
R3 (pipeline) substantially complete: both basename collisions gone
(`_agent_invocations` rename + dead `knowledge/augmenter.py` deleted), +72
tests for the 5 untested critical modules (1 real bug fixed in
`_citation_verify` — unreachable 'failed' branch), framing registry (Spec 1)
completed, `_azure.py` split (824→500 + 4 siblings), `_translation_edition`
(1056→576) + `_slide_authoring` (999→569) split along genuine seams,
`intake_book` split DECLINED with recorded reasoning, stage-order drift fixed
(`_stage_gate` was missing the live `literary` stage), audit deferrals all
resolved. DR-005 grandfather list burned 24→21. Callable-DI sweep = recorded
remainder (R3h), sequenced with R4's go/no-go. R2 (site) in progress:
Pass 1 fully done (constants/types/markers/pickers extracted; 21/23 editor
fetches on apiFetch), renderers merged (61-file byte-diff, 0 mismatches),
both fat frontmatters extracted (`library-view.ts`, `studio-shelves.ts`),
CSS layered (`theme-*`/`studio-editor-*`), hooks 3/9 landed one-per-commit
with live browser verification (`useEditorPrefs`, `useAutosaveDraft`,
`useSectionDepth` — the exemplars for the remaining six: useStageApproval,
useAiActions, useTermCuration, useReplaceTool, useDenoiseTool,
useAnnotations). eslint gained `react-hooks/refs` ratchet-warn (compiler
analyzes extracted hooks but bailed on the giant component). All gates
green: pytest 1658 (post-dead-code delta), astro check 0, eslint 0 errors,
prettier clean, lint:views 0/0, smoke 32/32. NOTE: one leftover
`stash@{0}` from an agent's baseline check (superseded snapshot JSONs only —
safe to drop). R4 packaging go/no-go + R5 wave-engine decision await Asif.

---

**Last updated:** 2026-07-18 9:45 AM EST (Clean-code hardening R0+R1 executed)

**Newest — clean-code hardening plan, R0+R1 tranche shipped (7 commits on
`develop`, pushed).** R0: Ruff gate + whole-tree format baseline (pipeline,
`1c26f42`); ESLint+Prettier gates (site, `936291e`); enforceable DR-005
line-count gate with 24-file shrink-only grandfather list + lint wiring into
pre-commit/CI/Makefile (`7fd115c`). R1: Studio renames — `reader/poc/` →
`studio/editor/`, `StudioPoc`→`StudioEditor` (+ CSS class family),
`corpus-mock/`→`corpus/`, `corpus-mock-sample.ts`→`corpus-fallback.ts`,
css pairs (`0bddb02`); `src/lib/api-fetch.ts` shared typed client, 35 call
sites across 21 files migrated, `ai/etymology`+`ai/english-term` flipped to
the strict envelope, apiOk/apiError gained a headers param (`7a5cbb1`).
StudioEditor's 23 fetches + 9 editor-coupled envelope routes deferred to R2
BY DESIGN. Roadmap: `waves_refactor:` block in plan.yaml (R0-R5; R2-R5
pending_approval) + snapshots (`b7a722f`); the Node snapshot generator now
auto-discovers `waves_*` keys (was hardcoded — mirror-parity fix). Gates all
green: pytest 1592, astro check 0, eslint 0 errors, lint:views 0/0, smoke
32/32, browser drive of editor + composer clean. NOTE: machine-policy myth
corrected repo-wide — this is a personal machine, `npm install` works
(`f16aa70`). R2 (editor decomposition), R3-R5 await Asif's approval.

---

**Last updated:** 2026-07-18 5:40 AM EST (Repo audit remediation — groups 1-3)

**Newest — full repo audit + safe-batch remediation.** Report:
`docs/assessment/repo-audit-2026-07-18.md`. Three commits on `develop`
(`b42e700` security, `fa328d9` dead-code, `b606936` edge-drift). Site impact:
removed a 30-file dead island (the superseded chapter-reader UI + 6 uncalled
API endpoints + `SpendChart`); added `sites`/`explainers` to `content-paths.ts`
to match Python; corrected the `editorial.ts` mirror docstring. Gates green
(`astro check` 0 errors, `lint:views` clean). Also (options A+B, pushed):
fixed the pre-existing `test_etymology.py::test_build_pipeline_keeps_only_gated`
flake (test-isolation — stubbed the global corpus loaders; suite 1592 pass / 0
fail); repaired `.codex/hooks.json` (foreign path → repo-relative `.claude/hooks/`);
canonicalized the `docs-updater` agent spec (infra + `.github` mirror) and rebuilt
`infra/_README.md` to 23 agents. Remaining deferrals: WC8 staging trio (live
stage-order mirror), `knowledge/augmenter.py`, `classify_slides.py`, StudioPoc
`poc/` rename + split, wave-engine fate. See `docs/assessment/repo-audit-2026-07-18.md`.

---

**Prior — interactive Etymology AI action on the Book Composer (PDF) page.** _(2026-07-17 2:08 PM EST)_
Commit `d203599` on `develop` (follows the `c85f458`/`03f1d1d` corpus-augmentation
pipeline work same session). Highlight a word in the Book Composer prose editor →
click **Etymology** in the Refinement panel → one Gemini Flash call returns TWO
reviewed outputs shown in a `.cx-ety-card`: (1) a compact **transliterated inline
insert** (`gratitude (shukr, from the root sha-ka-ra — also shakir, mashkur)`) that
REPLACES the highlighted word in the reading-edition prose and autosaves to
`book.md` → so it flows into the generated PDF; and (2) a richer **chapter-aware
companion note** in **voweled Arabic script** (شُكْر · ش-ك-ر · شَاكِر with an example
· مَشْكُور) filed to the Companion Panel as a new `etymology` note-kind, explaining
each derivative with an example in the KSESSIONS/KQUR teaching voice. New
`POST /api/ai/etymology` (two-way English↔Arabic; local KSESSIONS/KQUR root-grounded
then Gemini Flash; inline stays Latin-only, companion is Arabic-with-diacritics —
the two script rules are locked separately in the prompt). Files: `api/ai/etymology.ts`
(new), `scripts/book-composer.ts`, `styles/book-composer.css`, `companion/registry.ts`.
Gemini 2.5 Flash needs `thinkingBudget: 0` or thinking tokens starve the JSON output
(caused a first-pass "unparseable output" — the documented fix). Gated: `astro check`
+ `lint:views` clean, `site-health-sentinel` PASS (32 routes, desktop+mobile, focus
+ Arabic contrast verified), `html-view-challenger` Level 2 conformant (fixed 2
REQ-048 a11y MUSTs: focus-visible on the new buttons + label↔input associations).
Compose route is light-only by design (its Light/Sepia/Dark toggle is the editor
paper, not a page theme). Podcast/PDF batch etymology (`_etymology.py`, 12 seed atoms)
remains the automated peer path; the interactive Studio button is the human-in-loop
creator.

**Earlier — Composer header redesign, Layout mode retired, autosave made shared infrastructure.**
Commit `f1c2936` on `develop`, pushed (follows `13d34c3`/`7018dea`, the Phase 3 Preview
work below, same session). Driven by live feedback on the shipped Preview screenshots —
Asif didn't like the large vertical pill stack in Compose's header. (1) **Header row**:
Preview/LIVE Session/Reading edition/Edit & Enrich moved from a tall vertical stack beside
the title to a compact horizontal row of small rectangular buttons above it, scoped to
Compose only (new `.cx-hdr-btn`/`.cx-header-actions` classes — the shared `.lib-studio-link`
pill other Studio pages use is untouched). This surfaced a REAL bug worth remembering:
reusing `.lib-hero-main` (`flex: 1 1 24rem`, tuned for its normal ROW-direction layout)
inside the new COLUMN-direction header made the 24rem flex-basis apply to HEIGHT instead of
width, padding the block out with ~330px of blank space below its actual content — fixed
with a scoped `flex: 0 1 auto` override. General lesson: flex-basis silently changes axis
meaning when a shared class's container direction changes; check computed `flexBasis`, not
just visual inspection, when a reused flex child looks oversized/undersized in a new home.
(2) **Reading edition removed, LIVE Session pushed far right**: the top-row "Reading edition"
button is gone (redundant with Companion Tool, below); LIVE Session moved to the row's far
right edge (`margin-left: auto`), separated from Preview/Edit & Enrich. (3) **Layout mode
retired** (explicit confirmation via AskUserQuestion after flagging the regression): the
Layout/Edit toggle is gone, Edit is now the sole permanent mode, and the "Layout" button's
old slot is a "Companion Tool" link to the reading edition instead. Figure placement/resize
has no UI home in Compose until Phase 4 (Edit-canvas merge, still queued — unaffected
otherwise). (4) **New `scripts/autosave.ts`**: factored the prose editor's existing
debounced-save pattern (single-flight, trailing re-save, Editing…/Saving…/Saved/Couldn't-save
states) into a shared, reusable module per Asif's explicit ask ("a data structure that can do
this globally in the app") — the figure-layout save (previously a manual "Save layout"
button, now fully autosaved) is the second consumer, and the prose editor was refactored onto
the SAME module rather than left duplicated. Status pill gained icons — spinning loader while
saving, a checkmark that pops in on save, warning + inline Retry on failure, respects
`prefers-reduced-motion`. Verified live end-to-end: placing a figure autosaved with a real
`PUT /api/studio/visual-layout` 200 and the pill reaching "Saved". One process note: while
testing the remove-a-figure path, nearly clicked the palette's delete-artifact-from-disk
button (not an unplace control — Layout's own remove-placement UI is gone too); caught it at
the confirmation dialog and cancelled before anything was destroyed — worth remembering when
testing this area again, since there is currently no non-destructive way to unplace a figure.
Gates: `astro check` / `lint:views` / `npm run build` / `npm run smoke` (32/32) all clean.

**Newest — Phase 3 Preview: live page-image render, zoom, Generate PDF moved off Compose.**
Commit `13d34c3` on `develop`, pushed. Shipped in a materially different shape than the
original Phase 3 plan (`~/.claude/plans/a-no-this-is-mossy-comet.md`) after two dead ends,
both discovered mid-build, not in planning: (1) live in-browser pagination via vendored
Paged.js hung/crashed on this environment's Chromium on every real test — including a
trivial two-paragraph, zero-stylesheet case with no book content involved — an unresolved
Paged.js↔modern-Chromium gap (Chromium only gained native paged-media support, print-only,
in v131; Paged.js's last stable release predates that); (2) an intermediate design embedding
the canonical book.pdf in an `<iframe>` was byte-perfect but wrong for "scroll the whole book
on the page" (a native PDF viewer owns its own internal scroll region) and only ever showed
the last-published file, not live edits — which is what Asif actually asked for once he saw
it ("this should NOT be the actual PDF... I want to see how the PDF will render based on the
changes I make in Compose").
**Landed design:** `/studio/<slug>/preview` renders LIVE from whatever is currently saved in
`book.md`/`visual-layout.json`/`citation-style.json` — a scratch PDF via the exact same
`render-book-pdf.mjs` engine the real PDF uses (auto-detected staleness vs. those three
source files, regenerated only when needed), rasterized page-by-page with `pdftoppm` and
cached under `book/_preview-cache/` (gitignored), then stacked as plain `<img>` elements in
normal document flow so the browser's ONE scrollbar carries the whole book — no boxed/nested
scroll region. A sticky Zoom slider (30-90% of the container, hard-capped at 90% per Asif's
ask) controls page width client-side, persisted to `localStorage`. The HTML-assembly logic
shared by the PDF renderer and Preview is factored out of `render-book-pdf.mjs` into
`scripts/lib/book-html.mjs` (single source of truth — REQ-SC-022 — verified byte-for-byte
regression-safe against the prior renderer via an A/B PDF diff on a real 117-page book before
landing). Compose's Output tab is REMOVED; "Save layout" moved next to the Layout/Edit mode
toggle; "Generate PDF" moved to Preview behind a themed `confirmDialog()` (never a native
`confirm()`) — it still writes the canonical `book/book.pdf` via the unchanged
`/api/studio/generate-book-pdf` endpoint, now the ONLY thing that touches that file. Two
sizing bugs caught and fixed mid-session, both worth remembering: (a) a page-image `max-width`
in `rem` silently rendered ~1.2x larger than intended — this site's `html` font-size is
`19.2px` (REQ-010 reading floor), not the standard `16px`, so `rem` sizing on raster/layout
widths needs a plain `px` value or an explicit note; (b) "too zoomed in" from Asif meant "too
large/magnified," not "too small" — the opposite of my first read; when a size complaint is
ambiguous, use a fixed reference in the user's own screenshot (here: the browser's own chrome,
which doesn't scale with page zoom) to measure the actual direction before changing anything.
Gates: `astro check` / `lint:views` / `npm run build` / `npm run smoke` (32/32 routes) all
clean; `preview-fidelity-challenger` (the Phase-0 parity agent) was never installed as a
blocking gate — parity between Preview and the PDF is now true by construction (same
renderer), so the page-structure-diff machinery it was meant to run is moot. Not yet done:
Phase 4 (Edit-canvas merge, Layout's figure controls folding into Edit) — unaffected by this
work, still queued next per the parent plan's risk ordering. A `repo-surgeon --scope podcast`
post-merge audit is due per standing convention before the next merge/push to `develop`.

Book Composer UX trio (autosave, reading-edition link, themed dialog).
Local commit on `develop` (not yet pushed). Files: `compose.astro`, `book-composer.ts`,
`book-composer.css`, new `confirm-dialog.ts`. (1) Composer header gains an "Open reading
edition" link → `/studio/<slug>/book`, and the misleading "Read" mode toggle is renamed
"Layout" (it's the figure-placement + preview surface, NOT a reader — repurposing it was
rejected as a regression). (2) The prose editor now AUTOSAVES: debounced (~1.2s) silent
PUT to `/api/studio/book-md`, single-flight + trailing re-save, a status pill (Editing… →
Saving… → Saved <time> → Couldn't save + Retry); the manual "Save prose"/"Cancel" buttons
are removed. Because the page holds the original server render in memory, LEAVING an edited
chapter (to Layout or another chapter) reloads once to re-render — and that reload now
PRESERVES the chapter + Edit mode (fixes the old always-reset-to-chapter-1 quirk) via
`sessionStorage` (`cx-restore-chapter` / `cx-restore-edit`). (3) New vanilla promise-based
`confirmDialog()` (`.cx-confirm-*`, `--c-*` tokens, focus trap, Esc/backdrop cancel, focus
restore, danger variant) replaces the native `confirm()` on the discard-edits + delete-
artifact paths; with autosave the discard prompt only fires on a genuine save FAILURE.
Gates: html-view-challenger PASS (full AA; added dialog `aria-describedby` per its one
SHOULD), site-health-sentinel PASS (no defects; confirmed the scrim already dims the nav).
Verified in chromium with the save endpoint MOCKED — book.md never mutated. Follow-up
DONE: the last native `window.alert()` (delete-FAILURE path) now uses a themed one-button
`noticeDialog()` (role=alertdialog, aria-describedby, danger); the now-implemented
`_workspace/plan/composer-ux-plan.md` was removed. Broader Studio redesign Phase 3
(Preview/Paged.js — needs a one-file download OK) + Phase 4 (Edit-canvas merge) remain.

**LIVE Session reworked: single-scroll reader + passage-level Companion.**
Local commit on `develop` (not yet pushed). Supersedes the Phase-2.5 pagination below.
`/studio/<slug>/live` is no longer paginated — it now stacks every chapter as its own
numbered paper "sheet" down ONE window scrollbar (no inner scrollbars): centered reading
toolbar, balanced margins, ~70ch measure, and a sticky right Companion. The Companion is
now PASSAGE-level: a scroll-spy shows exactly ONE card — the note for the sentence you're
reading — and highlights that verbatim sentence in YELLOW (`.lsv-hl.is-active`, per-paper
`--lsv-mark`); non-active passages are invisible; no inner companion scroll. Data: added a
verbatim `quote` field to companion notes (`types.ts`/`store.server.ts`; distinct from the
`anchor` card-title label); pre-filled 27 real chapter sentences (verified verbatim in
book.md) across the 8 M&D chapters; 5 illustration-only notes intentionally have no quote.
Editor: the Companion note form (`CompanionPanel.tsx`) gained a "Capture passage" control
(select prose → stored as `quote`), the `anchor` field is relabeled "Card title", and note
cards show a yellow passage pill (`CompanionCard.tsx`). Verified in real chromium (reader
highlight + editor capture + API persist round-trip); `astro check` 0 errors, `lint:views`
clean. Gates: BOTH PASS. site-health-sentinel PASS (fixed one mobile defect — the
"Contents" button clipped at ~360-390px; `flex-wrap:wrap` on `.lsv-topbar-left`).
html-view-challenger PASS on DoD + theme after fixes: a keyboard MUST (the Capture button
was mouse-only → now onClick, keyboard-accessible), 2 aria SHOULDs (hint `role=status`;
dropped the verbose scroll-driven live-region on `#lsv-explain-body`), and tokenizing the
highlighter into one shared `--reader-mark`/`--reader-mark-edge` pair (in book-reader.css)
referenced by BOTH the reader highlight and the editor pill (no `--c-*` theme change). Fix
commit follows `d97c1cf`. Known pre-existing debt: HEAD stores note em-dashes escaped
(`—`) while the store writes them literal — left as-is.

**Earlier — Phase 2.5: LIVE Session was a Kindle-style e-reader (now superseded above).**
Commits `757957e` + `64c0422` on `develop`. `/studio/<slug>/live` now paginates the book into
screen-sized pages (CSS multi-column + translateX) turned one at a time (flip buttons,
Arrow/Page keys, swipe); a ResizeObserver re-paginates on layout/font/resize and reveals
after a stable measure (no pre-font flash). Adds a reading toolbar (font, size stepper,
paper Light/Sepia/Dark — same reading-paper colours as the composer), a TOC drawer that
jumps to any chapter, justified body + left-aligned accent headings, tighter spacing,
Arabic scaled 1.4x, and note-anchor highlighting (verbatim best-effort). Gated:
html-view-challenger PASS Cortex L1 + SC-CLEAN, site-health-sentinel PASS (fixed a
mobile large-font heading clip + note-card keyboard a11y). Remaining: Phase 3 Preview
(needs a one-file Paged.js download OK) and Phase 4 Edit-canvas merge.



**Latest — Composer/Preview/LIVE-Session redesign, Phases 0-2 on `develop`.**
Four commits (`b6685d5`, `bcfe7db`, `7b1c584`, `04e2bcf`) toward a 4-phase Studio UX
redesign (plan: `~/.claude/plans/a-no-this-is-mossy-comet.md`). **Phase 0** — durable
contract: `docs/standards/studio-composer-quality.md` (REQ-SC-*), skill
`skills-staging/studio-composer/SKILL.md` (registered), deterministic Preview↔PDF
parity probe `plan-dashboard/scripts/preview-fidelity-check.mjs` (PF-* ids; PDF side
live via pdftotext, preview side is a guarded Phase-3 seam) + `preview-fidelity-challenger`
agent, and `/studio/<slug>/live` wired into the smoke + sentinel manifests. **Phase 1** —
"Chapters" tab restyled as a `.lib-tab-cta` pill matching "PDF Generator"; a new
"LIVE Session" pill on the overview tab row + composer header. **Phase 2** — new LIVE
Session view `/studio/<slug>/live` (`live.astro` + `live-session.css` own identity,
reuses `book-reader.css` prose): reading column + a right-hand read-only explanation
panel that scroll-syncs to the in-view section and shows that section's Companion
notes; a bucket-filterable, multi-volume-nested book picker sourced from `listContent()`
(`live-index.ts` + `live-session.ts`). Gated: html-view-challenger PASS Level 1,
site-health-sentinel PASS, 31/31 smoke clean. **Remaining: Phase 3** (rename Read→Preview,
whole-book paginated preview reusing `book-print.css` via vendored Paged.js — needs a
one-file download OK) and **Phase 4** (full-merge the Edit canvas: text + figure
place/resize in one surface, inspector Edit-only — the highest-risk rework).

**Prior — Editor UX parity across both editors + a durable null-hook fix.**
Three commits on `develop` (`efa86c2`, `36149ea`, `aa2f544`). (1) **Book Composer
editor** (`/studio/<slug>/compose`, `book-composer.ts` + `book-composer.css`) is
now a word-processor-style editing surface: a framed editor card with a
`:focus-within` accent ring and a tinted toolbar header; a **font · size · B/I/U**
toolbar (font selector Sans/Serif/Lato/Inter/Mono/Dyslexic, a text-size stepper,
B/I/U + H/quote/list); **Kindle-style paper themes** Light/Sepia/Dark; the writing
area fills the column and **justifies** (headings excluded); a white full-width
hero banner with a full-width description. (2) **Edit & Enrich editor**
(`StudioPoc.tsx` + `studio-poc.css`) got the SAME reading-comfort controls
(font/size/paper) + justified full-width prose, as React state persisted to the
SAME `cx-editor-*` localStorage keys so a choice carries between both editors; the
picked Latin face is PREPENDED to the mixed-script ProseMirror stack so Arabic
still falls through to Amiri; the B/I/U bar was intentionally NOT ported
(StudioPoc has its own mark tooling). (3) **Shared fonts**: new
`src/styles/editor-fonts.css` self-hosts Inter/Lato/OpenDyslexic (WOFF2 400/700 +
OFL under `public/fonts/*`), imported by both editor pages (composer duplicate
removed). Editor-view controls are VIEW-ONLY — `book.md` carries no font/size, so
the printed book is unaffected; underline is editor-only (the reader's markdown
renderer escapes raw HTML, no underline syntax). (4) **Durable fix**:
`resolve.dedupe: ['react','react-dom']` in `astro.config.mjs` ended the recurring
"Cannot read properties of null (reading 'useContext'/'useRef')" island blanks
(a nested dep resolved its own React). Also cleared a stale/corrupt
`node_modules/.vite` optimize cache that had blanked Edit & Enrich mid-session.
**Verification**: `lint:views` clean, `astro check` 0 errors, `npm run build`
clean, and the headless smoke sweep is **30/30 routes clean** (was 29/30 with
`/corpus` failing before the dedupe). Visual sign-off via the browser tools was
deferred (they disconnected mid-session); the changes are CSS/state-scoped and
gate-verified.

**Prior — Site-health runtime gate shipped.** The site now has a RUNTIME/visual
peer to the static `html-view-challenger`, mirroring the book pipeline's
`book-challenger` (source) vs `book-render-challenger` (rendered) split. Two
layers, both using the already-installed Playwright (no `npm install`):
(1) **deterministic, zero model spend** — `plan-dashboard/scripts/site-health-smoke.mjs`
(`npm run smoke`) boots the dev server, visits every page route in headless
chromium, hard-fails on any console error / uncaught exception / failed request /
5xx; auto-fires from the re-purposed `Stop` hook
(`.claude/hooks/ui-reviewer-stop.sh`, formerly the disabled `ui-reviewer` stub)
whenever `plan-dashboard/` changed and a server is up on :4322. (2) **visual
judgment** — the new `site-health-sentinel` agent (both agent trees + registry;
installed to `.claude/agents/`) screenshots each surface at ~1440px + ~390px
across states via `scripts/site-health-shots.mjs`, judges pixels, fixes the
smallest in-pattern source change, re-gates `lint:views` + `astro check`,
converges ≤5, deletes its throwaway `.visual-qa/`. DoD line added to CLAUDE.md;
runs as a PAIR with `html-view-challenger`. Inaugural sweep: **29/29 routes clean
(0 console errors / 0 exceptions / 0 5xx); 0 actionable visual defects** across
architecture / library (desktop+mobile) / composer / reading edition / wisdom
empty-state. Two CONTENT observations surfaced (not agent-fixable): chapter-title
echoed as the first body line in the composer + reading edition; wisdom intro
counts (19/122/1,337) vs live 0/0/0 (likely local corpus-DB gap). Dark theme on
long-form architecture views stays light-bodied — consistent with the KNOWN
deferred theme-exception work, not a regression. NOTE: the agent registry is
fixed at session start, so `site-health-sentinel` is invokable via the Agent tool
from the NEXT session onward.

**Prior — Book Composer round 2.** Three follow-up groups landed
(plan: `~/.claude/plans/create-a-detailed-plan-piped-perlis.md`): (1) **Citations**
now center BOTH Arabic and translation with tighter translation leading
(line-height 1.35), across all four CSS layers (`book-styles`, `book-print`,
`book-reader`, `book-composer`). (2) **Editing** — the chapter opens directly in
the editor by default; the **Refinement tab is now AI text actions** (Rewrite /
Expand / Condense / Simplify / Explain) that call `/api/ai/rewrite` (+ new
`expand` mode, hardened JSON parse) and `/api/ai/explain`, showing an
accept/reject option popup and replacing the editor selection; figure layout
controls moved OUT of Refinement onto a floating `.cx-fig-card` on the selected
figure (Read mode). Chapter switching while editing is guarded with a discard
confirm. (3) **Artifacts** — hover-to-enlarge preview, per-item delete + AI-edit
icon buttons, and a "New AI image" box. Net-new backend:
`scripts/podcast/composer_visual.py` (Gemini `gemini-3.1-flash-image` generate +
image-to-image edit, reuses `_visual_candidates.write_index` + `_gemini_client`)
behind `api/studio/visual-op.ts` (spawn-Python, like generate-book-pdf). Delete
removes the index entry + unlinks the file. Real Gemini image spend (~$0.04/img,
authorized). Palette item refactored to a `role="group"` with a real place-button
+ sibling action buttons (fixed the challenger's nested-interactive a11y finding).
Gates: astro check 0/0/0, lint:views clean, build OK, html-view-challenger
PASS-WITH-CAUTION → the one a11y MUST fixed. Verified in-browser: centered verse,
default editor, Rewrite→3 options→accept-replaces, inline figure card, hover
preview, real Gemini generate (gen-1.png, 670KB) → delete round-trip (fixture
restored, no content/ mutations).

**Prior — Book Composer is now a chapter-scoped editing workspace.** Three
feature groups landed (plan: `~/.claude/plans/create-a-detailed-plan-piped-perlis.md`):
(1) **Shell** — chapter picker moved to the top-left of the preview, first
chapter default, only the selected chapter renders, header trimmed to "Edit &
Enrich" (dropped "Citation styles"/"Reading edition"), and a new **Citations**
tab after Artifacts (tablist: Artifacts · Citations · Refinement · Output).
(2) **Citations tab** — reuses the `.bs-*` predefined-style picker
(plain/scholarly/elegant, persisted via `/api/studio/citation-style`) + lists
this chapter's detected Quran/hadith citations (detected in `composer.ts` from
the `blockquote.quran` markup now emitted by `markdown.ts`). The Quran verse was
toned down across all three layers (`book-print.css`, `book-reader.css`,
`book-styles.css`): no box, minimal padding, Arabic at ~body scale in
`var(--c-ink)` instead of gold. Per-type distinct PDF rendering is deferred
(declined pipeline). (3) **Edit mode** — a Read/Edit toggle mounts the same
TipTap engine (`book-md-editor.ts`, `@tiptap/core` + StarterKit) on the selected
chapter, editing **book.md directly** (not chapter source — verified via the
compose chain that source edits never reach book.md) and saving the chapter's
section via new `PUT /api/studio/book-md` (surgical section replace, `.bak`
backup). NOTE: a manual `compose_book_v2 --force` would regenerate book.md and
overwrite direct edits; book.md is the last-mile reading edition so this is
acceptable. Gates: astro check 0/0/0, lint:views clean, build OK,
html-view-challenger PASS-WITH-CAUTION (Level 1). Verified in-browser: chapter
scoping, Citations detection (2 in ch.1), toned verse (body-ink), Edit mount +
surgical save round-trip (fixture restored).

**Prior — Book Composer preview is now truly WYSIWYG.** Closed the three
open gaps against the original Phase-4 spec (drag-to-anchor, resize handles,
float-exact preview): placed figures now render INLINE inside `.cx-body` at the
exact paragraph the PDF renderer (`scripts/visual-layout.mjs::applyLayout`)
would use (null→after intro, 0→chapter top, N→after Nth top-level `<p>`) instead
of a band at the chapter top; wrap figures truly float with body text wrapping
beside them (`.cx-body` is `display: flow-root`); a corner resize handle
(`.cx-fig-handle`, pointer-drag → width_pct, snapped 5%, clamped ≤50% wrap); and
drag-and-drop is paragraph-granular with an insertion indicator. The
preview-vs-PDF paragraph counters were proven to agree exactly (blockquote-
nested `<p>` excluded by both). Files: `compose.astro`, `book-composer.ts`,
`book-composer.css`. Gates: `astro check` 0/0/0, `lint:views` clean,
`html-view-challenger` PASS-WITH-CAUTION (the one MUST — REQ-010 1.02rem body
prose — is the pre-existing intentional print-fidelity exemption, unchanged by
this work). Verified in-browser: place → wrap float wraps text → Position moves
the figure → handle-drag 50%→30%.

**Current branch merged into develop:** book-pipeline-v2 (merge 4165160, --no-ff);
review follow-ups in 3a7534a (GET visual-layout endpoint, paragraph-level
anchor_para + "Position in chapter" Composer control, dashboard snapshots).
Fluency de-calque validated faithful on 2 real mukhtasar chapters (both kept, 59
Arabic runs preserved) — see `_workspace/plan/book-pipeline-cutover.md`. Cutover
still held pending the full knob-matrix + PDF render loop.

**Current branch merged into develop:** book-pipeline-v2 (merge 4165160, --no-ff).

**What changed:** Book Pipeline v2 landed behind the `book_pipeline_v2` flag
(default OFF — zero behaviour change on develop until a book opts in). New Astro
surface: the **Book Composer** at `/studio/<slug>/compose` (view
`studio/[slug]/compose.astro`, loader `lib/reader/composer.ts`, client
`scripts/book-composer.ts`, styles `styles/book-composer.css`) where a human
places visual candidates (align/flow/width/drag-anchor/caption/page_fit), Save
writes `book/visual-layout.json` via `api/studio/visual-layout.ts`, and Generate
PDF calls `api/studio/generate-book-pdf.ts`. Assets served by
`api/studio/visual-asset.ts`. The PDF renderer (`render-book-pdf.mjs` +
`book-print.css` under `body.book-v2`) consumes the layout contract (floats for
wrap, centered for standalone, one-plate, page-fill) — all flag-scoped. Contract
mirror: `_visual_layout.py` ↔ `visual-layout.mjs` ↔ `composer.ts` anchorKey.

**Site verification:** `lint:views` clean, `astro check` 0/0/0, `npm run build`
succeeds, `node scripts/visual-layout.test.mjs` (12) green, and the Composer was
driven in-browser (desktop + mobile): place → configure → Save writes a valid
`book.visual-layout/v1` file → wrap clamps width to 50%. `html-view-challenger`
PASS (Level 1).

**Current translation-edition state:** `mukhtasar-ul-asar-2` has a rerendered
titled PDF in `content/Islamic/mukhtasar-ul-asar-2/book/` and the Google Drive
Podcast Library copy was refreshed by `build_book_pdf.py`.

**Site verification:** `node --check plan-dashboard/scripts/render-book-pdf.mjs`,
`npm run lint:views`, `validate_book_ready.py mukhtasar-ul-asar-2`, Poppler
page-by-page blank audit, and focused podcast regression tests all pass.

**Current Al Anwaar state:** vol-01 has a 27-entry glossary and Arabic script in
all 11 chapters. Ship validation passes all 14 gates, including G13
`arabic-script-in-chapters`.

**Prior Studio status carried from develop:** Session 32 reworked the Studio Arabic
review/editor shell, unified action panel, Noise tool, raw Arabic styling, reading
width, and left-gutter mark icons. Deferred design decisions remain: NarrativeScroll
theme exception/retheme, REQ-010 typography sweep, section ids/number markers,
figure wrappers, print/smooth-scroll/metadata polish, system-map density split, and
SpendChart dead-code removal.
