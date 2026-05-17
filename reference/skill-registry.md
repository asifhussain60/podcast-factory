# Skill Registry

**Purpose:** Single source of truth for every skill in the user's Cowork ecosystem, its CORTEX Challenger Framework compliance tier, and its file ownership claims.

**Authority:** Anchored to `reference/cortex-challenger-framework.md` v1.0.

---

## Active skills

| Skill | Tier | Framework version | Status | SKILL.md or overlay path |
|---|---|---|---|---|
| **CORTEX** | BASELINE | self-defining | Active (plugin) | `~/.claude/skills/cortex/SKILL.md` |
| **ADLC** | GOLD | predates framework but compatible | Active (plugin) | `~/.claude/skills/adlc/SKILL.md` |
| **Podcast** | OUT OF SCOPE (content-prep, by design) | n/a | Active in staging — content-prep skill, intentionally exempt from CORTEX per SKILL.md §9; quality judged by human listening, not automated gates | `journal/skills-staging/podcast/SKILL.md` (content workspace: `journal/content/podcast/<book-slug>/`) |
| **Journal** | SILVER (target) | v1.0 | Active (plugin) — overlay describes post-compliance behavior | `~/.claude/skills/journal/SKILL.md` + `journal/reference/skill-overlays/journal-cortex-overlay.md` |
| **Refine** | BRONZE (target) | v1.0 | Active (plugin) — overlay applies | `~/.claude/skills/refine/SKILL.md` + `journal/reference/skill-overlays/refine-cortex-overlay.md` |
| **Tell-me** | SILVER (target) | v1.0 | Active (plugin) — overlay applies | `~/.claude/skills/tell-me/SKILL.md` + `journal/reference/skill-overlays/tell-me-cortex-overlay.md` |
| **Clean-commit** | BRONZE (target) | v1.0 | Active (plugin) — overlay applies | `~/.claude/skills/clean-commit/SKILL.md` + `journal/reference/skill-overlays/clean-commit-cortex-overlay.md` |
| **CSS-theme-sync** | SILVER (target) | v1.0 | WIP in staging | `journal/skills-staging/css-theme-sync/skill.md` + `cortex-compliance.md` |
| **Repo-surgeon** | BRONZE (target) | v1.0 | WIP in staging | `journal/skills-staging/repo-surgeon/skill.md` + `cortex-compliance.md` |
| **UI-modernizer** | SILVER (target) | v1.0 | WIP in staging | `journal/skills-staging/ui-modernizer/skill.md` + `cortex-compliance.md` |
| **Usage-auditor** | BRONZE (target) | v1.0 | WIP in staging (spec only) | `journal/skills-staging/usage-auditor/skill.md` + `cortex-compliance.md` |

## Retired skills

| Skill | Status | Retired | Notes |
|---|---|---|---|
| **Trip-log** | RETIRED | 2026-05-16 | Memory tombstoned; plugin file still present (read-only) — disable via Cowork plugin settings to fully remove |

---

## Tier meanings

(See `reference/cortex-challenger-framework.md` Section 5 for full definitions.)

- **GOLD** — 100% applicable framework items satisfied; all gates hard; framework referenced in SKILL.md
- **SILVER** — 100% applicable items satisfied; some gates documented but not fully enforced
- **BRONZE** — ≥80% applicable items satisfied; key gates enforced
- **NEEDS-WORK** — <80% applicable items satisfied
- **PRE-COMPLIANCE** — Skill exists but framework not yet applied
- **BASELINE** — Defines the framework rules others adopt (CORTEX itself)

"Target" suffix (e.g., "SILVER (target)") means: the overlay or compliance doc has been written; the listed tier reflects the post-application state. Until overlays are merged into plugin skills (via plugin rebuild), the actual runtime tier is PRE-COMPLIANCE.

---

## File ownership

Per the framework's Section 7 cross-skill coordination contract, the following file-ownership claims govern write access. Skills that need to write to a file owned by another skill must use a staging file + apply step.

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
| `content/podcast/_system/*` (book-agnostic refs incl. `enrichment-sources.md` whitelist) | podcast |
| `content/podcast/<book>/_system/*` | podcast |
| `content/podcast/<book>/chapters/*.txt` | podcast |
| `content/podcast/<book>/episodes/*.txt` | podcast (generated by `scripts/podcast/build_episode_txt.py`) |
| `reference/skill-registry.md` | this file — framework owns |
| `reference/cortex-challenger-framework.md` | framework only (locked) |
| `reference/skill-bootstrap.md` | framework only |
| `reference/skill-overlays/*` | each skill owns its own overlay |
| `_workspace/challenger-reports/*` | per-skill (write own report) |
| `site/css/*.css` (themes) | css-theme-sync |
| `site/*.html`, `site/css/app.css` | ui-modernizer (with css-theme-sync coordinating for theme tokens) |
| Repo root structure | repo-surgeon (proposes; user commits) |

---

## Compliance audit log

| Date | Auditor | Scope | Result |
|---|---|---|---|
| 2026-05-16 | (cowork session) | Full ecosystem audit | All non-CORTEX/ADLC skills at PRE-COMPLIANCE; framework v1.0 authored; overlays / compliance docs created; targets recorded above |
| 2026-05-16 | (cowork session, later) | Podcast redesign | Replaced 16-stage pipeline with lighter NotebookLM source-bundle agent; podcast moved out of CORTEX scope (content-prep skill, quality judged by human); new content workspace at `podcast/` |
| 2026-05-16 | (cowork session) | Content reorg | Introduced `content/babu-memoir/` and `content/podcast/<book>/` tree. Memoir refs moved from `reference/` to `content/babu-memoir/_system/`. Podcast moved to `content/podcast/ayyuhal-walad/` with single-txt episodes built by `scripts/podcast/build_episode_txt.py`. `reference/` now holds only repo-wide skill governance. File-ownership table updated accordingly. |
| 2026-05-16 | (cowork session, later) | Episode-txt format + chapters invariant | Bug: initial build script glommed all 5–6 draft files into the deliverable (8K–10K words, 2× NotebookLM ceiling). Rewritten to emit CUSTOMIZE PROMPT + SOURCE only, gated to [500, 5500] words per `notebooklm-best-practices.md`. New invariant enforced: `<book>/chapters/` must be non-empty before any episode is built. Populated 22 chapters for Ayyuhal Walad from source sections. |
| 2026-05-16 | (cowork session, later) | Phase 0 pipeline + chapter-as-SOURCE + enrichment whitelist | v3.3: strict 1:1 chapter ↔ episode mapping. Chapter file IS the SOURCE block (no more `01-source-primary.md` in drafts). New `content/podcast/_system/enrichment-sources.md` whitelist (Tier 1 author corpus → Tier 5 Ismaili tradition → Tier 6 near-Ghazali Sufis). Phase 0 protocol (0a–0g) encoded in `SKILL.md` §1.5. A/B/C rule: rewrite-for-articulation allowed; 1,500-floor / 2,500–3,500-target / 4,500-ceiling; ≤60% outside enrichment. Build script signature `<BOOK_DIR> <EP##-slug>` with slug-parity invariant. Ayyuhal Walad migrated: 22 thin chapters archived, 5 substantive promoted as enrichment-pending. |
| 2026-05-16 | (cowork session, later) | Chapter IS source + Phase 0 enrichment protocol | Strict 1:1 chapter ↔ episode mapping adopted (chapter slug == episode slug). Eliminated `01-source-primary.md`; chapter file IS the SOURCE. Phase 0 rewritten: extract → English refinement → Arabic phonetic pass → chapter design (meaningful separation, balanced size) → enrichment (Tier 1–7 whitelist; ≤60% outside material). New whitelist file `content/podcast/_system/enrichment-sources.md` (author's corpus, Quran, hadith, Imam Ali, Ismaili tradition, Sufi tradition, modern reference). Build script call signature changed to `BOOK_DIR EP##-<slug>` with slug-match chapter lookup. |
| 2026-05-16 | (cowork session, later) | NotebookLM hygiene: HTML-comment stripping + meta-prose anti-pattern | Bug caught by Asif: chapter files (plain .txt) carried `<!-- ENRICHMENT STATUS -->` headers + "This file is a refined presentation…" paragraphs that NotebookLM would read out loud. `build_episode_txt.py` now strips all `<!-- ... -->` blocks and hard-refuses any chapter containing meta-prose tells (`This file is`, `Phase 0`, `Nothing has been added…`, etc.). All 5 Ayyuhal Walad chapters cleaned. Protocol encoded in SKILL.md §6, Quality Gate item 4a, orchestrator content invariants, framework.md Rule 7. |
| 2026-05-16 | (cowork session, later) | podcast-challenger agent (semantic-quality gate) | New agent `.github/agents/podcast-challenger.agent.md`. Complements `build_episode_txt.py` (structural gate) by validating semantic quality: citation authenticity, phonetic coverage, enrichment depth, framing 4-part structure, NotebookLM literalness. 30 checks across 6 categories (Authenticity, NotebookLM literalness, Pronunciation, Enrichment & depth, Articulation & shape, Framing integrity). Convergence loop ≤3 iterations. Auto-fixes deterministic issues (em-dashes, cross-episode refs, honorific repetition, lexicon parity); flags semantic findings. Sidecar report at `BOOK_DIR/_system/challenger-report.md`. Orchestrator ship-readiness gate refuses upload intents until `SHIP-READY` verdict. Podcast skill Phase 4 adds challenger-to-convergence step before compile. |
| 2026-05-16 | (cowork session, later) | Two-file deliverable model (v3.4 architecture refactor) | Architecture inversion caught by Asif: v3.3.x had `episodes/EP##.txt` concatenating CUSTOMIZE PROMPT + SOURCE blocks, requiring per-upload copy-paste split. New model: `chapters/chNN-<slug>.txt` IS the SOURCE (uploaded directly), `episodes/EP##-<slug>.txt` IS the CUSTOMIZE PROMPT only (pasted into Customize box). `build_episode_txt.py` rewritten — validates chapter as-is (no transformation), emits customize-prompt-only episode txt from `00-framing.md`. Chapter metadata moved from inline HTML comments to sidecar `BOOK_DIR/_system/enrichment-log.md`. Chapter files are upload-ready by construction. All 5 Ayyuhal Walad chapters + framings updated; episode txts shrink from ~4,000 to ~900 words each. podcast-challenger bumped to v1.1 with scope clarifications. |

Next audit: when any skill's tier is meaningfully updated (overlay merged into plugin SKILL.md, WIP skill graduates, etc.) — record date, auditor, scope, and result.

---

## How to add a new skill to the registry

1. Author the skill's SKILL.md (or skill.md for staging).
2. Author its `cortex-compliance.md` (in-skill) or its `skill-overlays/<name>-cortex-overlay.md` (for read-only plugins).
3. Self-assess against the framework's adoption checklist (Section 4 of framework).
4. Determine the target tier.
5. Add a row to the "Active skills" table above with the framework version targeted and the SKILL.md / overlay path.
6. If the skill claims write ownership over any files, add to "File ownership" table.
7. Update the audit log.

## How to graduate a skill's tier

1. Apply outstanding gaps from the skill's compliance doc.
2. Re-self-assess against framework's adoption checklist.
3. If percentage applicable items satisfied increased into the next tier band, update the registry table.
4. Add a row to the audit log.

## How to deprecate / retire a skill

1. Add to "Retired skills" table.
2. Note retirement date and reason.
3. If files owned by the retired skill should pass to another owner, update "File ownership" table.
4. Remove from "Active skills" table.
5. Update audit log.
