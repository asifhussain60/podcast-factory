# _workspace

Working surface for the podcast-factory project. Five folders, nothing else.
Naming convention: lowercase-kebab-case throughout. No SCREAMING_CASE filenames.

| Folder | What lives here |
|---|---|
| `inbox/` | Raw source material coming into the pipeline — PDFs, audio files, YouTube downloads. Transient: commit text pipeline outputs only; audio/video stay local. |
| `plan/` | Master plan. `refactor/plan.yaml` + `refactor/plan.md` = canonical roadmap. `site-work-status.md` = live session-continuity doc (auto-injected at session start). `architecture.md` = timeless design reference. |
| `prompts/` | Prompt templates, improvement specs, continuation starters. `continue-*.md` = session-bootstrap prompts for specific work tracks. |
| `reviews/` | Audit reports, deployment reviews, orchestrator logs, historical archives. Read-only reference — nothing here drives active execution. |
| `tests/` | PEQ baselines for KaR and M&D (regression floor). Test strategy backlog, case, and findings directories. |

## Key files

- `plan/site-work-status.md` — current work state (read this first in any new session)
- `plan/continuation-2026-05-30.md` — WC8 autonomous build mandate + wave-8 slice table
- `plan/refactor/plan.yaml` — master roadmap (all waves A–K, WC8, dual-platform)
- `plan/architecture.md` — timeless system design (read when conventions feel stale)
- `prompts/intelligence-layer-spec.md` — locked design decisions D1–D15 for the intelligence layer
- `reviews/reports/2026-05-30-full-repo-audit.md` — full repo architect audit + 12-phase to-do list

## Standing rules

- No file version suffixes — git history is the version log (DR-009)
- No root-level sprawl — only README.md and the five typed subdirectories above
- Single-machine model since 2026-05-23; session-starter is `scripts/start-session.sh`
