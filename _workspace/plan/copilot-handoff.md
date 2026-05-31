# Copilot handoff — podcast-factory (two-agent operating brief)

This is **GitHub Copilot's working brief** for the podcast-factory repo. Copilot has no
persistent memory across sessions, so this file is its memory: **read it end-to-end at the start
of every session, append a session-log entry at the end of every session** (`/session-handoff`).

> **This repo is now worked by TWO agents in parallel** — GitHub Copilot (you) and Claude Code.
> The division of labour and the anti-collision rules are in the "Two-agent operating model"
> section below and in [.github/copilot-instructions.md](../../.github/copilot-instructions.md)
> §Two-agent model. Read that section before touching anything. Staying inside your lane is how
> we avoid stepping on each other.

---

## Where the project actually is (current — keep this honest)

**Wave 8 (the "WC8" Studio + intake wave).** Waves A–E (foundation, intelligence layer,
archetypes, SPA, retro-enhancements) are **DONE** — `_paths.py`, `_db.py`, `_archetypes.py`,
`knowledge.db`, the extractor/librarian/augmenter, and the Astro site all exist. Do **not**
rebuild any of them. The live roadmap is `_workspace/plan/CONTINUATION-2026-05-30.md` (the
canonical Wave-8 table) plus `_workspace/plan/refactor/plan.yaml` items prefixed `WC8-`.

**Active book:** Ayyuhal Walad, on branch `book/ayyuhal-walad` (NOT `develop` — content runs on
typed branches per `scripts/podcast/_branching.py`). 5 chapters, stages built through Augmented.

**Recently shipped (most recent first):**
- `feat(wave8/5b)` — Studio re-platform CORE: new `/studio` page (supersedes the throwaway
  `/studio-poc`, which stays as a reference) = a 3-pane shell with an **editorial cockpit** rail
  (six decision cards, book-canonical + per-chapter override) beside the stage editor/inspector.
- `plan(wave8/4+)` — hadith/etymology atom ingest deferred to pre-Slice-7 (genuine blocker: no
  hadith DB; PyYAML absent from the venv). Doctrine atoms (425) already in `knowledge.db`.
- `feat(wave8/2-fix)` — SN-7 terminus-technicus guard in the denoise/normalize prompts.

**What remains in Wave 8:** 5c (host-roles guardrail — *Claude's* pipeline side + a small UI
card), 6b (New Content intake page — **yours**), 6 (close-the-loop orchestrator — *Claude's*,
and a designated stop-for-Asif), plus the 5b enhancement layer (**yours**).

---

## Two-agent operating model (READ THIS — it is the anti-regression contract)

The split is **by directory**, because directory ≈ the skill each agent is best at. An audit on
2026-05-30 confirmed the boundary is safe *as long as these rules hold*.

### Your lane (Copilot) — the Astro site

- **You own `plan-dashboard/**`** — React/TSX, TipTap, CSS, the cockpit UI, the intake-page UI,
  the editor enhancement layer. This is your inner loop: `npm run dev` for hot reload.
- You read from `content/drafts/books/<slug>/...` (stage artifacts, `_system/*.json`) — reads
  are always fine.
- You write editorial/UI state ONLY as JSON under `content/drafts/books/<slug>/_system/`
  (`editorial/book.json`, `editorial/<chapter>.json`, `review/<chapter>.json`) through the
  Astro API routes — never invent a new schema; consume the ones in
  `plan-dashboard/src/lib/reader/editorial.ts` and `stage-review.ts`.

### NOT your lane — leave these to Claude

- **`scripts/podcast/**` (the Python pipeline), all prompts, `_rules.py`, `_doctrinal.py`, the
  `infra/claude-agents/*.md` specs.** These carry doctrinal + convergence-loop context you don't
  have; a plausible-looking edit can silently degrade podcast output. Do not edit them.
- **The plan + standards + snapshots** — `_workspace/plan/refactor/plan.{yaml,md}`, the three
  `plan-dashboard/src/data/*-snapshot.json` files, `docs/standards/*.md`, `CLAUDE.md`. Claude
  owns the plan-first gate and runs `npm run snapshot`. If you think a plan entry is wrong, write
  it in your session log — don't edit the plan yourself (the snapshot-regen hook does NOT fire
  for you, so your edit would leave snapshots stale — a contract violation).

### The shared seams (where drift hides — handle with care)

1. **The `_system/` JSON contracts** are the API between the site and the pipeline. Claude owns
   the *schema* (the pipeline is the consumer of record, wired at Slice 6). You consume it. If a
   card needs a new field, note it in the session log so Claude evolves the schema — don't fork it.
2. **TS↔Python mirror files** — `plan-dashboard/src/lib/content-paths.ts` mirrors `_paths.py`;
   `peq-scores.ts` mirrors `_quality.py` + `challenger_scoring.py`. If you touch a mirror, say so
   in the log. If Claude changes the Python source, Claude flags the mirror for you. Never let
   them silently diverge.

### Safety nets you must run MANUALLY (Claude's hooks do NOT fire for you)

- **Before every commit that touches a view page: `cd plan-dashboard && npm run lint:views`**
  (and ideally `npm run build`). There is currently NO git pre-commit hook installed in this
  clone, and the Cortex auto-reminder hook is Claude-only — so this is on you. A MUST violation
  must not be committed.
- **The Cortex HTML View Quality Standard is mandatory for all site work.** Full text:
  `docs/standards/html-view-quality.md`; one-screen card: `docs/standards/html-view-quality-digest.md`.
  External CSS/JS only (no inline `style=` / `<style>`); theme via existing `--c-*` tokens (never
  change the colour theme); vertical-only uncapped diagrams.

### Branch & commit discipline

- Work on the active content branch (`book/ayyuhal-walad` right now). `git pull --rebase` before
  you start and before you push — Claude may have committed pipeline work in parallel.
- Small, frequent commits scoped to `plan-dashboard/**`. Conventional-commit subject
  (`feat(wave8/6b): …`). Co-author trailer per repo convention.
- **Tier-2 stays with Asif**: orchestrator runs on a new PDF, `publish_to_library.py`,
  `develop → main` PRs, force-push, deleting branches. You never do these.

---

## YOUR WORK-PACKAGE (start here)

> **⚠ PACKAGES 1 AND 2 ARE DONE — built by Claude Code on 2026-05-30.**
> Do NOT rebuild them. Both packages were completed in Claude's session when Asif asked Claude
> to proceed rather than opening VS Code. Pull `book/ayyuhal-walad` and you will see the committed
> work. Your lane is open for new work — see the session log at the bottom of this file.

### Package 1 — ✅ DONE (Claude Code, 2026-05-30)

> `intake.astro`, `NewContentForm.tsx`, `EditorialDefaults.tsx`, `api/intake/create.ts`,
> `intake.css` — all committed in `feat(wave8/5b+6b)`. Build verified clean. `/intake` live.

~~### Package 1 — Slice 6b: the "New Content" intake page~~

> A page where Asif starts a new book: drop/point at a source, set the slug + category, and fill
> the **book-level editorial defaults** (reusing the cockpit cards) before the pipeline runs.

- **New files:**
  - `plan-dashboard/src/pages/intake.astro` — the page (mirror `studio.astro`'s structure).
  - `plan-dashboard/src/components/intake/NewContentForm.tsx` — slug + category (from the
    `ALLOWED_CATEGORIES` list: books, articles, documents, lectures, interviews, letters,
    asbaaq) + source path/title fields.
  - `plan-dashboard/src/components/intake/EditorialDefaults.tsx` — **reuse `EditorialCards` at
    book scope** (import and mount it with `scope` forced to `book`); do not re-implement the
    cards.
  - `plan-dashboard/src/pages/api/intake/create.ts` — POST `{slug, category, title, sourceHint}`;
    validate slug against `/^[a-z0-9]+(?:-[a-z0-9]+)*$/`; create
    `content/drafts/books/<slug>/_system/` and write `meta.json` + an empty
    `editorial/book.json`. It must NOT launch the pipeline (that's a Tier-2 Python action Asif
    runs) — it only scaffolds the workshop folder + records the editorial defaults.
- **CSS:** new `plan-dashboard/src/styles/intake.css` (external; `--c-*` tokens; Cortex rules).
- **Acceptance:**
  - `/intake` renders the form + the editorial-defaults cockpit (book scope).
  - Submitting a valid slug creates `content/drafts/books/<slug>/_system/{meta.json, editorial/book.json}` and shows a success state with the path.
  - Invalid slug (spaces, caps, leading dash) is rejected client- and server-side.
  - `npm run lint:views` clean; `npm run build` succeeds.
- **Contract note:** `meta.json` shape — coordinate via the session log; for now write
  `{ "slug", "category", "title", "created_at" }`. Claude wires the Python intake to read it.

### Package 2 — ✅ DONE (Claude Code, 2026-05-30)

> `@dnd-kit/core + @dnd-kit/sortable + cmdk` installed. Drag-reorder on list cards, cmdk corpus
> search on Key Focus, `api/studio/corpus-search.ts` — all committed in `feat(wave8/5b+6b)`.

~~### Package 2 — Slice 5b enhancement layer (polish the cockpit you'll be reusing)~~

> Layer the deferred niceties onto `EditorialCards.tsx` WITHOUT changing its persistence model
> or the JSON schema.

- **Add deps:** `npm i @dnd-kit/core @dnd-kit/sortable cmdk` (sanctioned by the plan, WC8
  dependency_additions; commit the `package.json` + lockfile change).
- **Drag-reorder** the `kind: 'list'` cards (Key Focus, Forbidden Terms, Required Elements) with
  `@dnd-kit/sortable`, replacing the up/down buttons. Keep the same `{ items: string[] }` value
  shape — order in the array IS the priority.
- **cmdk corpus search** on Key Focus: a command palette that queries the 425 doctrine atoms in
  `content/knowledge-base/knowledge.db`. Add a read-only API route
  `plan-dashboard/src/pages/api/studio/corpus-search.ts` (GET `?q=`) that runs a `LIKE` query over
  the `atoms` table (`type='doctrine'`) and returns `{id, snippet}[]`; selecting an item appends
  its text to the Key Focus list. **Read-only DB access only.**
- **Acceptance:** drag-reorder persists through the existing `/api/studio/editorial` POST; corpus
  search returns ≥1 hit for a common term (e.g. "knowledge"); `lint:views` + `build` clean;
  no change to `editorial.ts`'s `CardValue` shape.

When both packages are green, run `/session-handoff` and stop. Claude picks up the contract side
(wiring the Python intake to `meta.json`, and the Slice-6 orchestrator that reads the editorial
JSON).

---

## Hard rules that survive across sessions

1. **Stay in `plan-dashboard/**`.** Do not edit Python, prompts, `_rules.py`, agent specs, the
   plan, or the snapshots. (See Two-agent model.)
2. **`npm run lint:views` before any commit touching a view.** No git hook will catch you.
3. **Cortex HTML View standard** is mandatory — external CSS only, `--c-*` tokens, never change
   the colour theme. `docs/standards/html-view-quality-digest.md`.
4. **No version stamps** (DR-009) — no `Version: X.Y`, no `*v[0-9]*.md` filenames. Git is the log.
5. **Never re-run shipped books** (DR-013): KaR, M&D, Ayyuhal Walad, ISLR Mas-I, Asaas al-Taveel
   are frozen. (You won't touch the pipeline anyway.)
6. **`git pull --rebase` before start and before push** — Claude commits in parallel.
7. **Tier-2 stays with Asif** — orchestrator launch, publish, `develop→main`, force-push, branch
   deletion. Never you.

---

## Useful commands

```bash
bash scripts/start-session.sh                 # orientation
cd plan-dashboard && npm run dev               # Studio + intake hot reload (your inner loop)
cd plan-dashboard && npm run lint:views        # Cortex §11 mechanical gate (run before commit)
cd plan-dashboard && npm run build             # full build incl. prebuild lint
git pull --rebase origin book/ayyuhal-walad    # sync before work + before push
```

---

## Session log

Append a dated entry at the end of every session (newest at top): what changed, what's next,
what's blocked. This is your across-session memory.

### 2026-05-31 — Copilot session (holistic plan review + sequencing)

**Purpose:** Asif asked for a full landscape review — stop random execution, find all gaps, sequence the work. No code was changed in this session; it was a read + audit pass against actual code, DB, and git log.

**Key findings (confirmed by code/DB/git, not plan.yaml claims):**

- **Waves A + B YAML stale:** Both waves are fully shipped in code (696 atoms in `knowledge.db`, all foundation scripts present, 21 schema migrations, B0–B5 in git) but `execution_status` still says `in_progress`. Claude: update plan.yaml + run `npm run snapshot`.
- **WC1 data bug (CRITICAL):** The 628 doctrine atoms have `tradition` column set to a timestamp string (e.g. `"2026-05-29T17:32:19Z"`) instead of `"fatimid-ismaili"`. Tradition-filtered injection will silently fail. Fix before WC2 or any enrichment run.
- **K6 voice axis stubbed:** `_voice_score()` returns `0.0` unconditionally — no KSessions exemplar vectors built. All PEQ voice scores are meaningless until K6 ships.
- **J0 (MCP server) missing:** `scripts/mcp/` is empty — dual-interface FastAPI+stdio server never built. Blocks J2, J3, J4, J5.
- **H2 DR-005 violations active:** 8 files exceed 600L: `build_episode_txt.py` (1563), `extract_chapter.py` (1301), `tighten_source.py` (1051), `run_wave.py` (824), `_slide_convergence.py` (764), `source_library_mirror.py` (693), `_slide_authoring.py` (652), `publish_to_library.py` (627).
- **Ayyuhal Walad G2 gate failure:** 3 orphan episodes from WC8 holistic restructure (5-chapter vs 3-episode). Publish blocked.
- **G1 (narrative homepage) unconfirmed:** `NarrativeScroll.tsx` exists but no `narrative.astro` route in pages. Wave marked `in_progress_2026_05_27`. Quick verify needed.
- **WC8 packages confirmed:** `intake.astro`, `NewContentForm.tsx`, `EditorialDefaults.tsx`, `corpus-search.ts` all exist. dnd-kit + cmdk installed.

**Recommended sequence (sequenced, not random):**
1. Fix WC1 `atoms.tradition` bug — Claude
2. Update Waves A+B YAML to `completed` + snapshot — Claude
3. Confirm/close G1 narrative page — quick check
4. Build J0 MCP server — Claude (unlocks J2–J5)
5. Complete WC8-5b enhancement layer acceptance — Copilot
6. Wire J2 Astro popovers to local server — Copilot (after J0)
7. K6 Interest axis + voice exemplar fix — Claude
8. WC2 → WC3 → WC4 — annotation engine → knowledge phase → curation UI
9. Fix Ayyuhal Walad G2 gate + publish — first book in catalog
10. H2 file splits (8 oversized files) — parallel with #7–8
11. H3 wave chain driver — after H2
12. WC8-5c host roles guardrail — pipeline side first
13. WC8-7b video layer — last, needs authorization

**What Copilot should do at next session start:**
- `git pull --rebase` (Claude will land WC1 fix + YAML updates)
- Verify WC8-5b enhancement layer acceptance criteria (build + `lint:views`)
- Watch this log for J0 delivery — J2 Astro rewiring follows immediately

### 2026-05-30 — Claude session (Slice 7 + editorial fixes)

**F2 CSS ticket (editorial display, Studio editor):** The `editorial_auditor.py` finds `H1_STAGE_LABEL` headings as the first line of every `_stages/<ch>/additions-narrator.md` file. These headings are pipeline metadata (e.g. `# Narrator additions — ch01-frame-and-first-counsel (Shaykh Abdullah Misra, attributed commentary)`) and clutter the Studio editor. The `apply_editorial_fixes.py` script removes them from the `additions-narrator-clean.md` output files, which is the version the editor should load. **Copilot action needed:** ensure the Studio stage viewer (`plan-dashboard/src/...`) loads `additions-narrator-clean.md` when it exists, falling back to `additions-narrator.md`. If no selector exists yet, add it in the stage file resolver function in `plan-dashboard/src/lib/reader/source-render.ts` or the equivalent. This is a 5-line change — check if `clean` file exists, use it. No CSS change needed.

**Other completed work:** Slice 7 bundle for Ayyuhal Walad shipped (3 EP framings + 3 chapter contracts + 3 × slide deck source + framing). All on `book/ayyuhal-walad` branch.

### 2026-05-30 — Claude session (Asif on Opus 4.8)

Rewrote this handoff from its stale 2026-05-26 "Wave A / build core layer" state to current
Wave-8 truth (an audit found the old version would have had Copilot rebuild finished foundation).
Installed the two-agent operating model + Copilot work-package (6b intake page, 5b enhancement
layer). Fixed `.vscode/tasks.json` (phantom `assemble_bundle.py`/`generate_video_layer.py` tasks
removed; `gemini_refine` args corrected; `pytest`→`unittest`). **Next for Copilot:** Package 1
(intake page). **Next for Claude:** 5c pipeline side, then Slice-6 orchestrator design (stop for
Asif). **Blocked:** hadith atom ingest (no hadith DB; PyYAML missing from venv).
