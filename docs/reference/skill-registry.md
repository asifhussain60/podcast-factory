# Skill Registry — podcast-factory repo

**Purpose:** Single source of truth for every skill present in THIS repo (the `podcast-factory` repo, renamed from `Journal` on 2026-05-22).

**Authority:** Anchored to `reference/cortex-challenger-framework.md` v1.0. Anything in `framework.md` defers to this file for skill-level detail.

The skill set here is a STRICT SUBSET of what existed pre-split — the journal skill (and css-theme-sync + ui-modernizer) moved to the sibling **[journal](https://github.com/asifhussain60/journal)** repo. Each duplicated general-utility skill is an INDEPENDENT COPY; changes do NOT cross-propagate to the sibling repo.

---

## Active skills — compliance

| Skill | Compliance Tier | Status | Definition path |
|---|---|---|---|
| **CORTEX** | BASELINE | Active (plugin) | `~/.claude/skills/cortex/SKILL.md` |
| **ADLC** | GOLD | Active (plugin) | `~/.claude/skills/adlc/SKILL.md` |
| **Clean-commit** | BRONZE (target) | Active (plugin) — overlay applies (duplicated copy) | `~/.claude/skills/clean-commit/SKILL.md` + `reference/skill-overlays/clean-commit-cortex-overlay.md` |
| **Podcast** | OUT OF SCOPE (content-prep) | Active in staging — exempt from CORTEX per SKILL.md §9; quality judged by human listening | `skills-staging/podcast/SKILL.md` |
| **Repo-surgeon** | BRONZE (target) | WIP in staging — consolidated to single skill.md (duplicated copy) | `skills-staging/repo-surgeon/SKILL.md` |
| **Studio-composer** | BRONZE (target) | Active in staging — behavioural contract for the Book Composer / Preview / LIVE Session surfaces; defers styling to html-view-quality | `skills-staging/studio-composer/SKILL.md` |

All skills target **CORTEX Challenger Framework v1.0**. The framework version is implicit unless a row says otherwise.

## Skills NOT present in this repo (sibling repo)

These live in the sibling **[journal](https://github.com/asifhussain60/journal)** repo:

- **Journal** — memoir authoring skill
- **CSS-theme-sync** — site CSS theme work
- **UI-modernizer** — site UI/UX modernization

## Retired skills

| Skill | Retired | Notes |
|---|---|---|
| **Trip-log** | 2026-05-16 | Memory tombstoned; plugin file still present (read-only) — disable via Cowork plugin settings to fully remove |
| **Cowork-brief** | 2026-06-02 | ADLC project tool; no invocation path in podcast-factory. Skill files removed from skills-staging/. Cortex overlay also deleted. |
| **Tell-me** | 2026-06-02 | ADLC/journal repo tool; no invocation path in podcast-factory. Skill files removed from skills-staging/. Cortex overlay also deleted. |
| **Usage-auditor** | 2026-06-02 | Journal repo tool (reads server/logs/); no invocation path in podcast-factory. Skill files removed from skills-staging/. |
| **Publish-podcast** | 2026-06-02 | Superseded by podcast-publisher agent. Gate descriptions absorbed into the agent spec. |

---

## Active skills — capabilities

Detail on what each skill owns, what triggers it, and what it explicitly defers to other skills.

### Podcast skill

| Skill | Purpose | Owns | Triggers |
|---|---|---|---|
| `podcast` | Convert scholarly Arabic books into NotebookLM Audio Overview podcast series | `content/<Bucket>/<slug>/` (all per-book state); publish = `status: published` flip in place via `publish_to_library.py` | `/podcast`, `/extract-chapter <ref>`, `claude --agent podcast-orchestrator` |

### Site-authoring skills

| Skill | Purpose | Owns | Triggers |
|---|---|---|---|
| `studio-composer` | Behavioural contract for the three Studio authoring surfaces (merged Edit canvas, whole-book Preview, LIVE Session) | `docs/standards/studio-composer-quality.md` (REQ-SC-*); defers styling to `html-view-quality` | "book composer", "compose view", "preview mode", "live session", "figure placement" |

### General-utility skills (duplicated independent copies from journal repo)

| Skill | Purpose | Triggers |
|---|---|---|
| `clean-commit` | Pre-commit / commit-quality discipline | "clean commit", "/clean-commit" |
| `repo-surgeon` | Holistic architecture audit, orphan cleanup, root hygiene | "/repo-surgeon", "repo surgery" |
