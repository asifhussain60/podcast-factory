# Skills Registry (memoir-only)

Central index of the skills that support the memoir engine and the journal site. As of v3.1 (2026-05-16) every skill targets the **CORTEX Challenger Framework v1.0** (`reference/cortex-challenger-framework.md`) and cites the shared SECTION 0 contract at `reference/skill-bootstrap.md`. As of v3.0 (2026-05-12) the trip/daybook/DayOne skills have been removed — see `framework.md` §"What was removed in v3.0".

Per-skill compliance tier and overlay path: `reference/skill-registry.md`.

## Execution Tiers

| Tier | Runner | Budget | Latency |
|---|---|---|---|
| T0 | Deterministic code | Free | <10ms |
| T1 | Haiku | ~$0.001/call | <2s |
| T2 | Sonnet | ~$0.01/call | <10s |
| T3 | Cowork (Claude Code) | ~$0.10–1.00/session | 30s–5min |

## Skill Index

### Memoir core (framework-defined, Cowork T3)

| Skill | Purpose | Owns | Triggers |
|---|---|---|---|
| `journal` | Memoir chapter writing + refinement (defined in `framework.md`; workflow in `reference/journal-workflow-v2.md`) | `chapters/`, `chapters/snapshots/`, `scratchpad/` | "journal", "continue writing", "next chapter", "refine chapter", "/journal work on chapter N" |

### Dev / infra (Cowork T3 unless noted)

| Skill | Purpose | Owns | Does NOT own | Triggers | Compliance |
|---|---|---|---|---|---|
| [`css-theme-sync`](css-theme-sync/skill.md) | Theme parity validation + auto-fix | Theme tokens across `site/css/` | Theme palette decisions (tweaker handles that) | "validate themes", "theme parity" | SILVER (target) |
| [`ui-modernizer`](ui-modernizer/skill.md) | Execute UI modernization phases | CSS + component changes on the site | Theme definitions (defers to css-theme-sync) | "modernize ui", "run ui phases" | SILVER (target) |
| [`repo-surgeon`](repo-surgeon/skill.md) | Holistic repo audit + repair | Structural integrity, orphan cleanup, registry alignment | Content quality (memoir voice), CSS detail | "repo review", "architectural audit", "cleanup sweep" | BRONZE (target) |
| [`usage-auditor`](usage-auditor/skill.md) | Audit Claude-API spend + forecast | Spend report against `MONTHLY_CAP` | Budget enforcement (proxy middleware does that) | "audit usage", "spend report" | BRONZE (target) |
| [`podcast`](podcast/SKILL.md) | Source-to-NotebookLM transformation (16-stage pipeline) | `_workspace/podcast/<slug>/*`, Podcast Pronunciation Lexicon section of `translations-glossary.md` | Memoir prose (defers to journal); theme work | "podcast this", "turn this into a podcast", "NotebookLM-ready" | GOLD (target) |

## Server prompt registry

Named prompts under `server/src/prompts/` that the proxy registers at startup:

| Prompt | Used by | Tier |
|---|---|---|
| `refine-general` | `/api/refine` — voice-DNA refinement (the AI drawer in the site) | T2 |
| `theme-swatches` | `/api/theme-swatches` (tweaker) | T2 |
| `theme-review` | `/api/theme-review` (tweaker) | T2 |

If you add a prompt, register it in `server/src/prompts/index.js` and add a row here.

## Agents

Agents live outside this registry; see `framework.md` §Agents. In short: `CORTEX` for governance, `journal-orchestrator` for skill routing, `repo-surgeon` for deep audits, `ui-reviewer` for CSS/theme review on Stop.

## Bootstrap & severity

Every skill in this directory cites `reference/skill-bootstrap.md` at SECTION 0. All severity labels are P0 (immutable / halt) / P1 (high / re-run after fix) / P2 (medium / proceed with explicit waiver) / P3 (advisory). Legacy labels (Blocker, Warning, Critical, High, Medium, Low, MAJOR, BLOCKER, NIT) are deprecated — see `reference/skill-bootstrap.md` §2.
