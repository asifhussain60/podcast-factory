# Journal Ecosystem Framework

**Version:** 3.1 (memoir-only — CORTEX Challenger Framework v1.0 adopted)
**Last updated:** 2026-05-16

This document governs the journal repo: the memoir engine, the journal site, and the small set of agents/skills that support memoir authoring. As of v3.0 the trip-planning, daybook/log-capture, and DayOne-publish ecosystems have been removed (preserved on branch `archive/full-stack-pre-strip`).

## Nomenclature

The memoir is *"What I Wish Babu Taught Me."* **Asif IS Babu.** Babu is Asif's wiser/elder voice addressing his younger self "Asif" inside each chapter's closing advice section. Babu is NOT Asif's father. Any stale "Dad" reference in read-only `SKILL_DIR/references/` copies is overridden by the writable Babu versions in `reference/`.

---

## Agents

| Agent | Location | Role |
|---|---|---|
| `CORTEX` | `.github/agents/CORTEX.agent.md` | Governance, vacuum, structure enforcement |
| `journal-orchestrator` | `.github/agents/journal-orchestrator.agent.md` | Skill routing + canonical-write protection |
| `repo-surgeon` | `.github/agents/repo-surgeon.agent.md` | Holistic architecture audit, orphan cleanup |
| `ui-reviewer` | `.claude/agents/ui-reviewer.md` | CSS/theme review (runs on Stop hook) |

---

## The single content skill: `journal`

**Purpose:** Write, refine, and polish chapters of *"What I Wish Babu Taught Me."*

**Owns:** `chapters/`, `chapters/snapshots/`, `scratchpad/`.

**Reads:** all of `reference/` — voice, craft, quotes, incidents, rules.

**Writes:** chapter files; date-stamped snapshots (`chXX-name-YYYY-MM-DD.txt`).

**Triggers:** `journal`, `continue writing`, `next chapter`, `refine chapter`, `edit my memoir`, `/journal work on chapter N`.

**Workflow:** The authoritative spec is `reference/journal-workflow-v2.md`. That file explicitly supersedes any conflicting `SKILL.md` content. Section 1 of the workflow lists the session-start reading order; Section 4 defines the eight-loop Challenger gate that every chapter must pass before finalization.

---

## Supporting skills (dev/infra, not memoir content)

These do not produce memoir prose. They keep the repo and its site healthy.

| Skill | Purpose | Location |
|---|---|---|
| `css-theme-sync` | Theme parity validation + auto-fix across `site/css/` | `skills-staging/css-theme-sync/` |
| `ui-modernizer` | Execute UI modernization phases on the journal site | `skills-staging/ui-modernizer/` |
| `repo-surgeon` | Holistic repo audit, orphan cleanup, registry alignment | `skills-staging/repo-surgeon/` |
| `usage-auditor` | Audit Claude-API spend + forecast against monthly cap | `skills-staging/usage-auditor/` |
| `podcast` | Source-to-NotebookLM transformation (16-stage pipeline; GOLD compliance) | `skills-staging/podcast/` |

All skills target the **CORTEX Challenger Framework v1.0** defined at `reference/cortex-challenger-framework.md`. Severity tiers (P0–P3), DoR gates, convergence loops, sweep contracts, holistic validation, challenge gates, and determinism contracts are universal across skills. The shared SECTION 0 contract that every skill cites at boot is at `reference/skill-bootstrap.md`. Per-skill compliance tiers are tracked in `reference/skill-registry.md`.

---

## Architecture

```
journal/
├── framework.md                ← this file
├── chapters/                   ← memoir text (plain .txt, no markdown)
│   ├── preface.txt, ch00-intro.txt, ch01-man.txt, ch02-love.txt, ch03-marriage.txt
│   └── snapshots/              ← date-stamped delta baselines
├── reference/                  ← single source of truth for memoir knowledge
│   ├── voice-fingerprint.md, voice-deep-analysis.md, craft-techniques.md
│   ├── thematic-arc.md, biographical-context.md, chapter-status.md
│   ├── locked-paragraphs.md, temporal-guardrail.md, translations-glossary.md
│   ├── quotes-library.txt, quotes-workflow.md, clinic-library.txt
│   ├── incident-bank.md, memoir-rules-supplement.txt
│   ├── journal-workflow-v2.md  ← authoritative workflow (overrides SKILL.md)
│   └── master-context.md       ← synthesized cross-chapter intelligence
├── scratchpad/                 ← active working drafts (deleted post-finalization)
├── site/                       ← journal SPA (React-via-Babel, no build)
│   ├── index.html
│   ├── chapters/               ← chapter .txt files mirrored for site reads
│   ├── data/notes/             ← per-chapter reader notes
│   ├── css/                    ← base, app, chapter-reader, themes/, ai-drawer, etc.
│   └── js/                     ← claude-client, voice-refiner, theme-switcher, tweaker, toast
├── server/                     ← local-only Claude proxy (port 3001)
│   ├── README.md
│   └── src/
│       ├── index.js            ← express bootstrap
│       ├── routes/             ← core, usage, theme
│       ├── prompts/            ← refine-general, theme-swatches, theme-review
│       ├── lib/                ← keychain, refine, voice-fingerprint, usage-summary, gemini-client
│       ├── middleware/         ← access-auth, usage-logger, rate-limit, throttle-budget
│       └── schemas/            ← theme-save.schema.json (only surviving schema)
├── shared/                     ← shared client/server modules (tag-normalize)
├── docs/                       ← anthropic-api-setup, proxy-setup, cloudflare integrations
├── infra/                      ← Cloudflare deployment configs
├── skills-staging/             ← dev/infra skills (see registry in README.md)
│   ├── css-theme-sync/, ui-modernizer/, repo-surgeon/, usage-auditor/
│   └── podcast/                ← source-to-NotebookLM (16-stage pipeline)
└── .github/agents/             ← CORTEX, journal-orchestrator, repo-surgeon
```

---

## The journal site + proxy

The site (`site/`) is a single-page React-via-Babel app served as static files. It reads chapter text directly from `chapters/*.txt` and per-chapter notes from `site/data/notes/*.json`. There is no chapter-related backend at runtime.

The proxy (`server/`) is a small Express service on `127.0.0.1:3001` that holds the Anthropic API key (loaded from macOS Keychain at startup) so the browser never touches it. Its surface:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + key-source diagnostics |
| GET | `/api/config` | Public feature flags |
| POST | `/api/voice-test` | Smoke test against memoir voice |
| POST | `/api/refine` | Voice-DNA refinement (used by the AI drawer) |
| POST | `/api/chat` | Generic passthrough with optional `promptName` |
| GET | `/api/reference-data/:name` | Tier 0 JSON files |
| GET | `/api/usage/summary` | Monthly spend rollup |
| POST | `/api/theme-swatches`, `/api/theme-review`, `/api/theme-save` | Tweaker (theme authoring) |

Commands:

```
npm run dev      # serve site on http://localhost:3000
npm run server   # start proxy on http://localhost:3001
```

CORS is locked to localhost + the two deployed hostnames (`journal.kashkole.com`, `journal-dev.kashkole.com`).

---

## Reference folder — single source of truth

All memoir knowledge lives in `reference/`. No duplication across skills.

### Voice & Craft
- `voice-fingerprint.md` — Asif's writing voice DNA
- `voice-deep-analysis.md` — Extended voice characteristics
- `craft-techniques.md` — Writing techniques and patterns
- `translations-glossary.md` — Urdu/cultural terms and translations

### Memoir Structure
- `thematic-arc.md` — Chapter themes and emotional progression
- `biographical-context.md` — Timeline, key people, life events
- `chapter-status.md` — Current state of each chapter
- `locked-paragraphs.md` — Approved text that must not be changed
- `temporal-guardrail.md` — Timeline consistency rules

### Content Libraries
- `quotes-library.txt` — Collected quotes for Babu's-advice sections
- `quotes-workflow.md` — Extraction + weaving protocol
- `clinic-library.txt` — Clinical signs library for cognitive/mental-health symptoms in incidents
- `incident-bank.md` — All memoir incidents, classified and scored

### Governance
- `memoir-rules-supplement.txt` — Rules for voice, structure, duplication prevention
- `journal-workflow-v2.md` — File-first model, eight-loop Challenger, git versioning
- `master-context.md` — Synthesized cross-chapter intelligence

---

## Rules of Engagement

### 1. File-First Model
All chapter work happens in `scratchpad/scratch-{name}.txt`. Chat is for section-numbered feedback only. Never dump prose into chat. Always present `computer://` file links so Asif can click through to read updates.

### 2. Voice Consistency
Every sentence must pass the calibration in `reference/voice-fingerprint.md`. The Challenger gate (Section 4 of the workflow) catches drift.

### 3. No Duplication
Content exists in exactly one place. Skills reference, they don't copy. If a file moves, update this framework and the skill registry.

### 4. Snapshot Discipline
Chapter snapshots use date stamps: `ch01-man-YYYY-MM-DD.txt`. Take a snapshot before any major edit session via `auto_delta.py --save`.

### 5. Babu Identity
Asif IS Babu. The Babu voice is Asif's elder/wiser self addressing "Asif" (his younger self). Babu is NEVER Asif's father. Any incoming material that frames Babu as the father needs correction before being used.

### 6. Cowork-Canonical-Writes
Canonical writes to `chapters/` and `reference/` happen via Cowork (Claude Code) only. The site/proxy never writes memoir state — the proxy is a read-only AI gateway for theme tweaking and voice refinement.

### 7. Integration Documentation
Any external API (Anthropic, Cloudflare Access, etc.) gets a corresponding doc in `docs/` covering auth, rate limits, error behavior, operational notes, and Keychain key name. Created when the integration ships; updated when it changes.

---

## What was removed in v3.0

For historical reference. All of these live on the branch `archive/full-stack-pre-strip`:

- Trip planning and editing (`trip-planner`, `trip-edit`, `trip-log` skills; `trips/` folder; itinerary HTML; flight/distance/weather/recalc backends).
- Daybook / daily-log capture (voice memos, photos, receipts, queue/dead-letter pipeline; skills `receipt-capture`, `food-photo`, `daily-drain`, `catch-up`, `queue-triage`, `queue-health`, `voice-to-prose`, `memory-promotion`).
- DayOne publishing (skill, server routes, UI).
- All YNAB MCP integration (holiday budget panel, classify-holiday-txns).
- SQLite ops database (`server/src/db/`) and the dual-write infrastructure that fed it.
- The MCP ops server (`server/src/mcp/`).

If anything from that branch needs to come back, cherry-pick from `archive/full-stack-pre-strip` rather than rewriting from scratch.
