# _workspace/plan/

Single source of truth for planning, design, and operational standards in the podcast-factory repo. Organized as a nested structure so each concern lives in one place.

## What's here

| Path | Purpose |
|---|---|
| **[architecture.md](architecture.md)** | Timeless design doc: six-layer module structure, three storage tiers, three-piece intelligence architecture, multi-tier capstone, archetype registry, agent ecosystem, external integrations, branch + content lifecycle, plan SPA. 13 ADRs. 12 Mermaid diagrams. |
| **[refactor/plan.md](refactor/plan.md)** | Human-readable 22-step roadmap to land the architecture. 5 waves: A foundation, B intelligence, C archetype expansion, D SPA + dashboard, E retroactive + gates. |
| **[refactor/plan.yaml](refactor/plan.yaml)** | Machine-readable companion to plan.md — per-step deliverables, acceptance, cost, authorization tier. |
| **[conventions/](conventions/)** | Standing rules across every podcast. `response-template.md` + `response-conventions.md` (how Claude reports back), `general.md` (cross-cutting), `authoring.md` (host gender lock, Essential Teachings, Imam doctrine, reflective-reverent emotion). |
| **[debt/pipeline-debt.md](debt/pipeline-debt.md)** | Live F-item operational backlog (framework gaps observed in flight). Updated continuously by every operator run. |
| **[operations/per-book-ship-checklist.md](operations/per-book-ship-checklist.md)** | Per-book ship checklist + DoR gates. The G1-G7 reference; G8-G12 extensions land via refactor step E4. |
| **[reader/polish-and-ai.md](reader/polish-and-ai.md)** | `podcast-reader/` Astro app polish + Gemini AI integration plan. Parallel concern to the pipeline refactor. |
| **[research/](research/)** | Reference + research: master-disciple recommendations, podcast best practices, redesign audits, findings ledger. |
| **[view/](view/)** | Existing HTML dashboard views (acceptance-criteria.html, intelligence-pipeline.html, kar-status.html, phased-plan.html, pipeline-explained.html). Eventually superseded by the Wave D SPA at `index.html`. |
| **[_drivers/](_drivers/)** | Helper scripts (binder_driver.py, commit_binders.sh, image_dedupe.py, stub_sidecars.py). |
| **[numeric-symbolic-disambiguation-plan.md](numeric-symbolic-disambiguation-plan.md)** | Live design doc for the Numeric/Symbolic Disambiguation protocol (Abjad numerals, jazāʾir, the seven seas). Referenced by `scripts/podcast/phases/p4_*.py` + `skills-staging/podcast/SKILL.md`. Stays at root until the code refs migrate (refactor step A4). |

## Standing doctrine

- **No file versions** (DR-009 in architecture.md). Every file IS the current version. The git history is the version log. Pre-commit hook rejects `Version:\s*\d` and `*v[0-9]*.md` filenames.
- **Retroactive for shipped books** (DR-013). KaR, M&D, Ayyuhal Walad, ISLR Mas-I, Asaas al-Taveel never get re-run through the pipeline. New enhancements ship as addendum episodes + metadata stamps.
- **No file in `scripts/podcast/` exceeds 600 lines** (DR-005). Six-layer acyclic module dependency: Core → Domain → Intelligence + Authoring → Phases → Driver.
- **SQLite + JSON1 for v1** (DR-001). Single-file database at `content/knowledge-base/knowledge.db`. Zero infrastructure on any Mac. Migration to Postgres + pgvector reserved for Wave 2.

## Reading order for a new contributor

1. **[architecture.md](architecture.md)** — what the system IS and why.
2. **[refactor/plan.md](refactor/plan.md)** — what's being built and in what order.
3. **[conventions/response-template.md](conventions/response-template.md)** — how to report progress.
4. **[debt/pipeline-debt.md](debt/pipeline-debt.md)** — what's currently broken or planned but not in the refactor.

For "where does X belong?", start with architecture.md. For "what's next?", read refactor/plan.md. For "what's the current state?", consult the dashboard (Wave D — once D4 lands).

## What used to be here (deleted 2026-05-26)

The legacy planning surface (~22 files including `acceptance-criteria.md` 84K, `podcast-plan.yaml` 263K, `STUDIO-ALIGNMENT-*`, `cohesion-audit-*`, `handoff-kar-*`, `v4-doctrine-propagation.md`, `f25-/f27-*-drafts.md`, `podcast-plan-DoR*.md`, 11 `wisdom-*` rollout artifacts, `podcast-intelligence-enhancements.md`, `intelligence-pipeline-wave1-spec.md`) was folded into this nested structure and deleted. Git history preserves every byte.

Notable folds:
- `intelligence-pipeline-wave1-spec.md` → [architecture.md §Intelligence Layer](architecture.md#the-intelligence-layer--three-piece-architecture) + [refactor/plan.md Wave B](refactor/plan.md#wave-b--intelligence-layer)
- `podcast-intelligence-enhancements.md` items 3-6 → [conventions/authoring.md](conventions/authoring.md)
- `f25-*`, `f27-*`, `v4-doctrine-propagation.md` → already-landed-per-pipeline-debt.md; deleted as superseded
- `acceptance-criteria.md` + `podcast-plan.yaml` → ARCHIVED banner already present at deletion time; references in active specs (SKILL.md, podcast-blueprint.md, podcast-challenger.md, repo-surgeon/skill.md) are dangling and will be updated in refactor step A2/A4 docs-sweep.
