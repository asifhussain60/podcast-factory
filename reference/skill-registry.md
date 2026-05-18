# Skill Registry

**Purpose:** Single source of truth for every skill in the user's Cowork ecosystem — compliance tier, file ownership, capabilities, triggers, execution tier.

**Authority:** Anchored to `reference/cortex-challenger-framework.md` v1.0. Anything in `framework.md` defers to this file for skill-level detail.

---

## Active skills — compliance

| Skill | Compliance Tier | Status | Definition path |
|---|---|---|---|
| **CORTEX** | BASELINE | Active (plugin) | `~/.claude/skills/cortex/SKILL.md` |
| **ADLC** | GOLD | Active (plugin) | `~/.claude/skills/adlc/SKILL.md` |
| **Journal** | SILVER (target) | Active (plugin) — overlay applies | `~/.claude/skills/journal/SKILL.md` + `journal/reference/skill-overlays/journal-cortex-overlay.md` |
| **Cowork-brief** (was `refine` pre-v3.5) | BRONZE (target) | Active (plugin) — overlay applies | `~/.claude/skills/cowork-brief/SKILL.md` + `journal/reference/skill-overlays/cowork-brief-cortex-overlay.md` |
| **Tell-me** | SILVER (target) | Active (plugin) — overlay applies | `~/.claude/skills/tell-me/SKILL.md` + `journal/reference/skill-overlays/tell-me-cortex-overlay.md` |
| **Clean-commit** | BRONZE (target) | Active (plugin) — overlay applies | `~/.claude/skills/clean-commit/SKILL.md` + `journal/reference/skill-overlays/clean-commit-cortex-overlay.md` |
| **Podcast** | OUT OF SCOPE (content-prep) | Active in staging — exempt from CORTEX per SKILL.md §9; quality judged by human listening | `journal/skills-staging/podcast/SKILL.md` |
| **CSS-theme-sync** | SILVER (target) | WIP in staging | `journal/skills-staging/css-theme-sync/skill.md` (+ `cortex-compliance.md`) |
| **Repo-surgeon** | BRONZE (target) | WIP in staging — consolidated to single skill.md | `journal/skills-staging/repo-surgeon/skill.md` |
| **UI-modernizer** | SILVER (target) | WIP in staging | `journal/skills-staging/ui-modernizer/skill.md` (+ `cortex-compliance.md`) |
| **Usage-auditor** | BRONZE (target) | WIP in staging (spec only) | `journal/skills-staging/usage-auditor/skill.md` (+ `cortex-compliance.md`) |

All skills target **CORTEX Challenger Framework v1.0**. The framework version is implicit unless a row says otherwise.

## Retired skills

| Skill | Retired | Notes |
|---|---|---|
| **Trip-log** | 2026-05-16 | Memory tombstoned; plugin file still present (read-only) — disable via Cowork plugin settings to fully remove |

---

## Active skills — capabilities

Detail on what each skill owns, what triggers it, and what it explicitly defers to other skills.

### Memoir core (framework-defined, Cowork T3)

| Skill | Purpose | Owns | Triggers |
|---|---|---|---|
| `journal` | Memoir chapter writing + refinement (workflow in `content/babu-memoir/_system/journal-workflow-v2.md`) | `content/babu-memoir/chapters/`, `content/babu-memoir/_system/snapshots/`, `content/babu-memoir/_system/scratchpad/` | "journal", "continue writing", "next chapter", "refine chapter", "/journal work on chapter N" |

### Engineering skills (Cowork T3 — CORTEX-compliant)

| Skill | Purpose | Owns | Does NOT own | Triggers |
|---|---|---|---|---|
| `css-theme-sync` | Theme parity validation + auto-fix | Theme tokens across `site/css/` | Theme palette decisions (tweaker handles that) | "validate themes", "theme parity" |
| `ui-modernizer` | Execute UI modernization phases | CSS + component changes on the site | Theme definitions (defers to css-theme-sync) | "modernize ui", "run ui phases" |
| `repo-surgeon` | Holistic repo audit + repair (4 passes: Structure / Code / Architecture / Brittleness) | Structural integrity, orphan cleanup, registry alignment | Content quality (memoir voice), CSS detail | "repo review", "architectural audit", "cleanup sweep", "root clutter" |
| `usage-auditor` | Audit Claude-API spend + forecast | Spend report against `MONTHLY_CAP` | Budget enforcement (proxy middleware) | "audit usage", "spend report" |

### Content-prep skills (out of CORTEX scope — quality judged by human)

| Skill | Purpose | Owns | Triggers |
|---|---|---|---|
| `podcast` | NotebookLM source-bundle prep — per-episode draft bundle that steers the Audio Overview into a focused two-host conversation | `content/podcast/` (registry, books, chapters, episodes) | "podcast", "/podcast", "@podcast", "new episode", "next episode", "make this a podcast", "NotebookLM episode", "audio overview", "turn this into a podcast" |

---

## Execution tiers

| Tier | Runner | Budget | Latency |
|---|---|---|---|
| T0 | Deterministic code | Free | <10ms |
| T1 | Haiku | ~$0.001/call | <2s |
| T2 | Sonnet | ~$0.01/call | <10s |
| T3 | Cowork (Claude Code) | ~$0.10–1.00/session | 30s–5min |

---

## Server prompt registry

Named prompts under `server/src/prompts/` registered at proxy startup via `server/src/prompts/index.js`:

| Prompt | Used by route | Execution tier |
|---|---|---|
| `refine-general` | `POST /api/refine` — voice-DNA refinement (the AI drawer on the site) | T2 |
| `theme-swatches` | `POST /api/theme-swatches` (tweaker) | T2 |
| `theme-review` | `POST /api/theme-review` (tweaker) | T2 |

When adding a prompt: register in `server/src/prompts/index.js` and add a row here. `repo-surgeon` Pass 3 rule A3 enforces bidirectional sync.

---

## Compliance tier meanings

(See `reference/cortex-challenger-framework.md` Section 5 for full definitions.)

- **GOLD** — 100% applicable framework items satisfied; all gates hard; framework referenced in SKILL.md
- **SILVER** — 100% applicable items satisfied; some gates documented but not fully enforced
- **BRONZE** — ≥80% applicable items satisfied; key gates enforced
- **NEEDS-WORK** — <80% applicable items satisfied
- **PRE-COMPLIANCE** — Skill exists but framework not yet applied
- **BASELINE** — Defines the framework rules others adopt (CORTEX itself)

"Target" suffix means: the overlay or compliance doc has been written; the listed tier reflects the post-application state. Until overlays are merged into plugin skills (via plugin rebuild), the actual runtime tier is PRE-COMPLIANCE.

## Bootstrap & severity

Every engineering skill cites `reference/skill-bootstrap.md` at SECTION 0 and uses the universal **P0–P3** severity taxonomy (P0 immutable / halt, P1 high / re-run after fix, P2 medium / proceed with explicit waiver, P3 advisory). Legacy labels (Blocker, Warning, Critical, High, Medium, Low, MAJOR, BLOCKER, NIT) are deprecated.

`podcast` is content-prep and is out of CORTEX scope per its SKILL.md §9 — no DoR gates, no convergence loops, no `_challenger-report.yml`. Its quality contract is its Section 7 manual gate.

---

## File ownership

Per the framework's Section 7 cross-skill coordination contract, the following file-ownership claims govern write access. Skills writing to a file owned by another skill must use a staging file + apply step.

| File / directory | Owner |
|---|---|
| `content/babu-memoir/chapters/*.txt` | journal |
| `content/babu-memoir/_system/translations-glossary.md` | journal |
| `content/babu-memoir/_system/quotes-library.txt` | journal (other skills propose) |
| `content/babu-memoir/_system/clinic-library.txt` | journal (other skills propose) |
| `content/babu-memoir/_system/incident-bank.md` | journal only |
| `content/babu-memoir/_system/voice-fingerprint.md` | journal only |
| `content/babu-memoir/_system/voice-fingerprint-light.md` | journal (used by Babu app orchestrators) |
| `content/babu-memoir/_system/voice-deep-analysis.md` | journal only |
| `content/babu-memoir/_system/craft-techniques.md` | journal only |
| `content/babu-memoir/_system/master-context.md` | journal only |
| `content/babu-memoir/_system/thematic-arc.md` | journal only |
| `content/babu-memoir/_system/biographical-context.md` | journal only |
| `content/babu-memoir/_system/memoir-rules-supplement.txt` | journal only (P0 governance file) |
| `content/babu-memoir/_system/locked-paragraphs.md` | journal only (P0 governance file) |
| `content/babu-memoir/_system/temporal-guardrail.md` | journal only (P0 governance file) |
| `content/babu-memoir/_system/chapter-status.md` | journal only |
| `content/babu-memoir/_system/journal-workflow-v2.md` | journal only |
| `content/babu-memoir/_system/quotes-workflow.md` | journal only |
| `content/babu-memoir/_system/scratchpad-markers.md` | journal only |
| `content/babu-memoir/_system/scratchpad/*.txt` | journal only |
| `content/babu-memoir/_system/snapshots/*.txt` | journal only |
| `content/podcast/.skill/handbook/*` (book-agnostic refs incl. `enrichment-sources.md` whitelist) | podcast |
| `content/podcast/.skill/registry.md` (cross-book episode index, mutable) | podcast |
| `content/podcast/.skill/archive/*` (superseded book snapshots) | podcast |
| `content/podcast/library/<category>/<book>/_system/*` | podcast |
| `content/podcast/library/<category>/<book>/chapters/*.txt` | podcast |
| `content/podcast/library/<category>/<book>/chapter-contracts/*.yml` | podcast |
| `content/podcast/library/<category>/<book>/episodes/*.txt` | podcast (generated by `scripts/podcast/build_episode_txt.py`) |
| `content/podcast/library/<category>/<book>/transcripts/*.txt` | podcast (transcripts dropped after NotebookLM render) |
| `content/_shared/arabic/*` | shared cross-skill data (read-only for podcast; framework + journal write with explicit approval) |
| `reference/skill-registry.md` | this file — framework owns |
| `reference/cortex-challenger-framework.md` | framework only (locked) |
| `reference/skill-bootstrap.md` | framework only |
| `reference/skill-overlays/*` | each skill owns its own overlay |
| `_workspace/challenger-reports/*` | per-skill (write own report) |
| `site/css/*.css` (themes) | css-theme-sync |
| `site/*.html`, `site/css/app.css` | ui-modernizer (with css-theme-sync coordinating for theme tokens) |
| Repo root structure | repo-surgeon (proposes; user commits) |

---

## Agents

Agents live outside the skill model. See `framework.md` §Agents for the full table. Currently:

- `journal-orchestrator` — skill routing + canonical-write protection (`.github/agents/journal-orchestrator.agent.md`)
- `repo-surgeon` — full procedure absorbed into `skills-staging/repo-surgeon/skill.md`; thin agent stub at `.github/agents/repo-surgeon.agent.md` for subagent registration only; absorbs root-hygiene/vacuum from the deprecated CORTEX agent
- `podcast-challenger` v1.2 — semantic-quality reviewer with Extract Mode contract checks (`.github/agents/podcast-challenger.agent.md`)
- `ui-reviewer` — CSS/theme review on Stop hook (`.claude/agents/ui-reviewer.md`)
- ~~`CORTEX`~~ — **DEPRECATED 2026-05-17.** Agent at `.github/agents/CORTEX.agent.md` is no longer routed; responsibilities absorbed by `repo-surgeon` and `journal-orchestrator`. The CORTEX **skill** at `~/.claude/skills/cortex/` remains active as the framework BASELINE.

---

## Compliance audit log

| Date | Scope | Result |
|---|---|---|
| 2026-05-16 | Full ecosystem audit | All non-CORTEX/ADLC skills at PRE-COMPLIANCE; framework v1.0 authored; overlays / compliance docs created |
| 2026-05-16 | Podcast redesign | 16-stage pipeline replaced with NotebookLM source-bundle agent; podcast moved out of CORTEX scope; new content workspace at `content/podcast/` |
| 2026-05-16 | Content reorg | `content/` tree introduced (`babu-memoir/`, `podcast/<book>/` siblings). Memoir refs moved from `reference/` to `content/babu-memoir/_system/`. `reference/` now holds only repo-wide skill governance |
| 2026-05-16 | Podcast pipeline v3.3 | Strict 1:1 chapter ↔ episode mapping; chapter IS the SOURCE; Phase 0 protocol (extract → English refinement → Arabic phonetic pass → chapter design → enrichment); enrichment whitelist at `content/podcast/_handbook/enrichment-sources.md` |
| 2026-05-16 | NotebookLM hygiene | `build_episode_txt.py` strips HTML comments + hard-refuses meta-prose tells in chapter and framing files |
| 2026-05-16 | podcast-challenger agent | New semantic-quality gate at `.github/agents/podcast-challenger.agent.md`. 30 checks across 6 categories. Convergence ≤3 iterations. Sidecar report at `BOOK_DIR/_system/challenger-report.md`. Orchestrator refuses "ready for upload" intents until `SHIP-READY` |
| 2026-05-16 | Two-file deliverable v3.4 | `chapters/chNN-<slug>.txt` IS the SOURCE (uploaded directly); `episodes/EP##-<slug>.txt` IS the CUSTOMIZE PROMPT only. `build_episode_txt.py` rewritten to validate chapter as-is + emit prompt-only episode txt |
| 2026-05-17 | Consolidation + root cleanup | `_system/legacy/` + `_system/meta/` removed from Ayyuhal Walad; stale dated memoir snapshots removed; root `.env.example` + `index.html` removed; `repo-surgeon` trinity collapsed to single `skill.md` + thin agent stub; `skills-staging/README.md` merged into this file |
| 2026-05-17 | Podcast Extract Mode | `scripts/podcast/extract_chapter.py` + per-chapter contract schema (`content/podcast/.skill/handbook/chapter-contract.template.yml`, formerly `_handbook/`) + splitting policy spec (`extract-capability.md`). NOTE: the memoir crossing recorded at the time of this row was SEVERED on the same day under the v3.5 workspace restructure — `content/babu-memoir/` is now fully out of scope for the podcast skill (see v3.5 row below). |
| 2026-05-17 | Production-readiness audit + remediation | Journal `SKILL.md` mirrored to `skills-staging/journal/` (was install-only); Dad→Babu rewrite + v2 banner + correct folder paths; `01-source-primary.md` invariant violation in `extract_chapter.py` removed (file no longer emitted); meta-prose lint in extractor sync'd with build script; handbook drift fixed in `scratchpad-markers.md`, `source-distillation.md`, `extract-capability.md`; `new_episode.py` registry path corrected; `podcast-challenger` v1.2 with Category G (Extract Mode contracts); CORTEX agent deprecated (responsibilities absorbed by `repo-surgeon` + `journal-orchestrator`); `clean-commit` / `refine` / `tell-me` mirrored from install to `skills-staging/`; `site-worker.js` `/trips/*` proxy removed |
| 2026-05-17 | Podcast workspace v3.5 + memoir severance | `content/podcast/<book>/` → `content/podcast/library/<category>/<book>/` (6 category folders: books/, articles/, documents/, lectures/, interviews/, letters/; only `books/ayyuhal-walad/` populated). Skill internals moved: `_handbook/` → `.skill/handbook/`, registry promoted to `.skill/registry.md`, `_archive/` → `.skill/archive/`. Memoir inbound severed: `content/podcast/from-memoir/` deleted (16 files); `extract_chapter.py` no longer reads `content/babu-memoir/chapters/`; `PROHIBITED_PATH_PREFIXES` now blocks all of `content/babu-memoir/`. `podcast-challenger` v1.5; SKILL.md §9 "one sanctioned read across the memoir boundary" removed. OUTBOUND library-proposals path preserved. |
| 2026-05-17 | Refactor audit Bundle 1 + 2 | `contract_path_for()` in `extract_chapter.py` bug-fixed (was constructing a v3.4-era path that no longer exists; now derived from `chapter.path.parents[1]`). Stale-doc cleanup: memoir `scratchpad-markers.md` parallel-copy link; `_shared/arabic/00-README.md` provenance reference; `skills-staging/clean-commit/references/folder-rules.md` Journal Repo section rewritten to v3.5 layout. Governance docs refreshed: `framework.md` Content Tree + Rule 7 + Phase 0e + v3.5 changelog; this file's file-ownership table + audit-log + `_shared/arabic/` row. |
| 2026-05-17 | v3.0 dead-code cleanup (v3.5.1) | Removed v3.0-stripped server modules + dependencies that had lingered for months. Deleted: `server/src/util/ynab.js`, `server/src/lib/gemini-client.js`, 5 trip/SQLite scripts, `mac-vision-ocr.swift`, 2 silently-broken validators. Slimmed: `keychain.js` (Anthropic-only), `routes/core.js` (no gemini status, no dead `/api/config`). Dropped deps: `@google/genai` (3 protobufjs CVEs), `better-sqlite3`, `multer`, `fast-json-patch`, `js-yaml`. `npm audit` now 0 vulns (was 3 high/moderate). Cleaned `.env` + `.env.example` of YNAB/ORS/REFINE_ALL_ENABLED. CI workflow simplified — schema/marker validation steps removed (scripts gone; schema validation moved to runtime Express middleware, marker discipline enforced by challenger agents). |

Next audit: when any skill's tier is meaningfully updated (overlay merged into plugin SKILL.md, WIP skill graduates) — record date, scope, and result.

---

## Maintenance procedures

### Add a new skill

1. Author `skill.md` (in-skill) or overlay (`skill-overlays/<name>-cortex-overlay.md`) for read-only plugin skills.
2. Author `cortex-compliance.md` next to the skill (if in `skills-staging/`).
3. Self-assess against the framework's adoption checklist (Section 4 of framework).
4. Add rows to "Active skills — compliance" and "Active skills — capabilities" tables above.
5. If the skill claims write ownership over any file, add to "File ownership" table.
6. Update audit log.

### Graduate a skill's tier

1. Apply outstanding gaps from the skill's compliance doc.
2. Re-self-assess against the framework's adoption checklist.
3. If applicable items satisfied increased into the next tier band, update the registry.
4. Add an audit log row.

### Deprecate / retire a skill

1. Add to "Retired skills" table with retirement date and reason.
2. If files owned by the retired skill should pass to another owner, update "File ownership" table.
3. Remove from "Active skills" tables.
4. Update audit log.
