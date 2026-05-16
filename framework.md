# Journal Ecosystem Framework

**Version:** 3.2 (content/ tree adopted — memoir + podcast siblings)
**Last updated:** 2026-05-16

This document governs the journal repo: the memoir engine, the journal site, the podcast source-bundle agent, and the small set of agents/skills that support content authoring. As of v3.0 the trip-planning, daybook/log-capture, and DayOne-publish ecosystems have been removed (preserved on branch `archive/full-stack-pre-strip`). As of v3.2 all authored content lives under a single `content/` tree with `babu-memoir/` and `podcast/<book-slug>/` as siblings.

## Nomenclature

The memoir is *"What I Wish Babu Taught Me."* **Asif IS Babu.** Babu is Asif's wiser/elder voice addressing his younger self "Asif" inside each chapter's closing advice section. Babu is NOT Asif's father. Any stale "Dad" reference in read-only `SKILL_DIR/references/` copies is overridden by the writable Babu versions in `content/babu-memoir/_system/`.

---

## Content tree

All authored content lives under [content/](content/):

```
content/
├── babu-memoir/                    ← the memoir (chapters only; no episodes)
│   ├── _system/                    ← voice, craft, quotes, incidents, snapshots, scratchpad, workflow
│   └── chapters/                   ← preface.txt, ch00…ch03.txt
└── podcast/                        ← parent for podcasted source books
    ├── _README.md                  ← podcast-wide intro
    ├── _system/                    ← book-agnostic refs (skill-owned)
    │   ├── registry.md             ← episode index across all books
    │   ├── notebooklm-source-format.md
    │   ├── notebooklm-best-practices.md
    │   ├── two-host-framing.md
    │   ├── source-distillation.md
    │   ├── episode-architecture.md
    │   ├── scratchpad-markers.md
    │   └── workspace-readme-template.md
    └── ayyuhal-walad/              ← one source book (template; add more as siblings)
        ├── _README.md              ← book-specific
        ├── _system/                ← book-specific authoring state
        │   ├── source/             ← original PDF + extracted/normalized text
        │   ├── meta/               ← extracted metadata, normalized.md, segments, lexicon
        │   ├── pronunciation.md    ← active overrides for the series
        │   ├── editorial-notes.md
        │   ├── library-proposals.md
        │   ├── episode-drafts/     ← per-episode 5–6 markdown source files (authoring scaffold)
        │   │   └── EP##-<slug>/
        │   │       ├── 00-framing.md
        │   │       ├── 01-source-primary.md (+ .scratch.md mirror)
        │   │       ├── 02-key-passages.md
        │   │       ├── 03-context-pack.md
        │   │       ├── 04-discussion-spine.md
        │   │       └── 99-show-notes.md
        │   ├── scratchpad/         ← series-policies.md + working scratches
        │   └── legacy/             ← superseded pipeline artifacts
        ├── chapters/               ← source-book chapters as plain txt
        └── episodes/               ← FINAL deliverables (one concatenated txt per episode)
            └── EP##-<slug>.txt     ← built by scripts/podcast/build_episode_txt.py
```

---

## Agents

| Agent | Location | Role |
|---|---|---|
| `CORTEX` | `.github/agents/CORTEX.agent.md` | Governance, vacuum, structure enforcement |
| `journal-orchestrator` | `.github/agents/journal-orchestrator.agent.md` | Skill routing + canonical-write protection |
| `repo-surgeon` | `.github/agents/repo-surgeon.agent.md` | Holistic architecture audit, orphan cleanup |
| `ui-reviewer` | `.claude/agents/ui-reviewer.md` | CSS/theme review (runs on Stop hook) |

---

## The memoir skill: `journal`

**Purpose:** Write, refine, and polish chapters of *"What I Wish Babu Taught Me."*

**Owns:** `content/babu-memoir/chapters/`, `content/babu-memoir/_system/snapshots/`, `content/babu-memoir/_system/scratchpad/`.

**Reads:** all of `content/babu-memoir/_system/` — voice, craft, quotes, incidents, rules.

**Writes:** chapter files; date-stamped snapshots (`chXX-name-YYYY-MM-DD.txt`).

**Triggers:** `journal`, `continue writing`, `next chapter`, `refine chapter`, `edit my memoir`, `/journal work on chapter N`.

**Workflow:** The authoritative spec is `content/babu-memoir/_system/journal-workflow-v2.md`. That file explicitly supersedes any conflicting `SKILL.md` content. Section 1 lists the session-start reading order; Section 4 defines the eight-loop Challenger gate that every chapter must pass before finalization.

**After finalizing a chapter:** run `scripts/site/sync_chapters.sh` to refresh the site's `site/chapters/` bundle mirror so the published site picks up the change on next deploy.

---

## The podcast skill: `podcast`

**Purpose:** Convert source material (PDFs, books, articles, transcripts) into NotebookLM-ready source bundles that steer the Audio Overview into a focused two-host conversation.

**Owns:** all of `content/podcast/` — both the book-agnostic `_system/` and every `<book-slug>/`.

**Reads:** sources Asif provides + `content/podcast/_system/` references.

**Writes:** per-episode draft bundles under `<book>/_system/episode-drafts/EP##-<slug>/`; final concatenated deliverables at `<book>/episodes/EP##-<slug>.txt` (rebuilt via `scripts/podcast/build_episode_txt.py`).

**Triggers:** `podcast`, `/podcast`, `@podcast`, `new episode`, `next episode`, `make this a podcast`, `NotebookLM episode`, `audio overview`.

**CORTEX:** out of scope (content-prep, by design — quality judged by human listening, not automated gates).

---

## Supporting engineering skills

These do not produce content. They keep the repo and its site healthy.

| Skill | Purpose | Location | CORTEX |
|---|---|---|---|
| `css-theme-sync` | Theme parity validation + auto-fix across `site/css/` | `skills-staging/css-theme-sync/` | SILVER (target) |
| `ui-modernizer` | Execute UI modernization phases on the journal site | `skills-staging/ui-modernizer/` | SILVER (target) |
| `repo-surgeon` | Holistic repo audit, orphan cleanup, registry alignment | `skills-staging/repo-surgeon/` | BRONZE (target) |
| `usage-auditor` | Audit Claude-API spend + forecast against monthly cap | `skills-staging/usage-auditor/` | BRONZE (target) |

Engineering skills target the **CORTEX Challenger Framework v1.0** defined at `reference/cortex-challenger-framework.md`. The shared SECTION 0 contract every engineering skill cites at boot is at `reference/skill-bootstrap.md`. Per-skill compliance tiers are tracked in `reference/skill-registry.md`.

Content-prep skills (`journal` and `podcast`) are governed by their own workflow docs, not by CORTEX automated gates — quality is judged by the human against the canonical voice and feel.

---

## Architecture

```
journal/                                    ← repo root
├── framework.md                            ← this file
├── content/                                ← all authored content (see Content tree above)
│   ├── babu-memoir/
│   └── podcast/
├── reference/                              ← repo-wide skill governance
│   ├── cortex-challenger-framework.md      ← the framework v1.0
│   ├── skill-bootstrap.md                  ← shared SECTION 0 contract
│   ├── skill-registry.md                   ← per-skill tier + file ownership
│   └── skill-overlays/
│       ├── journal-cortex-overlay.md
│       ├── clean-commit-cortex-overlay.md
│       ├── refine-cortex-overlay.md
│       └── tell-me-cortex-overlay.md
├── skills-staging/                         ← in-repo skill definitions
│   ├── README.md
│   ├── podcast/                            ← podcast skill (SKILL.md + scripts/)
│   ├── css-theme-sync/, ui-modernizer/, repo-surgeon/, usage-auditor/
├── scripts/
│   ├── memoir/                             ← auto_delta, detect_user_delta, save_snapshot, refresh_all_snapshots
│   ├── podcast/                            ← build_episode_txt.py (draft → single-txt deliverable)
│   ├── site/                               ← sync_chapters.sh (canonical memoir → site mirror)
│   ├── git-hooks/, install-git-hooks.sh
├── site/                                   ← journal SPA (React-via-Babel, no build)
│   ├── index.html
│   ├── chapters/                           ← BUILD ARTIFACT — mirror of content/babu-memoir/chapters/
│   │                                          (synced by scripts/site/sync_chapters.sh)
│   ├── data/notes/                         ← per-chapter reader notes
│   ├── css/                                ← base, app, chapter-reader, themes/, ai-drawer, etc.
│   └── js/                                 ← claude-client, voice-refiner, theme-switcher, tweaker, toast
├── server/                                 ← local-only Claude proxy (port 3001)
│   └── src/                                ← index, routes/, prompts/, lib/, middleware/, schemas/
├── shared/                                 ← shared client/server modules (tag-normalize)
├── docs/                                   ← anthropic-api-setup, proxy-setup, cloudflare integrations
├── infra/                                  ← Cloudflare deployment configs
├── _workspace/                             ← gitignored scratch (chats, ideas, screenshots)
└── .github/agents/                         ← CORTEX, journal-orchestrator, repo-surgeon
```

---

## The journal site + proxy

The site (`site/`) is a single-page React-via-Babel app served as static files. It reads chapter text directly from `site/chapters/*.txt` — which is a **build artifact** mirroring `content/babu-memoir/chapters/` (the canonical source). The mirror is refreshed via `scripts/site/sync_chapters.sh` after any chapter finalization, and before any site deploy. Per-chapter notes live in `site/data/notes/*.json`.

The proxy (`server/`) is a small Express service on `127.0.0.1:3001` that holds the Anthropic API key (loaded from macOS Keychain at startup) so the browser never touches it. Its surface:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + key-source diagnostics |
| GET | `/api/config` | Public feature flags |
| POST | `/api/voice-test` | Smoke test against memoir voice |
| POST | `/api/refine` | Voice-DNA refinement (used by the AI drawer) |
| POST | `/api/chat` | Generic passthrough with optional `promptName` |
| GET | `/api/reference-data/:name` | Tier 0 JSON files (server-local, unrelated to memoir refs) |
| GET | `/api/usage/summary` | Monthly spend rollup |
| POST | `/api/theme-swatches`, `/api/theme-review`, `/api/theme-save` | Tweaker (theme authoring) |

The voice-fingerprint files read by `server/src/lib/voice-fingerprint.js` resolve to `content/babu-memoir/_system/voice-fingerprint.md` and `voice-fingerprint-light.md`.

Commands:

```
npm run dev      # serve site on http://localhost:3000
npm run server   # start proxy on http://localhost:3001
```

CORS is locked to localhost + the two deployed hostnames (`journal.kashkole.com`, `journal-dev.kashkole.com`).

---

## Rules of Engagement

### 1. File-First Model
All chapter work happens in `content/babu-memoir/_system/scratchpad/scratch-{name}.txt`. Chat is for section-numbered feedback only. Never dump prose into chat. Always present `computer://` file links so Asif can click through to read updates.

### 2. Voice Consistency
Every sentence must pass the calibration in `content/babu-memoir/_system/voice-fingerprint.md`. The Challenger gate (Section 4 of the workflow) catches drift.

### 3. No Duplication
Content exists in exactly one place. Skills reference, they don't copy. The only sanctioned duplicate is `site/chapters/`, which is an explicit, scripted build-artifact mirror.

### 4. Snapshot Discipline
Chapter snapshots use date stamps: `ch01-man-YYYY-MM-DD.txt`. Take a snapshot before any major edit session via `python3 scripts/memoir/save_snapshot.py content/babu-memoir/chapters/<file>.txt`. Snapshots land under `content/babu-memoir/_system/snapshots/`.

### 5. Babu Identity
Asif IS Babu. The Babu voice is Asif's elder/wiser self addressing "Asif" (his younger self). Babu is NEVER Asif's father. Any incoming material that frames Babu as the father needs correction before being used.

### 6. Cowork-Canonical-Writes
Canonical writes to `content/` happen via Cowork (Claude Code) only. The site/proxy never writes content state — the proxy is a read-only AI gateway for theme tweaking and voice refinement.

### 7. Podcast Episode Deliverable
Per-episode work is authored as a 5–6 file markdown draft under `content/podcast/<book>/_system/episode-drafts/EP##-<slug>/`. The single `content/podcast/<book>/episodes/EP##-<slug>.txt` is the ONLY artifact uploaded to NotebookLM. It is rebuilt by `scripts/podcast/build_episode_txt.py` on every change to the draft — never hand-edited.

The episode txt contains **exactly two clearly delimited blocks**: the CUSTOMIZE PROMPT (body of `00-framing.md` minus the upload checklist) and the SOURCE (body of `01-source-primary.md`). Key-passages, context-pack, discussion-spine, and show-notes are **authoring-only scaffolds**; they do not appear in the txt because their inclusion would push the source over NotebookLM's word-count ceiling and dilute the listener's focus (anchored to `content/podcast/_system/notebooklm-best-practices.md` §3 and §7).

Source word counts: 1,800–2,800 words is the Default Deep Dive sweet spot; up to 4,500 (Longer Deep Dive) acceptable with rationale; hard refuse outside [500, 5,500].

### 8. Chapters Required Before Episodes (INVARIANT)
**Episodes cannot exist without source-book chapters.** For every podcasted book, `content/podcast/<book>/chapters/` must contain at least one `.txt` file (one per chapter of the source book) before any episode is built. The `build_episode_txt.py` script enforces this with a hard error. If chapters are missing, promote the per-section raw extracts from `<book>/_system/source/text/sections/` into `<book>/chapters/chNN-<slug>.txt` first.

This invariant keeps the structure honest: episodes are derivative artifacts of a source book, never freestanding NotebookLM bundles.

### 9. Integration Documentation
Any external API (Anthropic, Cloudflare Access, etc.) gets a corresponding doc in `docs/` covering auth, rate limits, error behavior, operational notes, and Keychain key name.

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

## What changed in v3.2

- Introduced `content/` tree. `babu-memoir/` and `podcast/<book>/` siblings, each with `_system/` + `chapters/` (+ `episodes/` for podcast only).
- Memoir refs moved from `reference/` to `content/babu-memoir/_system/`. Memoir scratchpad and snapshots followed.
- Podcast moved from `podcast/` to `content/podcast/ayyuhal-walad/`. Episode deliverables are single `EP##.txt` files; the per-section markdown drafts persist under `_system/episode-drafts/`.
- New script `scripts/podcast/build_episode_txt.py` builds the single-txt deliverable. It enforces two invariants: source word count ∈ [500, 5,500] (per NotebookLM best practices §3) and `chapters/` non-empty.
- New script `scripts/site/sync_chapters.sh` mirrors `content/babu-memoir/chapters/` into `site/chapters/` for Cloudflare deploy.
- `reference/` now holds only repo-wide skill governance: framework, bootstrap, registry, overlays. No memoir content.

### v3.2.1 — episode-txt format + chapters-required invariant (2026-05-16, later)

- **Bug fix:** initial `build_episode_txt.py` concatenated all 5–6 draft files into the deliverable, producing 8K–10K word txts — 2× the NotebookLM 5,500-word ceiling. Rewritten to emit only CUSTOMIZE PROMPT + SOURCE, matching `notebooklm-best-practices.md` §3 / §5 / §7.
- **Invariant added:** episodes cannot be built unless `<book>/chapters/` is non-empty. `build_episode_txt.py` hard-errors otherwise. Promotes the structural rule "episodes are derivative artifacts of a source book" from documentation into executable enforcement.
- **Chapters populated** for Ayyuhal Walad: 22 source sections promoted into `content/podcast/ayyuhal-walad/chapters/chNN-<slug>.txt`.
