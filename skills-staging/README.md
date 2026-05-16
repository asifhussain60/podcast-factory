# Skills Registry (memoir + podcast)

Central index of the skills that support the memoir engine, the journal site, and the podcast workspace. As of v3.1 (2026-05-16) every **engineering** skill targets the **CORTEX Challenger Framework v1.0** (`reference/cortex-challenger-framework.md`) and cites the shared SECTION 0 contract at `reference/skill-bootstrap.md`. **Content-prep** skills (currently just `podcast`) are intentionally exempt from CORTEX overhead — their quality is judged by the human reading/listening, not by automated gates.

As of v3.0 (2026-05-12) the trip/daybook/DayOne skills have been removed — see `framework.md` §"What was removed in v3.0".

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
| `journal` | Memoir chapter writing + refinement (defined in `framework.md`; workflow in `content/babu-memoir/_system/journal-workflow-v2.md`) | `content/babu-memoir/chapters/`, `content/babu-memoir/_system/snapshots/`, `content/babu-memoir/_system/scratchpad/` | "journal", "continue writing", "next chapter", "refine chapter", "/journal work on chapter N" |

### Engineering skills (Cowork T3 — CORTEX-compliant)

| Skill | Purpose | Owns | Does NOT own | Triggers | Compliance |
|---|---|---|---|---|---|
| [`css-theme-sync`](css-theme-sync/skill.md) | Theme parity validation + auto-fix | Theme tokens across `site/css/` | Theme palette decisions (tweaker handles that) | "validate themes", "theme parity" | SILVER (target) |
| [`ui-modernizer`](ui-modernizer/skill.md) | Execute UI modernization phases | CSS + component changes on the site | Theme definitions (defers to css-theme-sync) | "modernize ui", "run ui phases" | SILVER (target) |
| [`repo-surgeon`](repo-surgeon/skill.md) | Holistic repo audit + repair | Structural integrity, orphan cleanup, registry alignment | Content quality (memoir voice), CSS detail | "repo review", "architectural audit", "cleanup sweep" | BRONZE (target) |
| [`usage-auditor`](usage-auditor/skill.md) | Audit Claude-API spend + forecast | Spend report against `MONTHLY_CAP` | Budget enforcement (proxy middleware does that) | "audit usage", "spend report" | BRONZE (target) |

### Content-prep skills (out of CORTEX scope — quality judged by human)

| Skill | Purpose | Owns | Does NOT own | Triggers |
|---|---|---|---|---|
| [`podcast`](podcast/SKILL.md) | NotebookLM source-bundle prep — 5-to-6 markdown files per episode (framing, primary source, key passages, context, discussion spine, optional show notes) that steer NotebookLM's Audio Overview | `podcast/` workspace (registry, episodes, archive) | Audio generation (NotebookLM does); scripts (NotebookLM does); web research (sources come from user / `journal/`) | "podcast", "/podcast", "@podcast", "new episode", "next episode", "turn this into a podcast", "NotebookLM episode", "audio overview", "make this a podcast", "I want to listen to this" |

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

Every **engineering** skill in this directory cites `reference/skill-bootstrap.md` at SECTION 0 and uses the universal P0–P3 severity taxonomy (P0 immutable / halt, P1 high / re-run after fix, P2 medium / proceed with explicit waiver, P3 advisory). Legacy labels (Blocker, Warning, Critical, High, Medium, Low, MAJOR, BLOCKER, NIT) are deprecated — see `reference/skill-bootstrap.md` §2.

`podcast` is a content-prep skill and is explicitly out of CORTEX scope per its own SKILL.md §9 — no DoR gates, no convergence loops, no `_challenger-report.yml`. Its quality contract is its Section 7 manual gate.
