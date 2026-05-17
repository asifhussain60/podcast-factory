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
    ├── _handbook/                  ← book-agnostic skill refs + templates + episode registry (sorts above books, contains no content)
    │   ├── registry.md             ← episode index across all books
    │   ├── enrichment-sources.md   ← Tier 1–7 whitelist
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
        │   ├── episode-drafts/     ← per-episode authoring scaffolds (NOT the source — see chapters/)
        │   │   └── EP##-<slug>/
        │   │       ├── 00-framing.md           ← the CUSTOMIZE prompt for NotebookLM
        │   │       ├── 02-key-passages.md      ← authoring reference; not uploaded
        │   │       ├── 03-context-pack.md      ← authoring reference; not uploaded
        │   │       ├── 04-discussion-spine.md  ← authoring reference; not uploaded
        │   │       ├── 99-show-notes.md        ← authoring reference; not uploaded
        │   │       └── chapter.scratch.md      ← @@-marker surface mirroring the chapter
        │   └── scratchpad/         ← series-policies.md + working scratches
        ├── chapters/               ← source-book chapters as plain txt
        └── episodes/               ← FINAL deliverables (one concatenated txt per episode)
            └── EP##-<slug>.txt     ← built by scripts/podcast/build_episode_txt.py
```

---

## Agents

| Agent | Location | Role |
|---|---|---|
| `journal-orchestrator` | `.github/agents/journal-orchestrator.agent.md` | Skill routing + canonical-write protection |
| `repo-surgeon` | `.github/agents/repo-surgeon.agent.md` | Holistic architecture audit, orphan cleanup, root hygiene, canonical-file write guards |
| `podcast-challenger` | `.github/agents/podcast-challenger.agent.md` | Semantic-quality review of podcasted-book chapters + framings + Extract Mode contracts; convergence loop (≤3 iterations) before any bundle ships to NotebookLM |
| `podcast-extract` | `.github/agents/podcast-extract.agent.md` | Single-chapter → NotebookLM bundle fast path. Thin wrapper around `scripts/podcast/extract_chapter.py`; zero handbook pre-reads. Invoked via `/extract-chapter <ref>`. Distinct from the full `/podcast` skill (Series Mode). |
| `refine-prompt` | `.github/agents/refine-prompt.agent.md` | Refines a raw request into one compact instruction-paragraph for Claude Opus 4.7 / Claude Code. Reads externalized Operating Contract; invoked via `/refine-prompt`. |
| `ui-reviewer` | `.claude/agents/ui-reviewer.md` | CSS/theme review (runs on Stop hook) |
| `CORTEX` (DEPRECATED 2026-05-17) | `.github/agents/CORTEX.agent.md` | No longer routed. Responsibilities absorbed by `repo-surgeon` (governance/vacuum) and `journal-orchestrator` (canonical-write protection). The CORTEX **skill** at `~/.claude/skills/cortex/` remains active as the framework BASELINE — only the standalone agent is deprecated. |

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

**Owns:** all of `content/podcast/` — both the book-agnostic `_handbook/` and every `<book-slug>/`.

**Reads:** sources Asif provides + `content/podcast/_handbook/` references.

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

## Refinement surfaces: `refine` vs `refine-prompt`

Two refinement surfaces exist in this repo with similar names but disjoint scope. Treat them as separate tools — never substitute one for the other.

| Surface | Location | Target | Output shape | Reads repo? |
|---|---|---|---|---|
| `refine` | [skills-staging/refine/](skills-staging/refine/) | Cowork briefs (external deliverable format) | Cowork-shaped brief | No |
| `refine-prompt` | Canonical: [.github/agents/refine-prompt.agent.md](.github/agents/refine-prompt.agent.md) + [.github/agents/operating-contract.md](.github/agents/operating-contract.md). Runtime: [.claude/agents/refine-prompt.md](.claude/agents/refine-prompt.md) + [.claude/commands/refine-prompt.md](.claude/commands/refine-prompt.md) (per-machine, gitignored, loaded by Claude Code) | Claude Opus 4.7 / Claude Code (VS Code) instructions for *this* repo | Single compact instruction-paragraph | Yes — inventories `framework.md`, `.github/agents/`, `.claude/agents/`, `skills-staging/`, root listing |

`refine-prompt` is repo-aware. It reads [.github/agents/operating-contract.md](.github/agents/operating-contract.md) (the externalized Operating Contract — single source of truth, repo-agnostic), distills its 8 sections into terse imperatives, layers in anti-regression hints from a single bash-call inventory, and emits exactly one paragraph (80–180 words) ending with the user's original ask as the closing imperative. The paragraph also embeds an interactive-clarification clause instructing the downstream Claude to surface `AskUserQuestion`-style options (best recommendation first, labeled `(Recommended)`, one question at a time) whenever ambiguity remains.

Determinism: same input + same repo state → byte-identical paragraph.

Boundary: `refine-prompt` is read-only at refinement time. It never modifies the repo. The canonical contract at `.github/agents/operating-contract.md` is the only authoritative source; refinement agents reference it directly, never inline its full text.

File layout follows the repo convention: tracked canonical agents live at `.github/agents/*.agent.md`; Claude Code's runtime working copies live at `.claude/agents/*.md` (per-machine, gitignored). When editing either copy, keep both in sync.

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
└── .github/agents/                         ← journal-orchestrator, repo-surgeon, podcast-challenger (CORTEX agent deprecated 2026-05-17)
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

### 7. Podcast Episode Deliverable (architecture v3.4 — two-file model)

Per-episode work is authored as a draft folder under `content/podcast/<book>/_system/episode-drafts/EP##-<slug>/` containing the framing (`00-framing.md`) and authoring scaffolds (`02-key-passages.md`, `03-context-pack.md`, `04-discussion-spine.md`, `99-show-notes.md`) PLUS the matching chapter at `content/podcast/<book>/chapters/chNN-<slug>.txt` (strict 1:1 chapter ↔ episode mapping, same slug after the prefix).

**Two files reach NotebookLM, in distinct roles:**

| File | Role | NotebookLM action |
|---|---|---|
| `content/podcast/<book>/chapters/chNN-<slug>.txt` | The enriched chapter — the **SOURCE** | Uploaded directly as the single source for the notebook (no transformation) |
| `content/podcast/<book>/episodes/EP##-<slug>.txt` | The customize prompt only — the **CUSTOMIZE PROMPT** | Pasted into NotebookLM's *Customize* prompt box |

The chapter file IS the source. `scripts/podcast/build_episode_txt.py` does NOT transform it; it only validates it. The episode txt IS the customize prompt — emitted by the build script from `00-framing.md` (HTML comments stripped, trailing Upload Checklist section stripped, post-strip meta-prose re-checked).

**Why two files (not one):** if a single concatenated file with both blocks is uploaded as a source, NotebookLM treats the customize prompt as source content and the hosts may read it aloud. Two separate files, two folders by purpose, zero ambiguity.

The other draft files (`02-key-passages.md`, `03-context-pack.md`, `04-discussion-spine.md`, `99-show-notes.md`) are authoring-only scaffolds — they inform the chapter's enrichment and the framing's tensions but do not flow to NotebookLM (anchored to `content/podcast/_handbook/notebooklm-best-practices.md` §3 and §7).

**Chapter file hygiene (NotebookLM protection):** Chapter files contain ONLY chapter content — they are uploaded as-is. Authoring metadata (status, citation inventory, enrichment ratio, verification notes) lives in `content/podcast/<book>/_system/enrichment-log.md`, NOT inline. Forbidden in any chapter: HTML `<!-- ... -->` blocks, *"This file is..."* / *"Phase 0..."* / *"Nothing has been added..."* / `[VERIFY CITATION]` markers, `EP\d\d` cross-references. `scripts/podcast/build_episode_txt.py` enforces this with `META_PROSE_TELLS` + `META_PROSE_REGEX_TELLS` + a no-HTML-comments check — any match is a hard build error. The same gate is re-applied to the framing file's post-strip content (the customize-prompt episode txt).

Chapter (= SOURCE) word counts: floor 1,500; target 2,500–3,500; ceiling 4,500; hard refuse outside [500, 5,500]. Framing (= CUSTOMIZE PROMPT) word counts: target 150–2,000.

### 8. Chapters: Designed, Enriched, Required (INVARIANT)
**Episodes cannot exist without enriched source-book chapters.** For every podcasted book, `content/podcast/<book>/chapters/` must contain one `chNN-<slug>.txt` per planned episode (the slug matches the corresponding `EP##-<slug>` draft folder exactly). Chapters are designed via Phase 0 of the podcast skill:

- **Phase 0a — Source extraction.** OCR / text-layer extract the original PDF into `<book>/_system/source/text/raw-extract.md`, then refine into `normalized.md`.
- **Phase 0b — English refinement.** Translation quality is fixed; OCR artifacts are cleaned; archaic or awkward phrasing is modernized while preserving meaning and intent.
- **Phase 0c — Arabic phonetic transcription pass.** Every Arabic transliteration, Quranic verse, hadith line, dua, honorific, and name receives a phonetic guide at first occurrence in the book; the lexicon at `<book>/_system/source/text/_lexicon.md` is the persistent canonical record.
- **Phase 0d — Chapter design.** The published structure of the source book is a HINT, not a constraint. Chapters are designed by MEANINGFUL THEMATIC SEPARATION and BALANCED SIZE (floor 1,500, target 2,500–3,500, ceiling 4,500; all chapters within ~30% of each other in word count).
- **Phase 0e — Enrichment.** Each chapter is enriched from the Tier 1–7 whitelist at `content/podcast/_handbook/enrichment-sources.md` (author's own corpus, Quran, hadith, Imam Ali via *Nahj al-Balagha*, Ismaili tradition, Sufi tradition, modern reference works). Outside material ≤ 60% of any chapter's word count — the author's argument stays the spine.
- **Phase 0f — Series intake + confirmation gate.** Asif confirms the chapter plan; confirming chapters IS confirming the episode plan under the 1:1 mapping.
- **Phase 0g — Register the series.** Episode draft folders are scaffolded with slugs matching their chapter slugs.

`build_episode_txt.py` enforces the chapter-exists and chapter-size invariants with hard errors. Episodes are derivative artifacts of an enriched source book, never freestanding NotebookLM bundles.

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

### v3.4 — two-file deliverable model (chapter IS the SOURCE; episode txt IS the CUSTOMIZE PROMPT) (2026-05-16, later)

- **Architecture flip caught by Asif:** the v3.3.x design had `episodes/EP##.txt` contain BOTH the customize prompt AND the source content concatenated with `=== ... ===` separators, requiring the user to copy-paste each block into the right NotebookLM surface. Confusing and error-prone. Asif's intent (from the original reorg request) was: chapters/ = SOURCE files (upload directly), episodes/ = customize prompts (paste into Customize box). Two folders, two roles, zero ambiguity.
- **Implementation**:
  - `scripts/podcast/build_episode_txt.py` rewritten. The chapter file is now uploaded as-is to NotebookLM; the build script validates it (no HTML comments, no meta-prose, word count in band) but does NOT transform it. The episode txt is emitted from `00-framing.md` only — HTML comments stripped, trailing Upload Checklist stripped, meta-prose re-checked.
  - Chapter metadata moved out of inline `<!-- ENRICHMENT STATUS -->` headers into a sidecar at `content/podcast/<book>/_system/enrichment-log.md`. Chapter files are now upload-ready by construction.
  - All 5 Ayyuhal Walad chapter files cleaned (HTML comments stripped); all 5 framings updated (recursive self-descriptions removed; Upload Checklists rewritten for the two-file workflow; H1s stripped of "EP## Framing:" boilerplate).
- **Episode txts shrink dramatically:** customize-prompt-only is 815–989 words per episode (was 3,400–4,800 with the concatenated model). Chapter SOURCE files are the same content as before.
- **Documentation propagated:** SKILL.md Section 6 + Section 7 (Quality Gate items 16/17/18 rewritten); Phase 4 step 2 rewritten with the new two-file model; podcast-challenger agent v1.1 (architecture clarifications throughout); orchestrator content-invariant block; framework Rule 7.

### v3.3.2 — podcast-challenger agent (semantic-quality gate before NotebookLM upload) (2026-05-16, later)

- **New agent**: `.github/agents/podcast-challenger.agent.md` — semantic-quality reviewer for podcasted-book chapters + framings. Complements `build_episode_txt.py` (which enforces structural contracts) by covering everything semantic: citation authenticity, phonetic coverage, enrichment depth, framing 4-part structure, NotebookLM literalness.
- **30 checks across 6 categories** — Authenticity (P0), NotebookLM literalness (P0), Pronunciation discipline (P1), Enrichment & depth (P1), Articulation & shape (P1), Framing integrity (P0–P1).
- **Convergence loop**: ≤3 iterations. Auto-fixes deterministic mechanical issues (em-dashes, cross-episode refs, honorific repetition, lexicon parity). Flags everything semantic for human resolution. Writes `BOOK_DIR/_system/challenger-report.md` with verdict (`SHIP-READY` / `SHIP-WITH-CAUTION` / `BLOCKED`).
- **Ship-readiness gate**: `journal-orchestrator` refuses to route any "ready for upload" intent until the most recent challenger run shows `SHIP-READY`.
- **Podcast skill integration**: `skills-staging/podcast/SKILL.md` Phase 4 now has a step 1a "run podcast-challenger to convergence" between the QUALITY GATE and the compile step.

### v3.3.1 — NotebookLM hygiene (HTML-comment stripping + meta-prose anti-pattern) (2026-05-16, later)

- **Bug caught by Asif:** chapter files carried two kinds of meta that NotebookLM would have read out loud: `<!-- ENRICHMENT STATUS: ... -->` headers, and "This file is a refined and enriched presentation..." paragraphs. Chapter `.txt` files are plain text; HTML comments do not get stripped by NotebookLM.
- **Fix:** `scripts/podcast/build_episode_txt.py` now (a) strips all `<!-- ... -->` blocks from both the framing and the chapter before writing the SOURCE block, and (b) scans the post-strip chapter content for meta-prose tells (`This file is`, `This document is`, `Phase 0`, `ENRICHMENT STATUS`, `Nothing has been added that is not in the source`, `Anything Ghazali only implies`, `preserved in blockquotes`, `structured by beat`, `refined presentation of the chapter`, `[VERIFY CITATION`, etc.) — any match is a hard error.
- **Cleanup:** all 5 Ayyuhal Walad chapter files have had their meta-prose paragraphs removed. ENRICHMENT STATUS HTML comments retained (now auto-stripped by the build).
- **Protocol encoded:** new "Chapter file = chapter content only (NotebookLM hygiene)" subsection in SKILL.md §6; new Quality Gate item 4a; new Content Invariant in the orchestrator agent; Rule 7 of framework.md updated.

### v3.3 — chapter IS the source + Phase 0 enrichment protocol (2026-05-16, later)

- **Architectural shift:** strict 1:1 chapter ↔ episode mapping. The chapter file under `content/podcast/<book>/chapters/chNN-<slug>.txt` IS the SOURCE block of its episode. Eliminated `01-source-primary.md` from episode-draft folders. Single source of truth; chapter rewrites flow straight to the next episode-txt build.
- **Phase 0 rewritten:** 0a Source extraction → 0b English refinement → 0c Arabic phonetic transcription pass → 0d Chapter design (meaningful separation, balanced size, content-driven) → 0e Chapter enrichment (Tier 1–7 whitelist; ≤60% outside material) → 0f Series intake + confirmation → 0g Register series.
- **New canonical reference:** `content/podcast/_handbook/enrichment-sources.md` — the whitelist of authorized enrichment sources (Author's corpus, Quran, hadith, Imam Ali via *Nahj al-Balagha* and *Ghurar al-Hikam*, Ismaili tradition: Holy Du'a, Ginans, Farmans of the Aga Khans, classical Ismaili philosophers, Sufi tradition near Ghazali, modern reference works) with citation formats and enrichment principles.
- **Build script call signature changed:** `build_episode_txt.py BOOK_DIR EP##-<slug>`. Reads framing from the draft folder and the SOURCE from the slug-matched chapter file. Slug mismatch is a hard error.
- **Quality Gate enriched:** 19-step checklist now includes chapter-exists, chapter-size band, enrichment-ratio cap, phonetic-coverage, and chapter-IS-source invariants.
- **Ayyuhal Walad migration applied:** 22 thin section-extract chapters retired (preserved in git history); 5 substantive episode source-primary files promoted to `chapters/ch01-frame-and-first-counsel.txt` through `ch05-method-and-closing-prayer.txt`. EP01 draft folder renamed `EP01-ayyuhal-walad-ch1` → `EP01-frame-and-first-counsel` for slug parity. Each draft folder's `01-source-primary.md` removed; scratchpads renamed to `chapter.scratch.md`. All 5 episodes rebuild cleanly under the new architecture. Enrichment (Phase 0e) is per-chapter content sessions driven by Asif.
