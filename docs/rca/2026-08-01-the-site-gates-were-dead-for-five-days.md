> Template from: Betsy Beyer, Chris Jones, Jennifer Petoff, and Niall Richard Murphy. ["Site Reliability Engineering."](https://landing.google.com/sre/book/chapters/postmortem.html).

# The site's CI gates were dead for five days (RCA-009)

### Date

2026-08-01 (incident window: 2026-07-27 04:34 PM – 2026-08-01 03:20 PM EST)

### Authors

Claude (investigation + fix), reviewed by Asif

### Status

RESOLVED 2026-08-01. All eight corrective actions closed the same day. The
`lint` workflow is GREEN on all three jobs for the first time since at least
2026-07-27, breaking a streak of 60+ consecutive failures.

The install step no longer depends on a property the lock file cannot have; the
four defects the restored gates exposed are fixed; the blind window has been
swept; and a sustained-red-CI signal now fires at session start, which is where
this would have been caught on day one.

### Summary

The `lint` workflow — which carries **five** of the site's quality gates,
including the deterministic half of the mandatory runtime + visual-QA gate —
failed on 60 consecutive runs on `develop` without a single success. Every run
died at `npm ci` before executing anything.

The cause is a property of npm that no amount of regenerating can fix:
`npm ci` refuses to install unless `package-lock.json` describes the complete
ideal tree for the runner's platform, and a lock generated on darwin-arm64
structurally cannot describe ubuntu-x64's.

This is the **second** occurrence. The identical failure was diagnosed and
"fixed" on 2026-07-21 by regenerating the lock (`ef325f2`, whose message opens
"`npm ci` refused to run at all — the committed lockfile was missing
@emnapi/core and @emnapi/runtime"). That fix held for **one day**.

### Impact

Five gates did not run on any commit to `develop` between 2026-07-27 and
2026-08-01: ESLint, Prettier, `astro check`, the site unit tests, and the
Cortex HTML-view quality gate. The sixth and most serious is the runtime smoke
job, which boots the dev server and hard-fails on any console error, uncaught
exception, failed request, or 5xx — the gate that exists precisely because the
static checks cannot see runtime breakage.

Every site change in that five-day window shipped behind local pre-commit checks
only. No runtime defect is currently known to have shipped, but that statement is
weaker than it sounds: for five days nothing was in a position to find one. The
post-fix sweep is AI-3.

`podcast-e2e` was unaffected and green throughout; the pipeline suite never
depended on this workflow.

### Root Causes

**1. `npm ci`'s contract cannot be met by a cross-platform lock file.**
`@tailwindcss/oxide-wasm32-wasi` and `@img/sharp-wasm32` are the **wasm fallback**
bindings, and they declare `@emnapi/core`, `@emnapi/runtime` and
`@emnapi/wasi-threads` at caret ranges. Resolving on darwin-arm64 never reaches
that subtree, so npm neither writes those entries nor keeps them. Verified three
independent ways on 2026-08-01:

- a clean `npm install --package-lock-only` on macOS produces a lock with **two**
  `@emnapi` entries, fewer than the committed one;
- adding `--os=linux --cpu=x64 --libc=glibc` does not change that;
- grafting the four missing entries back by hand and letting npm normalise
  **prunes all four again**.

A Linux-generated lock is therefore not a durable fix: the next local
`npm install` strips it. That is exactly what happened to `ef325f2`.

**2. The 2026-07-21 fix was verified in the environment that cannot fail.**
That commit's verification line reads "npm ci from scratch" — run on macOS,
where `npm ci` passes with the incomplete lock. The check that would have shown
the fix did not hold was the one nobody could run locally. The failure is
observable *only* on Linux, and the only Linux available is the CI that was
being fixed.

**3. Nothing escalated 60 consecutive red runs.** The workflow had been red for
five days across dozens of pushes. There is no alerting on sustained CI failure,
and a red badge on a workflow that is not the pipeline suite was evidently easy
to walk past. It surfaced only because an unrelated post-merge audit went looking
at CI after a push.

### Trigger

`@emnapi` published versions past the caret ranges (`runtime`/`core` 1.11.3,
`wasi-threads` 1.2.3). Until then npm on Linux could satisfy the unpinned ranges
with what it already had; afterwards it resolved them fresh, found no lock entry,
and failed. The latent defect had existed since `ca21cb8` (2026-07-22) took the
lock from 10 `@emnapi` entries to 6.

### Resolution

Both jobs now install with `npm install --no-audit --no-fund` instead of
`npm ci`. `npm install` has no whole-tree sync requirement, so it cannot fail
this way on any platform. Every version the lock does pin is still honoured;
only the handful of entries the lock structurally cannot carry are resolved
fresh. For a lint + smoke gate that publishes nothing, that is the correct
trade — and unlike regenerating the lock, it does not decay the next time
anyone runs `npm install` on a Mac.

The reasoning is recorded as a comment at the install step itself, ending in an
instruction not to revert it without reading this RCA — because the obvious
"cleanup" a future reader will reach for is restoring `npm ci`, which is what
this incident is.

### What the restored gates immediately found

Fixing the install did not turn the workflow green — it turned it *informative*.
The first run that got past `npm ci` failed on three real defects that the dead
gate had been hiding. Both are fixed in the same commit as the install change.

**A fresh clone could not build the site's own editor package.**
`@asifhussain/prose-editor` is a local workspace package whose `dist/` is
gitignored, and its `package.json` declared `prepack` but not `prepare`. npm runs
`prepack` only on pack/publish; `prepare` is what runs after installing a
workspace dependency. So on any machine without a previously-built `dist/`, every
import of the package failed — **two site test files and five SSR Studio routes
(`edit`, `compose`, `book`, `preview`, `arabic-review`) returning 500**. It works
on Asif's machine solely because `dist/` is already on disk there. Adding
`prepare` makes a fresh clone self-sufficient; verified by deleting both
`node_modules` and `dist/` and reinstalling from nothing.

This defect is older than the blind window. It has been latent since the package
was scaffolded on 2026-07-26 and could only ever have been caught by a gate
running on a clean checkout — which is precisely the gate that was down.

**An unpinned linter upgraded itself into a failure.** CI installed `ruff`
unpinned. Ruff 0.16 began formatting Python fenced blocks inside Markdown, taking
`ruff format --check` from 584 files to 789 and failing five plan/spec/standard
DOCUMENTS that nobody had touched. Confirmed by A/B: 0.15.0 reports "584 files
already formatted", 0.16.1 reports "5 files would be reformatted, 789 already
formatted". Markdown is prose here, not source — its snippets are illustrative and
sometimes deliberately abbreviated — so `*.md` is now excluded in `pyproject.toml`,
and `ruff`/`mypy` are pinned so the next such change is a deliberate bump.

**Two more, found only once the smoke gate could speak.** The smoke runner
spawned the dev server with `stdio: "ignore"`, so a 5xx could be reported by URL
but never by cause — and the failures were not reproducible on macOS from a fresh
clone. Capturing that output (printed only on failure) named both immediately:

- **`pdftoppm` is a system binary the Composer preview shells out to.** Present
  on the author's Mac via homebrew, absent on a bare runner, taking
  `/studio/<slug>/preview` down with `spawnSync pdftoppm ENOENT`. CI now installs
  poppler-utils — the right fix over stubbing the page, because a smoke gate that
  skips the render path is not exercising the surface it claims to cover.
- **`knowledge.db` does not exist on a fresh clone.** `/api/studio/action-items`
  and `/api/studio/section-depth` both 500 in 0–1 ms — a throw at open, not a
  query — because `content/knowledge-base/knowledge.db` is gitignored and
  pipeline-built. Four routes (`edit`, `compose`, `book`, `arabic-review`) fail on
  it. **Open** as AI-7: what those endpoints should do without a database is a
  behaviour decision across 14 call sites, not a CI fix.

A local test appeared to rule `knowledge.db` out and was a false negative: the
file was moved aside while a dev server was already running, and sqlite does not
notice a file unlinked underneath an open connection. The same lesson as this
RCA's own, one layer down — a test that cannot fail proves nothing.

### Detection

An unrelated post-merge audit. After pushing 68 commits on 2026-08-01, a routine
check of the triggered CI runs showed `podcast-e2e` green and `lint` red — and
that the red run predated the push.

No monitoring detected this. No human reported it. Five days and dozens of
pushes produced no signal that anyone acted on.

### Action Items

| # | Action | Type | Owner | Status |
|---|---|---|---|---|
| AI-1 | Replace `npm ci` with `npm install` in both site jobs; document why at the call site | fix | Claude | DONE |
| AI-5 | Add `prepare` to `@asifhussain/prose-editor` so a fresh clone builds it | fix | Claude | DONE — verified from a deleted `node_modules` + `dist/` |
| AI-6 | Exclude `*.md` from ruff formatting and pin `ruff`/`mypy` in CI | fix | Claude | DONE |
| AI-7 | Install PyYAML so the repo-surgeon probe can run at all; capture dev-server output in the smoke gate; install poppler-utils | fix | Claude | DONE |
| AI-8 | Decide what the knowledge-database endpoints do when the database is absent | prevent | Claude | DONE — reads degrade per TABLE, writes refuse with a typed error; 4 tests pin absent / partial / built / no-create |
| AI-2 | Alert on sustained CI failure — N consecutive red runs on `develop` should surface, not wait for an audit | prevent | Claude | DONE — `start-session.sh` reports a workflow at 3+ consecutive failures; verified red AND green against live data |
| AI-3 | Sweep the site for runtime regressions that shipped while the smoke gate was blind (2026-07-27 → 2026-08-01) | mitigate | `site-health-sentinel` | DONE — desktop clean; 3 mobile-only defects found and fixed, class closed by INV-5 |
| AI-4 | Record in the RCA README that "verified locally" is not evidence for a CI-only failure mode | prevent | Claude | DONE — see Lessons |

### What the blind window actually cost

Desktop came through clean. Mobile did not: three groups of controls had no
reachable right half at 390px — the Composer's Paper picker and "Show changes",
the Companion's placeholder third line, and both LIVE Session pickers with their
chevrons 13px off screen.

The reason they shipped is worth more than the fix. They were **structurally
invisible** to the gate that was down, because the smoke run only ever measured
at 1440px. Even a fully working CI would not have caught them. So the honest
reading is not "five days of blindness let three defects through" — it is that
one of the gates had a blind spot of its own, and looking for regressions is
what found it. `INV-5` now re-measures at phone width and flags any control that
lands off-screen with no scrollable ancestor, verified in both directions.

### Lessons Learned

#### What went well

The second occurrence was recognised **as** a second occurrence. Checking the
lock file's history before regenerating it is what turned "run `npm install` and
push" into a real diagnosis — the 2026-07-21 commit message described this exact
failure, and seeing that the previous fix survived one day is what ruled out
repeating it.

The three-way verification (clean regenerate, platform-targeted regenerate, hand
graft) established that the lock *cannot* hold the entries, rather than assuming
it from one failed attempt. That is what justified changing the install strategy
instead of the lock.

#### What went wrong

A fix was declared on evidence that could not have distinguished success from
failure. "Verified: npm ci from scratch" is a true statement that carries no
information about a defect which only manifests on another operating system.

Six quality gates were wired to a single install step with no fallback, so one
unmet precondition took all of them out simultaneously — including the one gate
the standing rules call mandatory.

Five days of red CI passed unremarked. The gates were treated as protection
while producing no protection at all, which is worse than not having them:
changes shipped with the confidence of a green process that was never running.

#### Where we got lucky

The blind window contained no known runtime regression, and it ended because of
an audit aimed at something else entirely. Had the post-merge audit not looked at
CI after pushing, the gates would still be dead.

`podcast-e2e` is a separate workflow with a separate install path. Had the site
and pipeline suites shared one job, the pipeline gates would have gone down with
them — and the articulation defect fixed the same day (RCA-008) would have had
one fewer thing standing in its way.

### Timeline

| Time (EST) | Event |
|---|---|
| 07-21 08:08 AM | `ef325f2` — the same failure is diagnosed and fixed by regenerating the lock. 10 `@emnapi` entries. Verified with `npm ci` on macOS |
| 07-22 | `ca21cb8` — a macOS `npm install` regenerates the lock; entries drop 10 → 6. Silent |
| 07-26 | `5133957` — prose-editor scaffold; lock regenerated again, still 6 |
| 07-27 04:34 PM | First recorded red `lint` run. Latent until now because npm could still satisfy the unpinned ranges |
| 07-27 → 08-01 | 60 consecutive red runs. Dozens of pushes. No signal acted on |
| 08-01 02:43 PM | 68 commits pushed; post-merge audit checks CI and finds `lint` red — and red before the push |
| 08-01 03:00 PM | Reproduction attempt: `npm ci` **succeeds** on macOS. Platform-specific, not general staleness |
| 08-01 03:10 PM | Three-way verification proves the lock cannot carry the entries on this host |
| 08-01 03:15 PM | History check finds the 2026-07-21 fix and its one-day lifespan |
| 08-01 03:20 PM | Install strategy changed in both jobs; reasoning recorded at the call site |

### Supporting information

- The workflow: [.github/workflows/lint.yml](../../.github/workflows/lint.yml)
- Example failed run: `gh run view 30713164571 --log-failed`
- The prior occurrence: `git show ef325f2`
- Related: [RCA-008](2026-08-01-a-faithful-opening-was-reverted-as-if-invented.md) — the same day's other CI-visibility defect, where a content-only commit escaped the pipeline workflow's path filters
