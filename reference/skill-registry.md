# Skill Registry

**Purpose:** Single source of truth for every skill in the user's Cowork ecosystem, its CORTEX Challenger Framework compliance tier, and its file ownership claims.

**Authority:** Anchored to `reference/cortex-challenger-framework.md` v1.0.

---

## Active skills

| Skill | Tier | Framework version | Status | SKILL.md or overlay path |
|---|---|---|---|---|
| **CORTEX** | BASELINE | self-defining | Active (plugin) | `~/.claude/skills/cortex/SKILL.md` |
| **ADLC** | GOLD | predates framework but compatible | Active (plugin) | `~/.claude/skills/adlc/SKILL.md` |
| **Podcast** | OUT OF SCOPE (content-prep, by design) | n/a | Active in staging — content-prep skill, intentionally exempt from CORTEX per SKILL.md §9; quality judged by human listening, not automated gates | `journal/skills-staging/podcast/SKILL.md` (content workspace: `journal/podcast/`) |
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
| `chapters/*.txt` | journal |
| `reference/translations-glossary.md` (memoir sections) | journal |
| `reference/quotes-library.txt` | journal (other skills propose) |
| `reference/clinic-library.txt` | journal (other skills propose) |
| `reference/incident-bank.md` | journal only |
| `reference/voice-fingerprint.md` | journal only |
| `reference/voice-fingerprint-light.md` | journal (used by Babu app orchestrators) |
| `reference/voice-deep-analysis.md` | journal only |
| `reference/craft-techniques.md` | journal only |
| `reference/master-context.md` | journal only |
| `reference/thematic-arc.md` | journal only |
| `reference/biographical-context.md` | journal only |
| `reference/memoir-rules-supplement.txt` | journal only (P0 governance file) |
| `reference/locked-paragraphs.md` | journal only (P0 governance file) |
| `reference/temporal-guardrail.md` | journal only (P0 governance file) |
| `reference/chapter-status.md` | journal only |
| `reference/journal-workflow-v2.md` | journal only |
| `reference/quotes-workflow.md` | journal only |
| `reference/skill-registry.md` | this file — framework owns |
| `reference/cortex-challenger-framework.md` | framework only (locked) |
| `reference/skill-overlays/*` | each skill owns its own overlay |
| `podcast/*` (content workspace: registry, episodes, archive) | podcast |
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
