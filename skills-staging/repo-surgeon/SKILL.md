---
name: repo-surgeon
description: "podcast-factory's project-specific audit layer. Runs the generic `repo-audit` engine for structure, dead code, duplicates and debris, then adds the probes only this repo needs: gate integrity, the retired-surface ban, the four agent mirrors, the fixture-pinned TS/Python pairs, the book-pipeline invariants, and plan conformance. Backed by a deterministic probe script, so every claim it makes can fail. Invoke for 'repo review', 'architectural audit', 'cleanup sweep', 'find regressions', 'repo health check', 'plan conformance', '/repo-surgeon', '/repo-surgeon --scope podcast'."
---

# repo-surgeon — the project-specific half of a repo audit

## What this skill is, and what it deliberately is not

This skill is **not** a general audit engine. The generic engine is the `repo-audit`
skill: root sprawl, dead code, duplicate implementations, debris, dynamic-reference
safety, the capability manifest, the risk register, the approval gate, the visual-QA
loop, and the commit discipline all live there and are **not re-implemented here**.

repo-surgeon owns only what a repo-agnostic engine cannot know: the invariants that
are true of *this* repo. It runs as a layer inside `repo-audit`'s Phase 3.

> **Why the split exists.** Until 2026-07-27 this file carried its own copy of the
> generic engine, with the project facts hardcoded inside it. Of its 38 rules, 21 were
> dead, inert, or aimed at directories deleted in the May 2026 repo split — and one
> asserted every plan wave must appear in a view directory that no longer existed,
> manufacturing 35 false findings on every run. The duplicated half was the half that
> rotted, so it is gone. The lesson is recorded in `repo-audit`'s own Phase 0.5
> rationale, which quotes this file's correction note as its cautionary example:
> *a rule that flags real directories and blesses deleted ones is worse than no rule,
> because its output has to be ignored to get any work done.*

---

## Section 0 — Bootstrap (read first, in order)

1. **[.repo-audit/profile.yaml](../../.repo-audit/profile.yaml)** — the tracked project
   contract. Root allow-lists, protected paths, the verify list, the mirror pairs, the
   size gate and its ratchet, and the paths flagged fragile.
2. **[.repo-audit/waivers.yaml](../../.repo-audit/waivers.yaml)** — findings the owner
   has already ruled not-a-defect, with expiry dates.
3. **[CLAUDE.md](../../CLAUDE.md)** — branch policy, authorization tiers, and the
   standing operator rules this skill enforces.
4. **[docs/reference/skill-bootstrap.md](../../docs/reference/skill-bootstrap.md)** —
   the P0/P1/P2/P3 severity grammar.
5. **[docs/reference/cortex-challenger-framework.md](../../docs/reference/cortex-challenger-framework.md)** —
   the challenger framework this skill targets.
6. This file, end to end.

The three framework documents live under `docs/reference/`. This file pointed at a
bare `reference/` prefix until 2026-07-27, so its own first instruction had been
unfollowable for two months.

### Facts this skill does not restate

Every row below is read from the contract at run time. **Do not copy any of them into
this file.** That is precisely how the previous version rotted: the list drifted out of
step with the repo, blessed two surfaces the project brief bans, and omitted five
directories that actually exist — including `.repo-audit/` itself, so the audit contract
was flagged as clutter.

| Project fact | Lives in | Never in |
|---|---|---|
| What may sit at the repo root | `root.allow_files` / `root.allow_dirs` | this file |
| What must never be moved or rewritten | `protected` | this file |
| What proves a change safe | `verify` | this file |
| Which files must change together | `mirrors` (each with its `pinned_by` fixture) | this file |
| The size ceilings and their ratchets | `size_gates` | this file |
| What is deliberately odd and must be asked about | `fragile` | this file |
| The web apps, their source roots, gates and route policies | `apps` | this file |
| What may be reclaimed, and what may never be | `hygiene` | this file |

A contract entry that no longer resolves is a **P1 finding against the contract**, never
a silent obedience and never a silent drop. The probe checks this before trusting it.

---

## Execution model

```
repo-audit  Phase 0    orientation + stack detection
            Phase 0.5  contract read / bootstrap / validate
            Phase 1-2  digital twin + capability verification
            Phase 3    findings  <-- repo-surgeon's probes run HERE
            Phase 4-5  challenge, fit assessment, APPROVAL GATE
            Phase 6-7  execution, verification, contract write-back, commit
```

### Where the old passes went

The five-pass vocabulary is preserved because `CLAUDE.md`, `project-steward`, and
`.github/prompts/repo-health-check.prompt.md` all invoke it by name. What changed is
who executes each pass.

| Old pass | Now |
|---|---|
| Pass 1 — Structure | **Delegated.** `repo-audit` Phase 3, driven by the contract's root lists. Retained here: the retired-surface ban (`RS-*`), which is a project rule. |
| Pass 2 — Code | **Delegated.** `repo-audit` Phase 3 refactoring findings + its dynamic-reference safety rule. Six of the eight old rules audited deleted directories. |
| Pass 2b — Pipeline probes | **Retained.** This skill's core. See *Pipeline probes* below. Unchanged `AU-*` finding ids. |
| Pass 3 — Architecture | **Reshaped.** Only this repo's real invariants survive: agent-mirror parity across four homes, skill-registry completeness, generated-file parity. The old prompt-registry rules audited a server tree deleted in May. |
| Pass 4 — Brittleness | **Mostly delegated.** Retained here: the retired-surface ban and the hardcoded-branch-name ban. The old rules grepped `site/`, `server/`, `wrangler.toml` and journal-repo residue — none of which exist here. |
| Pass 5 — Plan conformance | **Retained and rewritten.** Five of its ten rules read plan keys that do not exist. See *Plan conformance* below. |

### Flags

| Flag | Effect |
|---|---|
| `--preview` | Findings + plan only, no execution. **Default.** |
| `--fix` | Execute the approved repair plan. Destructive ops still need confirmation. |
| `--scope podcast` | Pipeline + book-pipeline + capability probes. The post-merge sweep `CLAUDE.md` mandates. |
| `--scope apps` | The two web surfaces only — gates, routes, test hygiene, clean code. |
| `--plan-only` / `--pass 5` | Plan conformance only. |
| `--root-only` | Contract root-membership check only. |
| `--cleanup` | The closing hygiene pass. See *Pass 6* below. Always dry-run first. |

---

## The deterministic probe

**Run this first, every time:**

```bash
python3 scripts/repo_surgeon_probe.py
```

`--scope podcast` narrows it to the pipeline groups; `--json` emits machine-readable
findings. Exit 0 means no unwaived P0 or P1; exit 1 means there are; exit 2 means the
probe could not run.

**It is a live gate.** Since 2026-07-27 the probe runs in three places: the contract's
`verify:` list (listed first — it is the cheapest at ~0.6s, and a stale contract
invalidates the reasoning behind every gate below it), the pre-commit hook, and the
`lint` workflow. CI is what actually binds; a hook can be bypassed with `--no-verify`
and is absent on a fresh clone. It blocks on **P0/P1 only** — P2 and P3 report without
failing, so an advisory can sit in the backlog without holding up unrelated work.

It was deliberately left unwired until its baseline reached zero. A gate that fails on
a backlog somebody else created is a gate people learn to route around.

The script is the executable half of this catalog. It loads the contract, validates it,
applies waivers with expiry, and machine-checks every claim below that can be checked
deterministically. Findings sort by severity, then id, then path, then line — so two
runs on one tree produce one report.

**Everything the script checks, it checks; everything it cannot, this file describes as
requiring judgment.** Never assert a probe result you did not run, and never re-derive
by hand what the script already reports.

> **A gate you add must be able to fail.** After extending the probe, break the thing
> it guards, confirm it fails, and restore. The three checks added on 2026-07-27 were
> each verified this way. A check that cannot fail converts an unknown into false
> confidence, which is worse than no check.

### Checked by the script

| Group | Ids | What it proves |
|---|---|---|
| Contract | `CT-PATH`, `CT-RATCHET`, `CT-VERIFY` | Every path, ratchet, Makefile target and npm script the contract names still resolves |
| Mirrors | `MI-UNPINNED`, `MI-PIN-GONE`, `MI-PATH` | Every pair the contract says must change together has a fixture that exists |
| Root | `R1` | Root membership against the contract's exhaustive lists |
| Retired surfaces | `RS-RESURRECT` | `server/`, `site/`, `shared/`, `wrangler.toml`, `site-worker.js`, `docs/cloudflare/` stay deleted |
| Agents | `A2` | Canonical specs and their generated `.github` mirrors are the same set |
| Skills | `A1` | Every `skills-staging/` directory is registered and has a `SKILL.md` |
| Self-integrity | `SK-DEADREF`, `SK-MISSING` | Every relative link in this skill and its agent spec resolves |
| Pipeline | `AU-S2`, `AU-A2` | No machine-specific paths in pipeline source; no duplicated version constant has drifted |
| Book pipeline | `AU-V1`, `AU-V2`, `AU-V4`, `AU-V5`, `AU-V6` | The unified compose route is the only route, its schema mirrors agree, its stages exist, its governance ids resolve |
| **Capabilities** | `CAP-PHASE`, `CAP-AGENT-REF`, `CAP-CMD-REF` | Every phase the orchestrator declares has a handler; every agent a doc invokes has a spec; every command a normative doc prints exists |
| **Gate coverage** | `GT-APP-UNVERIFIED`, `GT-UNGATED`, `GT-MISSING` | Every web app is named in the verify list, and every gate it declares is wired into CI, a hook, or that list |
| **Routes** | `RT-DANGLING`, `RT-ORPHAN`, `RT-BOUNDARY`, `RT-PATH-GATE`, `RT-POLICY-GONE` | The Library's route tree — which IS its access policy — resolves both ways, owns its error boundary, and gates by position rather than by pathname |
| **Tests** | `TS-FOCUS` | No committed `.only`, which disables a whole file while the suite still reports success |
| **Clean code** | `CQ-NO-LINT`, `CQ-NO-SIZE-GATE`, `CQ-DEBUG` | Each app has a lint config and a size ceiling, and no debug output ships in a page |
| **Hygiene** | `HY-DEBRIS` | Regenerable artifacts are measured, not described |
| Plan | `L1`, `L2`, `L2-DUP`, `L10` | The plan parses, its wave references resolve, its ids are unambiguous, the ship checklist maps onto it |

`SK-DEADREF` is the check that would have caught this whole rot two months ago: it
asserts the audit's own references resolve. It exists because nothing did.

The seven bolded groups were added on 2026-08-16 and live in
[scripts/repo_surgeon_checks.py](../../scripts/repo_surgeon_checks.py) — a separate
module for the reason this catalog rotted in the first place, that nobody could
hold all of it at once. Each is pinned by
[tests/test_repo_surgeon_checks.py](../../tests/test_repo_surgeon_checks.py): one
synthetic tree carrying one defect, plus a clean-tree case, plus an empty-repo case
so no check can crash on a partial clone. That replaces the break-it-by-hand ritual
with something that holds after the person who wrote it has moved on.

### What the new groups deliberately do NOT re-check

Each of these questions already has exactly one answer, and a second one would be
worse than none:

| Already proven by | So the probe never re-asks |
|---|---|
| `listener/test/routes.test.ts` | whether every route sits inside the gate |
| `plan-dashboard/.../site-health-routes.test.mjs` | whether the smoke sweep covers every Astro page |
| `frontend-ratchets.json` + `check-dr005.py` | whether a file is over its ceiling |
| `npm run security` | whether an access-control bypass is reachable over HTTP |

What is added is the layer ABOVE them: whether each gate is **wired anywhere**.
That is the failure nobody notices, because a gate that runs only when somebody
types it is indistinguishable from a gate that passes — the exact condition that
left the Podcast Factory Library's access-control probe with no home in any
contract, hook, or workflow until this pass.

---

## Pipeline probes (`--scope podcast`, formerly Pass 2b)

**Scope:** `scripts/podcast/**/*.py`, `skills-staging/podcast/SKILL.md`,
`infra/claude-agents/*.md`, `_workspace/plan/**/*.md`, `CLAUDE.md`.
**Out of scope:** `plan-dashboard/` (the Astro site has its own gates — see *Gate
integrity*), `infra/azure/`, `node_modules/`, the sibling journal repo.

`AU-S2` and `AU-A2` are machine-checked. The rest need judgment and are the reason a
model runs this rather than a linter.

| ID | Axis | Severity | What to detect |
|---|---|---|---|
| AU-E1 | Efficiency | P1 | **Dead code** — modules nothing imports, scripts no agent or phase invokes. Build the call graph from `import` statements, `subagent_type` references, and `python3 scripts/podcast/X.py` invocations across every `.md` and `.py`. Apply `repo-audit`'s three dynamic-reference greps before calling anything an orphan. |
| AU-E2 | Efficiency | P1 | **Duplicate scripts** — overlapping responsibility. Cluster by function-name overlap, docstring topic, and read/write footprint. Check the contract's `fragile` list first: the dual snapshot generators are a deliberate, waived pair. |
| AU-E3 | Efficiency | P1 | **Validation duplication** — the same check in more than one place (em-dash, HTML comments, word-count bands). |
| AU-A1 | Accuracy | P0 | **Spec/code drift** — docs naming paths, scripts or constants that no longer exist. `scripts/check_doc_links.py` covers the normative docs; this probe covers the rest. |
| AU-A2 | Accuracy | P0 | **Version-constant drift** — a version pinned in both `_rules.py` and an agent spec. `podcast-challenger` is exempt by its own instruction: its spec tells the agent to read `CHALLENGER_VERSION` at run time rather than hardcode it, so there is no second copy to drift. Only genuinely duplicated pins are compared. |
| AU-A3 | Accuracy | P0 | **Registry/disk drift** — `_system/registry.md` rows whose slug matches no `chapters/ch##-<slug>.txt`, and chapter files with no row. |
| AU-S1 | Scalability | P1 | **Magic numbers** — ALL_CAPS literals that are configuration in everything but name. |
| AU-S2 | Scalability | P0 | **Hardcoded absolute paths** — `/Users/` or `/home/` in pipeline source outside test fixtures and state-file provenance. |
| AU-S3 | Scalability | P1 | **Cost-cap leakage** — a new paid API call that never reaches the orchestrator state's cost dict. |
| AU-X1 | Extensibility | P1 | **Hard-coded enums** — a category or status list of more than three elements appearing in more than one file, which should be a registry. |
| AU-X2 | Extensibility | P1 | **Missing plugin points** — the same shape in several places with no registration pattern. |
| AU-X3 | Extensibility | P2 | **Convention drift** — recent additions that do not match established naming, layout, or invocation patterns. |
| AU-H1 | Hygiene | P1 | **Folder-root sprawl** — files at a folder root outside vacuum's root-legit whitelist (`infra/claude-agents/vacuum.md`, the root-legit whitelist section). Report with `delegate_to: vacuum`. |

### Book pipeline conformance (`AU-V*`)

The unified book path must remain the sole compose route. Architecture:
[book-pipeline-plan.md](../../_workspace/plan/book-pipeline-plan.md); cutover state:
[book-pipeline-cutover.md](../../_workspace/plan/book-pipeline-cutover.md).

| ID | Severity | What to detect |
|---|---|---|
| AU-V1 | P0 | **Unified compose is the only route** — `phases/book_driver.py` calls `compose_book_v2` unconditionally, and no `book_pipeline_v2_enabled` or `FEATURE_FLAG_*` has reappeared anywhere. |
| AU-V2 | P0 | **Layout schema mirrors agree** — `book.visual-layout/v1`, the `align`/`flow`/`page_fit` enums, the wrap `width_pct<=50` rule and the center-implies-standalone rule agree between `_visual_layout.py` and `plan-dashboard/scripts/visual-layout.mjs`. The anchor-key leg moved out of `composer.ts` — it is now re-exported from `scripts/lib/anchor-key.mjs` and fixture-pinned, so audit it through the contract's `mirrors` list, not here. |
| AU-V4 | P1 | **Unified stages exist** — `compose_book_v2`, `author_phase_book_augment`, `apply_fluency_adapt`, `apply_author_companion_voice`. |
| AU-V5 | P1 | **Governance ids resolve** — every `BR-*` id cited by `_book_render_checks.py` is defined in `docs/standards/book-print-quality.md`, and the `book-render-challenger` spec exists in both tracked mirrors. The probe derives the id list from the code rather than hardcoding it; the prose rule hardcoded the original four and so never noticed three later checks citing a standard that omits them. |
| AU-V6 | P1 | **Legacy compose stays retired** — no `generate_translation_edition.py`, no `book-illustrated.md` assembly, no `book-slides.md` injection write. |

`AU-V3` was **removed on 2026-07-27**. It asserted that the `book.visuals-index/v1`
schema string must match verbatim between `_visual_candidates.py` and the
`render-book-pdf.mjs` reader. The renderer reads `visual-layout.json` and the string
appears nowhere in `plan-dashboard/`, so the rule asserted a mirror that does not exist.

---

## The web surfaces (`--scope apps`)

Two apps, and they are not interchangeable. Both are declared in the contract's
`apps:` block — directory, source roots, gates, route policy — so this file names
neither a path nor a gate.

| | Podcast Factory Astro Site | Podcast Factory Library |
|---|---|---|
| Audience | Admin / authoring | The readers, on the public internet |
| Routing | File-based (`src/pages/**`) | A manifest that **is** the access policy |
| Lint | ESLint + Prettier, in CI | **None** — reported as `CQ-NO-LINT` |
| Size gate | 1,000-line ceiling + ratchet | **None** — reported as `CQ-NO-SIZE-GATE` |
| Browser gates | `smoke` (in CI) | `smoke`, `security`, `controls` (local only) |

### Routes are a security surface here, not a tidiness one

On the Library, protection comes from a route's **position** in the tree. Three
findings follow from that, and each is P0 because each is a way the gate stops
being a gate:

- **`RT-ORPHAN` / `RT-DANGLING`** — a module present in one place and absent from
  the other. The existing test proves every route in the policy is gated; it
  cannot see a module that is in neither. Such a file reads as a page, is reached
  by nothing, and drifts out of step with the rule it was written under.
- **`RT-BOUNDARY`** — an `ErrorBoundary` exported anywhere but the declared owner.
  A denied page would then render differently from a genuine 404, and which slugs
  exist becomes discoverable by asking.
- **`RT-PATH-GATE`** — access decided from `pathname.startsWith(...)`. `compilePath`
  matches case-insensitively, so `/Admin/people` walks past it, and the `.data`
  suffix is stripped only after middleware has already seen the URL.

### Clean code, where a linter cannot reach

`CQ-NO-LINT` and `CQ-NO-SIZE-GATE` are findings about a **missing gate**, not about
a line of code — which is the level an audit adds something at. ESLint cannot tell
you it was never configured, and a ratchet cannot tell you a whole source tree
falls outside its glob. `CQ-DEBUG` is the one line-level rule, scoped to shipped
source only: a build script prints on purpose, a page does not.

**When a finding here is a scope decision, report it and stop.** Adopting a lint
config across an app is a formatting commit touching every file, and imposing a
size ceiling is a number only the owner can choose — the contract already records
that reasoning for the Astro site's 1,000.

---

## Pass 6 — the closing cleanup (`--cleanup`)

Every run ends here, after the findings and after any approved repair. The executor
is [scripts/repo_cleanup.py](../../scripts/repo_cleanup.py); what it may reclaim
and what it may never touch come from the contract's `hygiene:` block.

```bash
python3 scripts/repo_cleanup.py                              # survey, removes nothing
python3 scripts/repo_cleanup.py --apply                      # the safe categories
python3 scripts/repo_cleanup.py --apply --include git-maintenance
```

**Dry-run first, always, and show the survey before asking.** Categories marked
`confirm: true` in the contract — the local object store, `git gc` — are skipped
until named, because each is large, app-adjacent, or slow to rebuild.

Four refusals are structural rather than configured, and are pinned by
[tests/test_repo_cleanup.py](../../tests/test_repo_cleanup.py):

1. **A tracked file is never debris.** Whatever a glob says, if git knows about it
   the sweep will not remove it — nor will it remove a directory containing one.
2. **`protected_runtime` paths are refused by prefix.** The local D1 is there by
   name: deleting it wipes the `session` table and signs Asif out of localhost, so
   the site shows a sign-in page and looks like nothing shipped.
3. **Nothing outside the repository root**, symlinks included — every candidate is
   resolved and re-checked immediately before deletion, because the survey is not
   the authority and the tree can change under it.
4. **`.git` reaches `git gc`, never a glob.** A loose object is garbage only if
   nothing references it, and the only thing that knows that is git.

Large **untracked** trees are reported with their size and never swept. Experiment
output and inbox drops are somebody's working files; a cleanup that guesses at them
is the one that cannot be undone.

Reclaiming a cache costs a rebuild. Reclaiming the wrong thing costs work that does
not come back — so when a path is ambiguous, report it and let the operator rule.

---

## Plan conformance (`--plan-only`)

Target: [plan.yaml](../../_workspace/plan/refactor/plan.yaml). Waves live under the
top-level keys matching `waves`, `waves_*`, `wave_*` — enumerate them dynamically;
there are six families and 35 waves today, and **there is no `phases[]` key.**

| ID | Severity | Rule |
|---|---|---|
| L1 | P0 | The plan parses. |
| L2 | P1 | Every `depends_on` / `parallel_with` reference resolves to a real wave id. |
| L2-DUP | P1 | No wave id is defined in more than one family. A duplicate makes every reference to it ambiguous. |
| L5 | P0 | **Boundary contract** — the pipeline never writes into the memoir, shared, or site trees. Enforced by `scripts/podcast/_boundary_check.py`, which is in the contract's verify list. Run the script; do not re-grep for it. |
| L6 | P0 | **Async safety** — if any book shows `phase_status: running` with a recent timestamp AND `pgrep -fl 'orchestrate_book|claude -p|extract_chapter|build_episode'` returns non-empty, HALT anything that would touch that book's directory. Report and stop; never fix through a live pipeline. |
| L10 | P1 | The ship checklist's cross-references resolve to plan ids. Only the trailing italic parenthetical is a cross-reference — the bold row ids are the checklist's own scheme, and bare `P0`-`P3` is the severity grammar. Scanning whole lines produced 30 findings for one root cause. |

**Removed on 2026-07-27**, all five for the same reason — the plan key they read does
not exist, so each had been passing without ever running:

| Removed | Read | Reality |
|---|---|---|
| L3 | `intelligence_sources` | No such key |
| L4 | `meta.scope_in` / `meta.scope_out` | No such keys |
| L7 | wave ids vs `_workspace/plan/view/*.html` | Directory deleted; emitted 35 false P2s per run |
| L8 | `meta.legacy_cleanup_basenames` | No such key |
| L9 | view mtime vs plan mtime | Same deleted directory |

L6 is retained as prose rather than moved into the probe on purpose: it is a **halt**
rule about a live process, and a probe that could halt an orchestrator mid-book is a
worse failure than a rule a human runs.

---

## Gate integrity

The repo already enforces nine gates. Before 2026-07-27 this skill knew about none of
them, which is why drift kept reaching `develop` past an audit that reported healthy.
The authoritative list is the contract's `verify:` block — read it there. What this
skill adds is the obligation to **treat a gate's absence or failure as a finding**, not
just to run it:

- A gate that does not run in CI or a hook is a **P1**: it will be skipped exactly when
  it matters.
- A gate whose script the contract names but that does not exist is `CT-VERIFY`, **P1**.
- The TS/Astro side has **no size gate** and six files exceed the Python ceiling, the
  largest above 3,000 lines. This is a known, deliberate omission recorded in the
  contract — the right ceiling for JSX is the owner's call. Report it; never impose one.

### Standing obligations this skill audits

| Obligation | Finding when broken |
|---|---|
| Any edit to `architecture.md`, `refactor/plan.{md,yaml}`, or `debt/pipeline-debt.md` regenerates the three snapshot JSONs in the same response (Tier 0) | P1 — stale snapshots are a contract violation |
| Any edit to an agent spec runs `scripts/podcast/sync-agent-wrappers.sh`; generated mirrors are never hand-edited | P1 — this is how a `.codex` mirror fell a generation behind while claiming parity |
| `CLAUDE.md` edits regenerate `AGENTS.md` | P1 — `scripts/sync_agent_instructions.py --check` proves it |
| Any merge touching `_rules.py` R-constants or `orchestrate_book.py` state fields also touches the podcast skill, `framework.md`, and the challenger catalog | P1 — the docs-sweep sub-rule |
| Discarded paid work, a defect crossing a gate, a human catching a pipeline miss, or a repeated mistake gets an RCA under `docs/rca/` | P1 — a recurrence with no postmortem is the signal this rule exists for |
| Branch names come from `_branching.py`, never hardcoded | P1 — a hardcoded bucket/slug can drift from the folder layout |

---

## Severity, determinism, convergence

Severity is P0/P1/P2/P3 per `docs/reference/skill-bootstrap.md`. Ordering, bounded
convergence (three cycles, then report what did not converge), sweep completeness, the
approval gate, and the commit discipline are **`repo-audit`'s Governing Constraints** —
follow them there rather than re-reading a second copy here.

Two project-specific severity calls:

- A **retired-surface resurrection** is P0 regardless of size. The project brief bans it
  by name, and the previous version of this file allow-listed two of them.
- An **unpinned mirror** is P1 even with both sides currently in agreement. Six real
  divergences were found the day the pins went in, including two resolution ladders that
  disagreed about precedence.

## Reports and the findings ledger

- Report: `_workspace/reviews/reports/<ISO-date>-repo-surgeon.md`.
- Ledger: one JSONL record per finding appended to `_learning/findings.jsonl` with
  `source: "repo-surgeon/podcast"` for the `AU-*` groups, matching the existing prefix
  convention other challengers already use.
- Every report ends with two lines even at zero, because a silent zero and an absent
  line read identically: `N finding(s) suppressed by waiver` and
  `N stale contract entry/entries`.

## What this skill deliberately does not do

- **Does not re-implement `repo-audit`.** If a rule would apply to any repo, it belongs
  there.
- **Does not restate the contract.** Facts get read, never copied.
- **Does not edit the plan.** Authoring is the operator's decision; conformance findings
  are advisory.
- **Does not write a waiver.** It may draft one and ask. Only the owner rules something
  not-a-defect.
- **Does not touch `content/**` or `_learning/**`** beyond appending findings — both are
  protected by the contract.
- **Does not fix through a live pipeline.** L6 halts instead.

## Revision log

- **2026-08-16** — Widened from the pipeline to every surface the project ships.
  Added seven probe groups in a new module: capabilities (`CAP-*`), gate coverage
  (`GT-*`), routes (`RT-*`), test hygiene (`TS-*`), clean code (`CQ-*`) and debris
  (`HY-*`), plus Pass 6, the cleanup executor. Declared both web apps and the
  hygiene rules in the contract so no path or gate is named here. Pinned all of it
  with 48 tests — the probe had none, so the "break it and confirm it fails" rule
  had been performed once per check and never again. The condition that prompted
  it: the verify list named the pipeline and the Astro site and was silent about
  the Podcast Factory Library, so the access-control probe on a private site ran
  only when somebody remembered.
- **2026-07-27** — Refactored. Deleted the duplicated generic engine and delegated it to
  `repo-audit`; moved every project fact to the tracked contract; removed `AU-V3` and
  `L3`/`L4`/`L7`/`L8`/`L9` as asserting contracts that do not exist; rewrote `L10`, which
  emitted 30 findings for one root cause; added `L2-DUP`, the gate-integrity group, the
  standing-obligation table, and `scripts/repo_surgeon_probe.py` so the catalog can fail.
  716 lines to roughly 300, with more real coverage.
- **2026-07-20** — Corrected the root allow-lists, which had drifted to bless two retired
  surfaces and omit five real directories.
- **2026-05-19** — Pass 5 (plan conformance) added.
