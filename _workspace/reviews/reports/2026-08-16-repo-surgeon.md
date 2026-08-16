# repo-surgeon — 2026-08-16, `develop`

Scope: full sweep, all surfaces, plus the Pass 6 cleanup. Run after widening the
audit layer from the pipeline to every surface the project ships.

## Verdict

The pipeline and both web apps are sound. Four gate failures were real, three are
fixed, and two findings need Asif's ruling. 2.9 GB of disk reclaimed.

## What the audit itself gained

Seven probe groups, in a new module `scripts/repo_surgeon_checks.py`, all pinned by
49 tests (`tests/test_repo_surgeon_checks.py`, `tests/test_repo_cleanup.py`) —
the probe had none, so its own "break it and confirm it fails" rule had been
performed once per check and never again. Each new check was mutation-tested:
neutering it fails a test.

| Group | Proves |
|---|---|
| `CAP-*` | Every declared pipeline phase has a handler; every agent a doc invokes has a spec; every command a normative doc prints exists |
| `GT-*` | Every web app is named in the verify list, and every gate it declares is wired into CI, a hook, or that list |
| `RT-*` | The Library's route tree resolves both ways, owns its error boundary, and gates by position rather than pathname |
| `TS-*` | No committed `.only` silently disabling a suite |
| `CQ-*` | Each app has a lint config and a size ceiling; no debug output ships in a page |
| `HY-*` | Regenerable artifacts measured, not described |

Both web apps and the hygiene rules are now declared in `.repo-audit/profile.yaml`,
so no path or gate is restated in prose.

**The condition that prompted the widening:** the contract's verify list named the
pipeline and the Astro Site and was silent about the Podcast Factory Library. The
access-control probe on a private site had no home in any contract, hook or
workflow — it ran when somebody remembered.

## Defects found and fixed

| What | Where | Disposition |
|---|---|---|
| Front-end ratchets red — 1 new lint rule, 4 file-size regressions | `plan-dashboard` | 4 of 5 fixed |
| An unused destructured binding | `src/pages/studio.astro` | Removed |
| 1,054-line smoke runner over its ceiling | `scripts/site-health-smoke.mjs` | Layout invariants extracted to `scripts/lib/layout-invariants.mjs` (555 + 514) |
| 1,166-line renderer over its ceiling | `src/lib/reader/markdown.ts` | Inline-Arabic and quote-card concerns extracted (950 + 120 + 148) |
| 1,354-line print assembler past its pin | `scripts/lib/book-html.mjs` | `_system/` sidecar loaders extracted (1,234 + 150) |
| A long identifier overflowing a phone with no scrollable ancestor | `/claude-plans/<slug>` | `overflow-wrap: anywhere` on `.cp-prose` |

Every extraction re-exports from its original module, so no call site moved. The
quote-card design pin (`_quote_cards.py`) was repointed at both screen modules —
it failed on the move, which is the pin working.

**One regression introduced and caught by the gate that exists for it.** Deduping
a third copy of `QUOTE_KIND_LABEL` against its home in `quote-kind.mjs` pulled
`node:fs` into a browser bundle; four Studio routes threw on load. `npm run smoke`
found it. The local copy is restored with the reason it must stay local written
beside it — markdown.ts had said so, and the audit deduped against that note.

## Verified after

| Surface | Result |
|---|---|
| Python | 4,257 passed, 8 skipped · `make lint` clean · boundary, doc-links, both mirror gates clean |
| Astro Site | eslint clean · prettier clean · `astro check` 0 errors · 600/602 tests · `lint:views` 0 errors / 27 warnings · **smoke 39/39 routes clean** |
| Library | typecheck clean · 713/713 tests · build clean |
| Probe | 0 P0, 0 P1 |

## Open — Asif's ruling

**1. `/media/*` has no access check on localhost.** `npm run security` fails two
checks: an ungranted reader gets a book's media, and a media file that should 404
returns 200. Pre-existing — it reproduces with this audit's work stashed, and it
arrived with `3ce507ef` this morning. The dev-only Vite plugin claims `/media/*`
before React Router's middleware chain runs, and its header records the skip as
deliberate ("a concern that does not exist on a single developer's own machine").

*Production is unaffected*: the plugin is `apply: "serve"` so it cannot ship, and
the Worker's `/media/:slug/*` route sits inside `_authed` where `requireUnitAccess`
reads the same `params.slug` the page did.

The cost is that localhost no longer reflects production's access behaviour, and
the gate that proves access control works is permanently red. Not fixed here
because the obvious repair — teaching the plugin to resolve grants — would be a
SECOND implementation of the access rule, which is the thing `access.server.ts`
exists to prevent.

**2. `book-composer.ts` is 4,254 lines against a 4,129 pin.** Taken down from
4,369 by moving out the data-island types, the inert toolbar data and the
duplicated label map. The remaining 125 lines have no safe cut: the file is one
`boot()` closure and every candidate block reads six to nine sibling closures.
Recorded in the contract's `fragile:` list. Deliberately NOT re-pinned — raising a
shrink-only ceiling to clear a red gate is the one move the ratchet exists to
prevent.

**3. Two P2s the probe reports and will not act on.** The Podcast Factory Library
has no lint configuration (91 source files) and no size gate (106 files, largest
`Player.tsx` at 1,357). Both are scope decisions with a formatting commit or a
chosen number behind them.

## Pass 6 — cleanup

2.9 GB reclaimed; repo 14 GB → 11 GB.

| Category | Reclaimed |
|---|---|
| git maintenance (`git gc --prune=now`) | 1,507 MB — 48,070 loose objects → 0, 26 packs → 1, 61 garbage files → 0 |
| local R2 mirror | 1,358 MB |
| build output | 18 MB |
| python bytecode | 14 MB |
| tool caches | 0.8 MB |

The local R2 mirror was proved redundant before removal: in dev the Vite plugin
claims `/media/*` before the Worker's R2 path runs, and
`upload_listener_media.py` repopulates it. The local D1 was refused by the
contract's `protected_runtime` rule and is intact — Asif is still signed in on
localhost.

Refused on safety grounds: three `.DS_Store` files under `content/**`, which the
contract protects. Reported and never swept: `ayyuhal-walad/m4a` (270 MB) and
`kunooz-al-hikmah/source` (139 MB) — untracked working files, Asif's to keep.
