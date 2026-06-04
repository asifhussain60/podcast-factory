# plan-dashboard

The Podcast Factory Astro Site (`plan-dashboard/`) — a living surface for the podcast-factory plan and the reader. Three pages, one local app:

- **Overview** (`/`) — the front door.
- **How it works** (`/architecture`) — vertical timeline of the pipeline stations with the modules that plug into each.
- **What it runs on** (`/infrastructure`) — Anthropic / Google / Azure with hover-to-see cost detail per service.
- **Live progress** (`/dashboard`) — the roadmap, the books in flight, the metrics. Streams updates from a server-sent-events feed.

## Run it

```bash
cd plan-dashboard
npm install
npm run dev      # opens http://localhost:4322
```

Once the dev server is up, the green dot in the top right shows the SSE stream is connected.

## Where the data comes from

Three JSON snapshots in `src/data/`:

| File | Source of truth | Authored by |
|---|---|---|
| `architecture-snapshot.json` | `_workspace/plan/architecture.md` + the actual pipeline phase files | `podcast-planner` agent |
| `infrastructure-snapshot.json` | `_workspace/setup/azure-stack.md` + `scripts/podcast/_cost_ledger.py` + Azure billing | `podcast-planner` agent |
| `dashboard-snapshot.json` | `_workspace/plan/refactor/plan.yaml` + `_workspace/plan/debt/pipeline-debt.md` + `content/drafts/*/_system/orchestrator-state.json` + `git log` | `podcast-planner` agent (statuses + live state); `npm run snapshot` (mechanical refresh) |

Two ways to refresh:

1. **The planner agent** — runs after every plan-related task and rewrites all three snapshots from current repo truth, including the plain-English copy. This is the primary path.
2. **`npm run snapshot`** — runs the mechanical refresher at `scripts/regenerate-snapshots.mjs`. Preserves the agent-authored plain-English copy, updates only the live fields (book state, recent commits, generated_at). Useful in CI and when you want a quick refresh without invoking a model.

Both paths touch `.snapshot-version`, which the SSE endpoint watches — the dashboard refreshes within ~100ms of either path completing.

## The design protocol

Every visual element in this app respects four locked rules:

1. **Plain English only** in copy that renders to the user. No `_authoring.py`, no `PHASE_0D`, no `R-PHONETICS-OUT`. Code-style identifiers stay in JSON keys, never in visible strings.
2. **Lato, 13–14px base** typography.
3. **Vertical flow, no fixed heights.** Pages scroll. Nothing scroll-locks or hides under a fold.
4. **Zero inline styling.** All visual properties come from `src/styles/theme.css`. Any new visual treatment gets a class added there, never an `style="..."` attribute or one-off color.

The `podcast-planner` agent enforces these rules in Guardian mode. Builder mode rejects its own output if it would violate them.

## Files

```
plan-dashboard/
├── README.md                                  ← this file
├── package.json
├── astro.config.mjs
├── tsconfig.json
├── scripts/
│   └── regenerate-snapshots.mjs               ← mechanical refresher
├── src/
│   ├── layouts/Base.astro                     ← shared shell, top nav, SSE subscriber
│   ├── pages/
│   │   ├── index.astro                        ← Overview
│   │   ├── architecture.astro                 ← How it works
│   │   ├── infrastructure.astro               ← What it runs on
│   │   ├── dashboard.astro                    ← Live progress
│   │   └── api/stream.ts                      ← SSE endpoint (server-sent events)
│   ├── components/
│   │   ├── PipelineSpine.tsx                  ← vertical timeline SVG
│   │   ├── LayerStack.tsx                     ← six-layer diagram
│   │   ├── InfraColumns.tsx                   ← vendor columns + hover tips
│   │   ├── Sparkline.tsx                      ← tiny per-service SVG
│   │   ├── SpendChart.tsx                     ← 30-day combined-spend bar chart
│   │   └── DashboardTabs.tsx                  ← roadmap / current / metrics tabs
│   ├── data/                                  ← snapshot JSONs (regenerated)
│   └── styles/theme.css                       ← single source of styling
└── .gitignore
```

## What this replaces

The seven static HTML views in `_workspace/plan/view/` are legacy. They opened over `file://`, had no live data, and required manual regeneration. This app supersedes them. Once the dashboard is verified end-to-end the legacy views will be archived in a single move.
