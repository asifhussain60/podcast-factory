# Corrections, moderators, and books under moderation

> ## Build status — 2026-09-20
> **Built and running locally (nothing deployed):** phases 1, 2, 3, 4 and 6, plus the Library half of
> phases 5 and 7 (see the table in section 9e), and the repo-side Python (packets and checks, the AI
> reviewer, applying corrections to the book, importing suggestions). Deployment to the live
> site waits on Asif's local sign-off, per the project rule.
>
> **Where the build differs from the design below, and why:**
> - **Moderator controls live on their own admin screen** (`/admin/moderators`), not on the People
>   table: that route was at its size ceiling, and a moderator is a kind of privilege worth a list of
>   its own.
> - **The reader route gained ONE line.** The whole feature is wired through the selection bar and a
>   window event, because that route is also at its size ceiling.
> - **Corrections are painted with the CSS Custom Highlight API**, not by wrapping text, because the
>   reader's own highlights are painted by rewriting the DOM and two painters over one DOM strip each
>   other's marks.
> - **`pipeline` is a valid "raiser"** for sweep suggestions, which forced the address comparison to
>   tolerate a non-address (a defect the tests caught before it shipped).
> - **§3's `VISIBLE_SQL` was wrong** in the first draft and is corrected in place.
> - **The source pane highlights the matching span only in the EXTRACTED text.** A scan is in the
>   original script and cannot be matched to an English quote, so it is never guessed at.
> - **`isaf-al-talib`'s scan is marked "noisy" by hand** (`_system/source/ocr/quality.json`): it mixes
>   clean Arabic with handwritten Urdu that the OCR renders as plausible fragments, which the automatic
>   heuristic cannot tell from text.

**Surface:** the Podcast Factory Library (`listener/`). Design only — nothing built yet.
**Date:** 2026-09-20

---

## 1. The one rule that shapes everything else

A correction is a change to a book's prose. This repo already has a locked answer for
where prose changes happen:

> **The Book Composer is the SINGULAR path for chapter modifications destined for the
> PDF** (CLAUDE.md, LOCKED 2026-07-20).

Chapter prose is rendered to HTML **once**, at publish time, by `renderMarkdown` — so the
web reader and the printed PDF cannot give two answers about the same paragraph. If the
Library writes corrected prose into its own `chapter` table, three things break at once:

1. The PDF and the web reader diverge, permanently.
2. The next `publish_to_listener.py` run overwrites the correction and says nothing.
3. There are two authoring surfaces for one sentence.

So the architecture is: **the Library CAPTURES corrections; it never applies them.**

A correction has a life: `open → accepted → applied → dismissed`. It is *applied* back in
the repo, through the Composer's own edit path (`_system/composer-edits.json`, replayed by
`_book_edits`), which is what makes a correction survive a re-compose. The normal
publish → deploy then carries the corrected prose back to the Library, and the correction
is stamped `applied`. The loop closes **through** the singular path instead of around it.

This is the single most important decision in this document. Everything below assumes it.

---

## 2. The moderator role

### What must not change

`isAdmin` today is `normalizeEmail(session email) === normalizeEmail(env.ADMIN_EMAIL)`.
There is deliberately **no role column anywhere**, so no row write can grant admin, and a
missing `ADMIN_EMAIL` fails closed. That stays exactly as it is. Moderator is a strictly
*additive*, strictly *lower* capability. **Admin always implies moderator.**

### Storage — migration 0022

```sql
CREATE TABLE moderator (
  user_email TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
  granted_by TEXT NOT NULL,
  granted_at TEXT NOT NULL,
  revoked_at TEXT
);
```

Keyed on **normalized email**, not user id — the same rationale `access_grant` gives: a
moderator can be provisioned before they have ever signed in. Revoked, never deleted.
Every grant and revoke writes an `access_event` row in the same `db.batch`, exactly as
`people.server.ts` already does for invites and grants.

Because the address is now a privilege bit in a second place, every comparison goes through
`normalizeEmail` in `email.server.ts`. No exceptions.

### Resolution — one field, one place

`Viewer` gains `isModerator`, resolved in `withSession` (`app/middleware/session.ts`)
beside `isAdmin`:

```ts
isModerator: viewer.isAdmin || (await isModeratorEmail(env.DB, email))
```

**Cost, stated honestly:** this adds one indexed D1 lookup per request that has a viewer.
The alternative — resolving it lazily in whichever gate needs it — is what the codebase
already warns against everywhere else: a rule computed in two places is a rule that will
disagree with itself. One field, resolved once, read everywhere. The lookup fails closed
(any error ⇒ `false`).

**Simulation (revised 2026-09-21).** `simulate.server.ts` still sets `isAdmin: false` unconditionally, but
`isModerator` is now the PERSON'S OWN status — the first draft forced it false, which made "See as them" useless for
checking a moderator's experience. It never gives the administrator more than the person holds, and every correction,
comment and chapter-review write is refused (403) while simulating. Proved in `security-moderation.mjs`.

### Gate — `app/middleware/moderator.ts`

Layer 3b, a sibling of `requireAdmin`, same shape, same `notFound()` denial — a 403 would
confirm the surface exists.

---

## 3. Books under moderation

### Interpretation of the ask

- An ordinary reader **does not see the book at all**. Showing them a greyed-out tile
  labelled "Under Moderation" would tell them a book exists that they may not open — which
  is precisely the information the 404-not-403 rule throughout this app exists to withhold.
- A **moderator or admin** sees the tile on their shelf, styled inert with an
  "Under Moderation" ribbon, and **can still open it** — that is the point of the state.
  "Disabled" here is a visual signal that the book is not live, not a dead control.

### Storage — migration 0022 (same migration)

```sql
ALTER TABLE content_unit ADD COLUMN under_moderation INTEGER NOT NULL DEFAULT 0
  CHECK (under_moderation IN (0, 1));
```

A **separate column, orthogonal to `status`** — not a fourth `status` value. Adding
`'moderation'` to the status CHECK would mean relaxing `VISIBLE_SQL`, and `VISIBLE_SQL` is
the one entitlement expression in the application; every relaxation of it is a leak
surface. A boolean lets the change to `VISIBLE_SQL` be a *tightening*, which fails closed.

### The entitlement rule stays a single expression

> **Corrected 2026-09-20 after review.** The first draft added only `AND (under_moderation = 0
> OR ?2 = 1)` and claimed that was a pure *tightening*. It is not enough: `VISIBLE_SQL`
> requires `status = 'published'` **and** an open/granted entitlement, and a book waiting for
> moderation is almost certainly still a **draft** with no grants. A moderator could never
> have seen it. Making them able to is an *additive* branch, which is a loosening — so the
> "fails closed" argument does not apply to that half, and it needs its own test.

`VISIBLE_SQL` becomes two mutually exclusive branches in **one** expression, keyed on the flag:

```sql
WHERE u.kind <> 'work' AND (
     -- Under moderation: ONLY moderators/admins, whatever the status or grants.
     ( u.under_moderation = 1 AND ?2 = 1 AND u.status <> 'archived' )
  OR -- Everything else: the existing rule, unchanged.
     ( u.under_moderation = 0 AND u.status = 'published' AND ( u.open_to_all = 1 OR EXISTS (...grant...) ) )
)
```

`?2` is the viewer's moderator bit. The two branches cannot both be true for one row, so an
ordinary reader can never reach the first, and a book flips wholly from one to the other with
a single column. Every caller now binds two parameters — `visibleUnits`, `canRead`, and the
`search.server.ts` JOIN — and a missed call site binds no `?2`, so it matches **no**
moderation books (fails closed). New tests: an ordinary reader with an `open_to_all` grant
still cannot see a moderated book; a moderator with **no** grant and a **draft** status can.

`canRead(db, email, slug, isModerator)` — so `requireUnitAccess` keeps working unchanged.

### Who sets it

`/admin/content` only. **`publish_to_listener.py` must never write this column**, under the
same standing prohibition that keeps it away from `status` and `open_to_all`: it runs
unattended, and a privilege bit set by an unattended script is a privilege bit nobody
decided. The existing test that greps for exactly this gets a third column name added to it.

---

## 4. The Correction button

### Where it lives

`app/components/reader/SelectionBar.tsx` — the bar that already appears over a selection
and over a tapped highlight.

### Why it cannot be another icon in the row

The bar is the one floating element in the app and its width is already scarce — the Copy
button was deliberately *removed* (2026-08-04) to stop it competing with the two actions
only that bar can do. A correction is also not the same **kind** of act as what is in that
row: highlights and notes are the reader's own private marks on their own copy, and a
correction is an editorial act on the book everyone reads. Making it a fifth sibling would
say the opposite.

### The design

A **separate strip beneath the swatch row**, in its own material — the way `--paper`
already turns the bar into a sheet of paper when you write a note:

```
┌────────────────────────────────────┐
│  ● ● ● ●   │   🗒   │   🗑         │   ← the reader's own marks
├────────────────────────────────────┤
│  ✎  Correct this passage           │   ← editorial. different material.
└────────────────────────────────────┘
```

- **A word, not an icon.** Every other control in the bar is a glyph; this one is labelled.
- **Its own accent**, from the existing `--l-*` token set — deliberately *not* one of the
  four highlight colours, which all mean "a reader marked this."
- **Full width**, so it costs the swatch row nothing on a phone.
- **Rendered only for moderators.** Never rendered-and-disabled: a greyed control tells an
  ordinary reader that a correction power exists.

No inline styles. The bar's `--sel-top` / `--sel-left` custom properties remain the only
inline style in the app, and they stay a measurement rather than a design decision.

---

## 5. The correction panel

### Not a popup — a third host for `SidePanel`

`app/components/reader/SidePanel.tsx` already serves the contents drawer on the left and
the reader's marks on the right, docks above a breakpoint and becomes an ordinary drawer
below it. Corrections get a **right-side panel** as a third host. A correction needs room
for four things at once — the original, the proposal, the source scan, and the reason — and
a bar floating over the paragraph it is quoting is the wrong shape for that.

### What the panel shows

| Pane | Content |
|---|---|
| **The passage** | The selected sentence, verbatim, with its surrounding paragraph greyed. Read-only. |
| **The source** | The OCR / extracted source span for this chapter (§6). Collapsed by default. |
| **The correction** | The proposed replacement text. **Plain text, not rich HTML** — see below. |
| **Why** | Free rationale, via `RichNoteEditor`. Rich is right here. |
| **Kind** | typo · Arabic · meaning · citation · formatting · other |
| **Open on this chapter** | Every other moderator's corrections on this chapter, with status. |

### Why the proposed text is plain and the rationale is rich

`book.md` is **markdown**, and the Composer replays edits as markdown. A proposal captured
as TipTap HTML cannot be replayed through `_book_edits` without a converter — a second
answer to what the paragraph says, which is the exact failure mode §1 exists to prevent.
The rationale never reaches `book.md`, so it can be as rich as the note editor already is.

`RichNoteEditor` is reused as-is for the rationale — it is the one note-editing surface, it
is already SSR-safe on a Worker with no DOM, and a second editor would be a second answer
to what a note looks like.

### Anchoring — reuse, do not reinvent

A correction anchors exactly the way an annotation and a Companion card do: `anchor_key` +
`block_index` + `start/end offset` + `quote` + `prefix`, resolved by `resolveAnchor` in
`app/lib/anchor.ts`, which **refuses on ambiguity rather than guessing**. A correction
whose quote no longer resolves after a re-compose is reported as *orphaned*, never guessed
into place — the same contract `_book_edits` already has for orphaned Composer edits.

### Storage — migration 0023

```sql
CREATE TABLE correction (
  id             TEXT PRIMARY KEY NOT NULL,
  slug           TEXT NOT NULL,
  anchor_key     TEXT NOT NULL,
  block_index    INTEGER NOT NULL,
  start_offset   INTEGER NOT NULL,
  end_offset     INTEGER NOT NULL CHECK (end_offset > start_offset),
  quote          TEXT NOT NULL,
  prefix         TEXT NOT NULL DEFAULT '',
  proposed_text  TEXT NOT NULL,
  rationale_html TEXT NOT NULL DEFAULT '',
  kind           TEXT NOT NULL CHECK (kind IN
                   ('typo','arabic','meaning','citation','formatting','other')),
  status         TEXT NOT NULL DEFAULT 'open' CHECK (status IN
                   ('open','accepted','applied','dismissed')),
  raised_by      TEXT NOT NULL COLLATE NOCASE,
  raised_at      TEXT NOT NULL,
  updated_at     TEXT NOT NULL,
  decided_by     TEXT COLLATE NOCASE,
  decided_at     TEXT,
  applied_at     TEXT,
  deleted_at     TEXT,
  deleted_by     TEXT COLLATE NOCASE
);
CREATE INDEX idx_correction_open ON correction (slug, status) WHERE deleted_at IS NULL;
```

> **A correction is NOT private to its author**, and this is the one place the reader-state
> rules deliberately do **not** apply. `bookmark` and `annotation` filter every read and
> every write on `user_email` — that was a live hole until 2026-08-04 and is pinned by
> `test/marks-isolation.test.ts`. A correction is shared moderator work: every moderator
> sees every correction on a book. **This difference must be written into the migration
> comment and pinned by its own test**, or somebody will later "fix" the missing
> `user_email` filter and silently make the queue single-player.

---

## 5a. Who may do what to a correction

**Reading is shared. Writing is owned. Admin overrides both.**

| Action | Moderator, own | Moderator, someone else's | Admin |
|---|---|---|---|
| See it | ✅ | ✅ | ✅ |
| Raise a new one | ✅ | — | ✅ |
| Edit the proposed text / reason | ✅ **while `open`** | ❌ | ✅ always |
| Withdraw it | ✅ while `open` | ❌ | ✅ always |
| Accept / dismiss | ❌ | ❌ | ✅ |
| Delete | ❌ | ❌ | ✅ (soft — see below) |

### The three inferences behind that table

1. **Only admins accept or dismiss.** Accepting a correction is authorising a change to the
   book. Moderators *propose*; the admin *decides*. This follows from "Admin can edit and do
   anything" and is what keeps the `open → accepted` transition a single editorial hand.
2. **A correction locks to its author once it leaves `open`.** Otherwise the text an admin
   accepted could quietly change before `pull_corrections.py` reads it, and the thing
   applied to the book would not be the thing approved. Admin can still change it.
3. **"Delete" is a soft delete.** Everything else in this schema that removes something
   keeps the row — `access_grant.revoked_at`, `invite.revoked_at`, `annotation.deleted_at`.
   A hard delete of another person's contributed work is unrecoverable and out of step with
   the whole database. `deleted_at` + `deleted_by`, gone from every view, recoverable,
   audited. **Flagged for your confirmation** — you said "delete", and this is me reading it
   as "make it go away" rather than "destroy the record".

### One function, called by every intent

The per-row authority check cannot be middleware — middleware runs before the row is known.
So it is exactly one function, in `corrections.server.ts`:

```ts
function authority(viewer: Viewer, row: Correction): "full" | "own" | "none"
```

`full` for an admin, `own` when `row.raised_by === viewer.email && row.status === "open"`,
`none` otherwise. **Every intent calls it; the UI never decides.** The panel hides controls
you cannot use, but hiding is cosmetic — the route is what refuses. A rule enforced in a
component is a rule a `.data` request walks straight past.

### Audit — what makes "admin can do anything" safe

Every accept, dismiss, edit and delete writes an `access_event` row in the same `db.batch`
as the change, exactly as invites and grants already do. An admin editing a moderator's
proposal records the **prior text** in the event's `detail`, so a rewrite is not invisible
to the person who raised it.

### Edge cases this covers

- **Two moderators correct the same sentence.** Both are kept — they may have spotted
  different things. The panel shows existing corrections on a passage *before* you write a
  new one, and marks the overlap. Not blocked, but never silent.
- **A moderator is revoked.** Their corrections stay. The work belongs to the book, not to
  them; attribution is preserved and their open proposals still await an admin decision.
- **The admin raises corrections too.** Admin implies moderator, so they land in the same
  queue, and `decided_by` is still recorded when they accept their own.
- **Attribution shown to other moderators** uses the display name where one exists, falling
  back to the address. Email is a privilege bit in this app; it is not shown for decoration.

### Comments — added 2026-09-21 at Asif's request

Originally recorded here as "deliberately not built". Asif then asked for it: **every moderator and admin may
comment on any correction, whatever its status and whoever raised it — that is how moderators discuss each
other's work without being able to change it.** Commenting never touches the correction, so it needs no authority
over it. A comment is its author's own: only they, or an admin, can remove it (soft delete, audited). Plain text
only, capped at 2,000 characters, never rendered as markup. Table `correction_comment` (migration 0027).

| | Moderator, own | Moderator, another's | Admin |
|---|---|---|---|
| Comment | yes | yes | yes |
| Remove a comment | own only | own only | any |

### Route

```
route("book/:slug/corrections", "routes/book.$slug.corrections.ts")
```

Hangs off `book/:slug` for the same reason `marks` does — `requireUnitAccess` then reads
the **same** `params.slug` the page did. Middleware: `[requireUnitAccess, requireModerator]`.
Both gates positional, per `routes.ts` being the policy. Form-data `intent`s mirroring the
marks route: `propose`, `revise`, `withdraw`, `accept`, `dismiss`, `delete` — each one
calling `authority()` (§5a) before it writes. **Every write refuses while simulating**,
exactly as the marks action already does; while simulating, `isModerator` is false anyway,
so the panel is not even reachable.

---

## 6. Bringing in the source scan

### The conflict, stated plainly

`scripts/podcast/_listener_source_ref.py` deliberately leaves the source excerpt on disk:

> the excerpt because it is copyrighted source prose **no reader-facing surface should
> reproduce**

That decision was about **reader visibility**. The correction panel is not a reader-facing
surface — it is behind two gates and visible to a handful of named accounts. So the
resolution is to serve it, under the exact precedent `companion.server.ts` already set.

### The precedent to copy exactly

`companionFor` returns `[]` **without querying the database at all** unless
`viewer.isAdmin`, and it lives in **its own module** rather than in `catalog.server.ts`,
because that file states of itself that nothing in it asks who may see what.

So: **`app/server/sourceOcr.server.ts`**, its own module, gate inside the query, returns
`null` for a non-moderator without touching D1.

### It must never join `source_reference`

`source_reference` is reader-visible by design and has no gate inside its query — the row's
own existence is the only gate. Mixing the OCR text into that table, or that query, is how
a leak happens. Separate table, separate module, separate reader. Migration 0024:

```sql
CREATE TABLE source_ocr (
  slug       TEXT NOT NULL,
  anchor_key TEXT NOT NULL,
  page_range TEXT NOT NULL,
  ocr_text   TEXT NOT NULL,
  PRIMARY KEY (slug, anchor_key)
);
```

### Chunked per chapter, not per book

`_system/source/ocr/raw-extract.md` is ~550 KB for a single book. It ships **per chapter**,
paired to chapters the way `_listener_source_ref.py` already pairs them — by
`anchor_key(title)`, never by index, because every book gets a pipeline-written
"Introduction to the Book" chapter that shifts positional pairing by one. The panel then
fetches only the span for the chapter being read.

### Honest availability

**9 of 55 books have an OCR folder.** Most books instead have
`_system/source/text/refined-english.md` and `raw-extract.md`, which are the *extracted*
text and are often the more useful comparison anyway. The publisher should ship whichever
exists, **labelled for what it is** ("Scanned source" vs "Extracted source"), and a book
with neither simply has no rows — the pane then says so, rather than rendering an empty
box. Same degradation pattern as the source-reference toggle.

Writer: a new `scripts/podcast/_listener_source_ocr.py` beside its sibling, called from
`publish_to_listener.py`. Like everything else that script writes, it names **no privilege
bit**.

---

## 7. The round trip back to the repo

`scripts/podcast/pull_corrections.py <slug>`:

1. Read `status='accepted'` corrections from D1 (`wrangler d1 execute --remote --json`).
2. Resolve each to a chapter of `book/book.md` by `_book_edits.anchor_key` plus an exact
   quote match. **Ambiguous or missing ⇒ reported as orphaned, never guessed.**
2b. **Refuse on overlap.** Two accepted corrections whose spans touch the same passage are
   reported and neither is applied — applying both in sequence would feed the second one a
   sentence the first had already changed. §5a keeps both rows on purpose, so this is the
   place that has to notice.
3. Apply through `_book_edits` — the same path a Composer save takes — so the edit lands in
   `_system/composer-edits.json` and **survives a re-compose**. The existing rule that a
   chapter carrying a Composer edit is not regenerated then protects it.
4. Stamp `status='applied'`, `applied_at`.
5. Normal `compose → publish → deploy` carries the corrected prose back to the Library.

Two existing guards that apply unchanged: the **marks-only vowelling gate**
(`_vowelling.rejection_reason`) for any Arabic correction, and the **90% word-retention
gate** (`_verbatim_correct`) for a Sessions- or Audiobook-lane book, whose prose is timed
against a recording.

An admin queue at `/admin/corrections` gives the cross-book view: every open correction,
grouped by book, with accept/dismiss and the pull command to run.

---

## 8. Gates

| Gate | What gets added |
|---|---|
| `npm run security` | Non-moderator hits `/book/:slug/corrections` → 404, **with an admin control proving the data is there** (the shape the Companion leak test already uses). A forged moderator cookie under simulation. A book with `under_moderation=1` invisible to a plain reader and present for a moderator. |
| `test/routes.test.ts` | New route is under both gates; exports no `ErrorBoundary`. |
| New `test/corrections.test.ts` | Corrections are **shared, not per-user** — the inverse of `marks-isolation.test.ts`, and pinned so nobody "fixes" it. Plus the whole §5a table as cases: moderator B cannot revise, withdraw, accept, dismiss or delete moderator A's row; a moderator cannot revise their own once it leaves `open`; an admin can do all six; every one of those writes an `access_event`. |
| New `test/moderator.test.ts` | Admin implies moderator; simulation forces it false; a missing/revoked row fails closed. |
| `npm run controls` | Presses the Correction button and every control in the panel. |
| `npm run check` | typecheck · lint · format · ratchets · test · build. |
| `npm run smoke` / `shots` | New panel at desktop and mobile, light and dark. |

**Scope note:** `npm run lint:views` and `html-view-challenger` govern the **Astro site**
(`plan-dashboard/`) and do **not** apply to `listener/` — the Library has its own
equivalents, listed above. Do not bolt one onto the other.

---

## 9. Build order

> **Superseded by §9c-D** after the holistic review. Kept for the record of what changed.

Each phase is independently shippable and independently testable.

| # | Phase | Ships |
|---|---|---|
| 1 | Moderator role | Table, session field, `requireModerator`, `/admin` grant UI, security tests. No reader change. |
| 2 | Under moderation | Column, `VISIBLE_SQL` clause, shelf ribbon, `/admin/content` toggle. |
| 3 | Capture corrections | Table, SelectionBar strip, `SidePanel` host, editor, route, and the §5a authority model. Useful on its own — corrections accumulate and are read in `/admin`. |
| 4 | Source scan | Publisher lane + gated reader + the source pane. |
| 5 | Round trip | `pull_corrections.py`, `/admin/corrections`, applied-status round trip. |

Phase 5 is what makes the feature *finished*; phases 1–3 are what make it *usable*.

---

## 9b. Handing corrections to AI — review first, then apply

**Principle:** the AI never decides. It *reads and advises*; an admin still accepts (§5a);
and applying an accepted correction to the book goes through the same Composer path and the
same gates as everything else (§7). What the AI removes is the *reading* — the admin opens
a card that already says whether the source agrees, and why.

### Where it runs — and where it must not

**Not in the Worker.** The Library is a Cloudflare Worker with no book on disk, no source
scan, no glossary, and no way to run `claude -p`. Everything the AI needs to judge a
correction lives in the repo, so the AI runs where the repo is, exactly as the
student-reader lane already does (`claude -p` on the Max subscription). The Library
stores the *verdicts*, never the model call.

```
Library (D1)                          Repo (this machine)
────────────                          ───────────────────
correction  ──open, unreviewed──▶  build_correction_packets.py
                                        │  one packet per correction
                                        ▼
                                   deterministic gates   (zero model spend)
                                        │  survivors only
                                        ▼
                                   correction-reviewer agent   (claude -p, batched per chapter)
                                        │  verdict per packet
correction_review  ◀──verdicts──────────┘
        │
   admin reads card → accepts / dismisses            (§5a — unchanged)
        │
correction(status=accepted) ──▶ pull_corrections.py ──▶ _book_edits ──▶ compose ──▶ publish
```

### The packet — everything the reviewer needs, and nothing it doesn't

One JSON file per correction at
`content/<Bucket>/<slug>/_system/corrections/packets/<correction-id>.json`, **built
deterministically from disk** — never by asking a model to go and find things.

| Block | What it holds | Why the AI needs it |
|---|---|---|
| **The claim** | quote, proposed text, kind, the moderator's rationale, who, when | What is being asserted |
| **The passage** | the chapter paragraph ±1, quote marked; chapter title + `anchor_key` | To judge the change in place, not in isolation |
| **The source** | the matched span from `source_ocr` / `refined-english.md` / `raw-extract.md`, page range, and **which of those it is** | The evidence. Labelled scan vs extracted, because a scan can carry an OCR error and extracted text is already interpreted |
| **The book's rules** | `narrative_frame`, `deliverable_mode`, `book_voice`, lane, `content_profile` | "Said" → "wrote" is a narrator question; a first-person book and a transmitted report answer it differently |
| **The vocabulary** | glossary entries (`_system/glossary.yml`) for every Arabic term in the span | So it doesn't "fix" a deliberate rendering |
| **Prior knowledge** | `arabic-verify-flags.json` entries touching this span; earlier Composer edits to this chapter; other corrections overlapping this passage | Don't re-litigate a settled point; don't collide with a human edit |
| **Gate results** | the deterministic checks below, already run | The AI is told what is already proven, so it spends nothing re-checking it |
| **Packet hash** | SHA-256 of the claim + passage + source | Detects a stale verdict when a proposal is edited after review |

**Why a packet, not "give the AI the repo".** A packet is small (a few KB, not a 600 KB
book), reproducible, cheap to cache, and auditable — you can read exactly what the model
was shown. An AI that goes looking for context will find different context each run.

### Two layers, in this order

**Layer 1 — deterministic gates, zero model spend.** These run first and can reject or
annotate before any tokens are spent. All already exist; nothing is reimplemented:

| Check | Existing home |
|---|---|
| Quote resolves to exactly one place | `_book_edits.anchor_key` + exact-match (§7 step 2) |
| Overlaps another live correction | §7 step 2b |
| Arabic change is marks-only, skeleton intact | `_vowelling.rejection_reason` |
| Narrative-frame integrity (person, speech tags, script retention, enumerations) | `_narrative` BK-N1–N7 |
| Word retention ≥ 90% on spoken-lane books | the `_verbatim_correct` gate |
| Chapter already carries a Composer edit | `_book_edits.edited_chapter_keys` |

A failure is recorded as `verdict: reject` with the gate's own message, **no model call
made**. A correction that cannot resolve to one place cannot be reviewed by anyone, human
or AI — so this is also the cheapest possible moderator feedback ("your selection matches
3 places — select a longer phrase").

**Layer 2 — the `correction-reviewer` agent, for what a rule cannot ask.** New agent, spec
in `infra/claude-agents/correction-reviewer.md` (canonical; the `.github`, `.codex` and
per-machine copies are generated by `sync-agent-wrappers.sh`, never hand-edited). It asks:

1. Does the **source** support the proposed wording? (scan first; extracted text as a check)
2. Is the proposed wording **articulate** in the book's own voice (REQ-BA-*), or does it
   stiffen the prose?
3. Is this an **improvement or a preference**? A moderator's taste is not an error.
4. Would this change **ripple** — same word wrongly rendered elsewhere in the chapter?

Structured output, per packet:

```json
{
  "verdict": "supports | revise | reject | needs_human",
  "confidence": "high | medium | low",
  "summary": "plain English, two sentences, what a person reads",
  "suggested_text": null,
  "evidence": [{"kind": "ocr", "page": 14, "excerpt": "..."}],
  "ripples": [{"anchor_key": "...", "quote": "..."}],
  "checks": [{"id": "source-span", "result": "ok|warn|no", "note": "..."}]
}
```

- `revise` carries a `suggested_text`. The admin can take it in one press; **it goes
  through the same gates** as a human's proposal, so the AI cannot smuggle in a change the
  gates would refuse.
- `needs_human` is a **first-class outcome**, not a failure. "The scan is cut off here"
  is the honest answer and is worth more than a confident guess on a religious text.
- The reviewer is told to prefer `needs_human` over a low-confidence `supports`.

### Efficiency — where the savings actually come from

| Lever | Effect |
|---|---|
| Gates before the model | Unresolvable / overlapping / gate-failing corrections cost nothing |
| **Batch per chapter** | One call reviews every open correction in a chapter; the chapter window, glossary and rules are sent **once**, not per correction |
| Packet hash | Unchanged since last review → skipped. Editing a proposal re-queues only that one |
| Subscription, not API | `claude -p` on the Max plan, per the repo's standing pattern — no per-token bill |
| Read-only by construction | The reviewer's tools are `Read` only. It cannot edit `book.md`; the worst it can do is give a wrong opinion, which an admin can see and overrule |
| Cap on batch size | A chapter with 40 open corrections is split, so one bad window can't poison the rest |

**One PAID exception, as in the student-reader lane:** none by default. A passage the
source cannot ground yields `needs_human`; it does **not** trigger a web search. Reaching
outside the library for a religious text is a decision for a person.

### Storage — migration 0025 (with the panel's tables)

```sql
CREATE TABLE correction_review (
  correction_id  TEXT NOT NULL,
  packet_hash    TEXT NOT NULL,          -- stale if the correction has since changed
  verdict        TEXT NOT NULL CHECK (verdict IN ('supports','revise','reject','needs_human')),
  confidence     TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
  summary        TEXT NOT NULL,
  suggested_text TEXT,
  detail_json    TEXT NOT NULL,          -- evidence, ripples, checks
  source_kind    TEXT NOT NULL,          -- 'ocr' | 'extracted' | 'none'
  model          TEXT NOT NULL,
  reviewed_at    TEXT NOT NULL,
  PRIMARY KEY (correction_id, packet_hash)
);
```

Keyed on `(correction_id, packet_hash)`, so a proposal edited after review shows **no
stale verdict** — the panel reads only the row whose hash matches now. History is kept.

**Read rule:** every moderator and admin sees the verdict (same shared-queue rule as §5a).
The **writer** is the repo-side script only, over `wrangler d1 execute`; no HTTP route
writes it, so no account — admin included — can forge an AI opinion from the browser.

### The apply step

`pull_corrections.py` (§7) reads `status='accepted'` only. It treats a `revise` suggestion
the admin took as an ordinary correction, applies through `_book_edits.record_edit`, and
stamps `applied`. **Auto-accept is deliberately not built.** A "high-confidence supports
⇒ accept automatically" rule is the obvious next request, and it removes the one human
hand from a religious text; if it is ever wanted, it should be a per-book, per-kind switch
that an admin sets, defaulting off.

### Gates for this layer

- `test_correction_packets.py` — packet is deterministic (same inputs → same hash); every
  block present; a book with no source yields `source_kind: none`, not an error.
- `test_correction_review.py` — a gate failure produces a reject **with no model call**
  (the call is stubbed and asserted not to fire).
- The reviewer's tool list is asserted to contain no write tools.
- `npm run security` — no route accepts a write to `correction_review`.
- `repo-surgeon` agent-mirror parity covers the new agent spec.

### Build order — slots between phases 4 and 5

| # | Phase | Ships |
|---|---|---|
| 4b | Packets + Layer 1 | `build_correction_packets.py`, deterministic gates, verdicts for gate failures. **Useful with no AI at all.** |
| 4c | The reviewer | `correction-reviewer` agent, batching, `correction_review` table, verdict on the card |

4b first on purpose: it delivers the cheap, certain half — and tells you how many
corrections even *need* a model — before any model is wired in.

---

## 9c. Holistic review — what the plan missed, and what would make corrections faster

Method: walked one correction from the moment a moderator selects a word to the moment a
reader sees the fixed sentence, then walked every *other* thing that touches that sentence.
Each finding below was checked against the code, not assumed.

### A. Gaps in the plan — must be fixed

| # | Gap | Why it bites | Fix |
|---|---|---|---|
| A1 | **§3 gave moderators no way to see a draft book** (corrected above) | The feature's main use-case — moderating a book before it is live — would not have worked | Two-branch `VISIBLE_SQL` |
| A2 | **Applying a correction orphans readers' own marks.** `anchor.ts` resolves a highlight by its quote and returns `orphaned` when the quote is gone. Fix the sentence and every reader who highlighted it silently loses that highlight to the "orphaned" list. Companion cards anchor the same way | The tool that improves the book damages readers' data | On apply, store `(anchor_key, old_quote → new_quote)`. `resolveAnchor` consults that map when a quote is missing and relocates to the new wording. Never guess — only an exact recorded substitution |
| A3 | **Accept has a race.** A moderator can edit a proposal in the instant an admin presses Accept; what is applied is not what was read | Breaks "what I approved is what ships" | Accept carries the `updated_at`/packet-hash the admin *saw*; a mismatch refuses with "changed since you looked" |
| A4 | **Stored rationale HTML is rendered to an admin.** A moderator is trusted, but stored markup shown to the higher-privileged account is a classic escalation path | XSS from moderator to admin | Sanitise **on write, server-side**, through the existing `sanitizeNote` (seven-tag allowlist, no attributes). Never trust the client editor |
| A5 | **Nothing stops a correction altering a Qur'anic verse.** The repo already resolves verses against the canonical mushaf (`_mushaf.is_quranic`) | A "typo fix" on scripture is not a typo fix | Packet carries `is_quranic`; any correction whose span is mushaf-resolved and changes letters is **auto-routed to `needs_human`**, never reviewed by AI, never applied by script |
| A6 | **Read-along timing.** Audiobook and Sessions books have prose timed to a recording (`sync-read-along.mjs`). A fixed sentence can shift word timings | Read-along highlights drift after a correction | Apply step re-runs the read-along sync for changed chapters and reports any it cannot re-align |
| A7 | **Offline copies go stale silently.** `book/:slug/text` carries no version, so a reader who downloaded a chapter keeps the old wording forever | Fix ships; some readers never see it | Add a content version to the download; the device compares and shows "updated — re-download" |
| A8 | **Podcast/slide lanes are not fed by `book.md`** (verified: `build_episode_txt.py` and `extract_chapter.py` never read it). A fix to the reading edition does **not** reach audio or slides | A corrected book with an uncorrected podcast | Out of scope to auto-fix, **not** out of scope to say so: the packet flags "this passage also appears in `chapters/ch04.txt`", and the card tells the admin the audio lane may still carry the old wording |
| A9 | **Putting a *live* book under moderation yanks it from readers**, and hides their bookmarks and progress | Surprising and disruptive | **Decided 2026-09-20 (Asif): for now, only `isaf-al-talib` is placed under moderation.** No general rule for live books is being designed yet. Two consequences are built regardless of scope: the `/admin/content` toggle **states how many readers hold marks or progress in the book before it confirms**, and their marks are kept (only hidden) so lifting moderation restores them exactly |
| A10 | **No exit from "under moderation".** The plan defines entering it, not leaving it | A book would sit there forever | Defined lifecycle in B4: the flag can be lifted when every chapter is marked reviewed and no correction is open |

### B. Features that would make correcting a book faster

Ordered by how much time each saves. **Tier 1 changes how fast a whole book is corrected; the
rest polish it.**

**Tier 1 — build with the core**

| # | Feature | What it does | Evidence it is worth it |
|---|---|---|---|
| B1 | **Pre-filled suggestions ("sweep")** | The pipeline's existing audits produce candidate corrections *before any moderator looks*. They arrive in the queue as `suggested`, and a moderator **confirms or dismisses with one tap** instead of finding the error first | `isaf-al-talib` already has **126** such entries in `arabic-verify-flags.json`, each with chapter, quote, suggested wording, certainty and page — almost exactly a correction. Finding is the slow part; this removes it |
| B2 | **"Fix everywhere" (ripple)** | When a correction is a repeated error — a term rendered wrongly throughout — the panel lists every other occurrence with a checkbox and submits them as **one** batch, all reviewed together | One term wrong 14 times is 14 corrections otherwise. The AI reviewer already returns `ripples`; this makes them actionable |
| B3 | **Chapter review checklist + claim** | A moderator marks a chapter "I've reviewed this" (or claims it, so two people don't read the same one). Per-book progress: "18 of 27 chapters reviewed" | Without it, a book with zero corrections is indistinguishable from a book nobody read. Also feeds B4 |
| B4 | **A defined way out of moderation** | An admin can lift the flag when every chapter is reviewed and zero corrections are open; the panel shows exactly what still blocks it | Closes A10 |
| B5 | **Keyboard triage for the admin** | A queue across all books: `j/k` to move, `a` accept, `d` dismiss, `e` edit; bulk-accept every AI-supported correction in a chapter after a glance | Reading 40 corrections one card at a time is the admin's bottleneck |
| B6 | **Decision note** | Dismissing (and rejecting an AI suggestion) takes an optional one-line reason the raiser sees | Moderators learn what you want; stops the same mistaken correction being raised again |
| B7 | **Quick fix** | Selecting a single word or a few letters offers an inline one-field edit, without opening the whole panel | Most corrections are one-word typos; the full form is heavy for them |

**Tier 2 — high value, after the core works**

| # | Feature | What it does |
|---|---|---|
| B8 | **Compare mode** | A reader toggle that shows the scanned source page beside the chapter, scrolling together. Moderators *read against the source* instead of select-then-check |
| B9 | **Promote to glossary** | A correction of kind "term" can also update `_system/glossary.yml` (and, if wanted, the cross-book library, as `pronunciations.jsonl` already does), so the same error stops recurring in every future compose and every other book |
| B10 | **Systemic detector** | Three or more corrections with the same shape on one book are surfaced as **a pipeline defect**, not three fixes, and written to the `_learning/findings.jsonl` ledger so `podcast-trainer` can fix the cause. Mirrors the repo's existing "systemic-fixes-from-chapter-archetype" rule |
| B11 | **Republish preview** | Before `pull_corrections.py` runs, show the whole-chapter diff of what will change, and one command to apply every accepted correction for a book, re-verify each quote survived, and stamp them `applied` |
| B12 | **Source-quality badge** | The source pane says how trustworthy the scan is (clean / noisy / handwritten). Verified need: `isaf-al-talib`'s own source is a handwritten Urdu PDF where OCR is known to be weak — the panel must not present it with the same confidence as a clean scan |

**Tier 3 — nice, not needed now:** listen-to-the-moment for audio-lane books (play the recording at the corrected sentence); a daily digest to the admin ("5 new on 2 books"); moderator activity summary.

### C. Deliberately not added

Auto-accept (stays off, per 9b); discussion threads on a correction; letting moderators change the source text or glossary directly; any write path to the Library's own chapter table.

### D. Revised build order

| # | Phase | Ships |
|---|---|---|
| 1 | Moderator role | Table, session field, gate, `/admin` grant UI, tests |
| 2 | Under moderation | Column, **two-branch `VISIBLE_SQL` (A1)**, shelf ribbon, `/admin/content` toggle |
| 3 | Capture | Table, bar strip, panel, editor, route, §5a authority, **accept-race guard (A3), server-side sanitising (A4)**, quick fix (B7), decision notes (B6) |
| 4 | Source | Publisher lane, gated reader, source pane, **quality badge (B12)** |
| 4b | Packets + deterministic checks | **incl. Qur'anic guard (A5), other-lane flag (A8)** |
| 4c | AI reviewer | Agent, batching, `correction_review` |
| 5 | Round trip | `pull_corrections.py`, republish preview (B11), **mark re-anchoring (A2), read-along resync (A6), offline versioning (A7)** |
| 6 | Speed | Sweep suggestions (B1), fix-everywhere (B2), chapter checklist + exit (B3, B4), keyboard triage (B5) |
| 7 | Compounding | Compare mode (B8), glossary promotion (B9), systemic detector (B10) |

Phase 6 is where a book goes from *"moderators hunt for errors"* to *"moderators confirm
errors the pipeline already found"* — the largest speed-up in the plan, and the reason it is
its own phase rather than an afterthought.

---

## 9d. Rollout scope (decided 2026-09-20)

Under-moderation is switched on for **one book only: `isaf-al-talib`**. Everything else stays
as it is. Consequences worth stating plainly:

- The **mechanism is still built generally** (a column and a toggle), because a special case
  for one slug would be a second code path. What is limited is *use*, not capability.
- `isaf-al-talib` is **already published to the Library** (its production record is
  `verified: true`). Turning moderation on therefore **hides it from every reader who can
  open it today** and leaves it visible to moderators and admins only. This is the intended
  effect, and the toggle's reader count (A9) is there so it is never a surprise.
- It has a ready-made head start: **126 existing Arabic-verification findings** for exactly
  this book — the raw material for the pre-filled suggestions in B1.
- Its source is a handwritten Urdu PDF with weak OCR, so it is also the book that most needs
  the source-quality badge (B12).

## 9e. What was built, phase by phase (2026-09-20)

| # | Phase | State | Where |
|---|---|---|---|
| — | Root cause: diacritics in source headings | Fixed and gated; 8 books cleaned | `_latin_plain.py`, `_listener_source_ref.py` |
| 1 | Moderator role | Built, tested, verified in the real site | `moderation.server.ts`, `admin.moderators.tsx` |
| 2 | Books under moderation | Built; `isaf-al-talib` held locally | `access.server.ts` (`visibleSql`), `admin.content.tsx` |
| 3 | Capture: button, panel, list, permissions | Built, tested, verified | `CorrectionLayer.tsx` and friends, `corrections.server.ts` |
| 4 | Source beside the correction | Built; 585 pages published locally | `_listener_source_ocr.py`, `sourceOcr.server.ts` |
| 4b | Packets and deterministic gates | Built (100 Python tests) | `_correction_packets.py` |
| 4c | AI reviewer | Built; **one real batch run** (2 of 33 corrections) | `correction-reviewer.md`, `review_corrections.py` |
| 5 | Round trip | Built; dry-run proven on real data; **`--apply` not yet run on a real book** | `pull_corrections.py` |
| 5 | Marks survive; offline copies refresh | Built and tested | `substitutions.server.ts`, `book_version` |
| 6 | Speed: suggestions, fix-everywhere, checklist, keyboard triage | Built; 33 suggestions imported locally | `import_correction_suggestions.py`, `admin.corrections.tsx` |
| 7 | Compounding: source tab, systemic detector, glossary candidates | Source tab built; detector and candidates are report-only | `SourcePane.tsx`, `pull_corrections.py` |

### Known limits — said plainly

- **Not exercised against the deployed site or a real `--apply`.** The apply step writes through the Composer
  and has been proven only on fixtures and as a dry run against the real book.
- **The AI reviewer has run on 2 of 33 corrections.** The other 13 batches (about 460 KB of prompt in total) were
  dry-run only; running them spends subscription time and is Asif's call.
- **Read-along timing** is reported, not fixed: `sync-read-along.mjs` copies a code file rather than re-syncing a
  book, so for narrated books the script prints the real command (it costs Azure speech).
- **The scan-vs-English highlight** only works on the extracted text; a scan cannot be matched to an English quote.
- **The audio and slide lanes are not fed by `book.md`.** A correction to the reading edition does not reach them;
  the pull step reports where the old wording remains.
- **Sweep suggestions are conservative.** Of 81 open findings, 48 were skipped because they are instructions to a
  person rather than replacement wording, carry editorial notes, or would fail the Arabic gate.
- **`revoice_gates` is stricter than it looks for corrections:** its "abridged" check rejects a correction that deletes
  more than 40% of a short paragraph, and it needs at least 8 words.
- **Untested seams:** the real `wrangler` call with multi-statement batches (SQLite accepts them; wrangler has not seen
  these), and the source-page choice for the reviewer when no audit flag names a page (a proportional estimate).

---

## 10. Still open

**Does an accepted correction change the live site immediately, or only after a republish?**

*Picture this.* A moderator is reading chapter 4 of Isaf al-Talib fi Jami al-Matalib and finds "the Imam said"
where the Arabic plainly says "the Imam wrote". They select it, press **Correct this
passage**, type the fix, and Asif accepts it that evening.

- **Proposal-only (recommended).** The live site still says "said" until Asif runs
  `pull_corrections.py`, re-composes and deploys — maybe next weekend. In exchange, the web
  reader and the printed PDF are *never* allowed to disagree, and there is exactly one place
  a sentence is authored.
- **Live-fix.** The web reader shows "wrote" within seconds. But the PDF still says "said"
  until the next compose, and the Library now holds prose that `book.md` does not — which
  is the divergence §1 was written to prevent, and the next `publish_to_listener.py` run
  would quietly overwrite it unless a whole override layer is built to stop it.

Recommended: **proposal-only**, because the alternative reintroduces exactly the divergence
the singular-Composer rule exists to forbid, and the cost of that divergence is a religious
text whose print and web editions say different things.
