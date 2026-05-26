# Postprod-Review + Vacuum — Running Task Ledger

**Branch:** `book/the-master-and-the-disciple`
**Started:** 2026-05-26
**Status legend:** ⬜ pending · 🔄 in_progress · ✅ done · 🛑 halted-waiting-on-Asif · ⚠ blocked
**Authority:** This file is the source of truth across sessions. The in-session TaskCreate list mirrors this file but is ephemeral. On every session resume, re-read this file first and re-mirror to TaskCreate.

---

## Current state — at a glance

- **Awaiting Asif:** Approval of the 17-task plan + Turboscribe transcripts for the-master-and-the-disciple
- **Last action:** Reorganized `_workspace/plan/` root into 5 topical subfolders (conventions/, pipeline/, ship-criteria/, podcast-reader/, postprod-vacuum/); rewrote plan-root README as a bucket index; applied the no-version-marker filename rule (renamed `postprod-vacuum-v2-review.md` → `postprod-vacuum-review.md`; renamed `feedback_response_format_v2.md` → `feedback_response_format.md`; cleaned v2-as-version-label residue from response-format spec + global CLAUDE.md + global response-template); fixed cross-folder relative paths in moved files
- **Next halt point:** T4 (folder-name decision), T5 (vacuum-plan review before --apply), T14 (`m4a/v1/` policy)

---

## The 17 tasks

| # | Status | Task | Depends on | Notes |
|---|---|---|---|---|
| T1 | ⬜ | Seed archetype library (`scholarly-deep-dive`, `socratic-dialogue`, `narrative-prose`) under `content/_shared/archetypes/<genre>/{exemplar.md,spec.yml,anti-patterns.md}` + `scripts/podcast/_archetypes.py` registry | — | Per `feedback_extensibility_first.md` — registry, not hardcoded |
| T2 | ⬜ | Stamp `archetype:` field in both books' `meta.yml` + intake template | T1, T13 | KaR → `scholarly-deep-dive`; master-and-disciple → `socratic-dialogue` |
| T3 | ⬜ | Build `scripts/podcast/vacuum.py` driver | — | Spec at [vacuum.md](../../../infra/claude-agents/vacuum.md); plan/apply lifecycle |
| T4 | ⬜🛑 | Resolve `m4a/` vs `audio/` convention (first-run vacuum decision; asks Asif) | T3 | Persist to `content/_shared/conventions/audio-folder-name.txt`; lead recommendation = `m4a/` (3 of 4 already use it) |
| T5 | ⬜🛑 | **Retroactive vacuum sweep on the-master-and-the-disciple** | T3, T4, T14, transcripts | Renames NotebookLM-titled files → `ch##-<slug>.m4a`; plan first, --apply after approval |
| T6 | ⬜🛑 | Retroactive vacuum sweep on kitab-al-riyad | T3, T4, T14 | Messier: sibling `transcripts/`, orphan `Ch07/`, `english-transcript.md`, `operator-review.md` |
| T7 | ⬜ | Build `scripts/podcast/postprod_review.py` driver | T1, T2 | Spec at [postprod-review.md](../../../infra/claude-agents/postprod-review.md); loops PA–PJ |
| T8 | ⬜ | **Run postprod-review on the-master-and-the-disciple** (6 chapters) | T5, T7 | First real exercise of archetype layer |
| T9 | ⬜ | Enrich orchestrator's finalize-halt message with the postprod steps (NotebookLM → m4a → Turboscribe → vacuum → postprod) | T3, T7 | Don't add a new phase; just enrich existing halt instructions in `orchestrate_book.py` |
| T10 | ⬜ | Update CLAUDE.md (tier table) + framework.md (post-production phase) + trigger docs-updater | T9 | Lightest-touch version; vacuum --apply = Tier 1, plan = Tier 0, postprod-review = Tier 0 |
| T11 | ⬜🛑 | **BUG (re-scoped 2026-05-26)**: investigate SKIP/BLOCK decision-path in `_slide_convergence.py` + `_slide_authoring.py` for M&D's `per-chapter-slides` outcomes (4×SKIPPED + 2×BLOCKED). Slide-deck folder DOES exist at `_system/slide-decks/` with all 6 chapter subdirs; phase ran to completion. Bug is in the per-chapter decision predicate, not module wiring or trigger eligibility. Surface (a) the SKIP/BLOCK predicate, (b) which input drove each verdict, (c) whether SKIPPED is a true no-op or a silent regression. | — (parallel) | Per `feedback_slide_decks_required.md` — if SKIP turns out to be the predicate's correct verdict, that contradicts the standing rule and is itself a halt point. See [postprod-vacuum-review.md](postprod-vacuum-review.md) §3.1 + open question 1. |
| T12 | ⬜ | Post-merge audit (`podcast-auditor`) + categorized commit | All above | Per `feedback_post_merge_audit.md` standing rule |
| T13 | ⬜ | Schema-lock the `meta.yml` `archetype:` field — add a registered-archetype check inside `_archetypes.py` that fails loudly if a stamped value isn't in the registry | T1 | Prevents silent-mismatch class of bug at the seam between archetype declaration (T2) and consumption (T7/T8). See [postprod-vacuum-review.md](postprod-vacuum-review.md) §3.2. |
| T14 | ⬜🛑 | Decide explicit policy for `m4a/v1/` legacy directory (delete / archive to `_system/legacy/m4a-v1/` / leave) and persist alongside the m4a-vs-audio decision in `content/_shared/conventions/audio-folder-name.txt`; update vacuum plan to handle deterministically | T4 | M&D has `m4a/v1/` sibling to `m4a/transcripts/`; vacuum spec mentions removing legacy mp3s but the policy isn't pinned. See [postprod-vacuum-review.md](postprod-vacuum-review.md) §3.3 + open question 2. Halt point because policy choice is destructive/irreversible. |
| T15 | ✅ | **Workspace-root hygiene** — extend vacuum to always clean `_workspace/plan/` root on every invocation; extend podcast-auditor with AU-H1 to validate root stays clean; execute initial cleanup (21 files archived) | — | Locked 2026-05-26. Vacuum spec gained §9 (Workspace-root hygiene); auditor gained Axis E + AU-H1 probe. KEEP list pinned in vacuum.md §9. Initial sweep moved 21 stale files to `_archive/2026-05-26/`. The standing rule: vacuum runs root-hygiene pre-flight on EVERY invocation; auditor flags any sprawl that vacuum missed. |
| T16 | ✅ | **Universal "subfolder by default" root rule** — locked into vacuum spec §9 addendum + auditor probe AU-H1; immediate execution at `_workspace/` root (deleted `.DS_Store`; `README.md` retained as whitelist exception); follow-on execution: `_workspace/plan/` root reorganized into 5 topical subfolders (12 files moved); plan-root README rewritten as a bucket index. | T15 | Asif confirmed the 5-bucket structure via AskUserQuestion. Cross-folder relative paths in moved files updated (`../../` → `../../../` for repo-root refs). The standing rule: vacuum's pre-flight runs root-hygiene against the universal whitelist on EVERY invocation; auditor probe AU-H1 flags any drift. |
| T17 | ✅ | **No version markers in filenames** — universal rule locked. Filenames NEVER carry `v1`, `v2`, `vN`. Single canonical version per doc; history via git. Initial cleanup renamed `postprod-vacuum-v2-review.md` → `postprod-vacuum-review.md` and `feedback_response_format_v2.md` → `feedback_response_format.md`; prose using "v2" as a version label cleaned in the response-format spec + global CLAUDE.md + global response-template. | T16 | Locked 2026-05-26. Note: one residual book audit artifact carries a versioned name (`content/drafts/BOOKS/the-master-and-the-disciple/audits/v2.2-vs-v2.1-diff.md`). That file's purpose is literally to compare two earlier versions — per the new rule, that comparison should be done via `git diff` rather than persisted as a document. Flagged for follow-up: delete or rename. |

---

## Halt points

These are the points where I stop and ask Asif before continuing:

1. **Before T1 starts** — overall plan approval (CURRENT GATE)
2. **T4** — folder-name choice (`m4a/` vs `audio/`)
3. **T5** — vacuum plan review for master-and-disciple before `--apply`
4. **T6** — vacuum plan review for KaR before `--apply` (more destructive ops in this one)
5. **T11 → action** — once SKIP/BLOCK decision-path is understood, Asif decides: tighten predicate / regenerate / accept-as-is (latter contradicts `feedback_slide_decks_required.md` and requires explicit rule-edit)
6. **T14** — `m4a/v1/` policy choice (delete / archive / leave) before vacuum touches any `v1/` directory

---

## Cross-references (do not lose)

- Agent specs: [postprod-review.md](../../../infra/claude-agents/postprod-review.md), [vacuum.md](../../../infra/claude-agents/vacuum.md)
- Review companion: [postprod-vacuum-review.md](postprod-vacuum-review.md) — reconciles Asif's 2026-05-26 "Architecture Planning" brief against this ledger; source of T13, T14, and T11 rescope
- Standing rules consulted: `feedback_extensibility_first.md`, `feedback_slide_decks_required.md`, `feedback_systemic_fixes_from_chapter_archetype.md`, `feedback_post_merge_audit.md`, `project_repo_architecture.md`
- Pipeline boundary check (no duplicates found): `clean-commit`, `repo-surgeon`, `publish_to_library.py`, `podcast-challenger`, `podcast-auditor`, `slide-deck-challenger`
- Empty home folders for transcripts already created on disk (2026-05-26):
  - `content/drafts/the-master-and-the-disciple/m4a/transcripts/`
  - `content/drafts/kitab-al-riyad/m4a/transcripts/`
  - `content/published/books/the-master-and-the-disciple/audio/transcripts/`
  - `content/published/books/kitab-al-riyad/m4a/transcripts/`

---

## Change log

- **2026-05-26 (initial)** — File created. 12 tasks queued. `postprod-review.md` already on disk (170 lines). `vacuum.md` newly written (175 lines). Empty transcript folders created in 4 book locations. Awaiting Asif's plan approval + Turboscribe transcripts.
- **2026-05-26 (review fold)** — Folded deltas from [postprod-vacuum-review.md](postprod-vacuum-review.md) per Asif's approval (B + C). T11 re-scoped from "missing slide-decks folder" to "SKIP/BLOCK decision-path bug in `_slide_convergence.py`" (folder + phase exist; outcomes are 4×SKIPPED + 2×BLOCKED). T13 added (archetype schema-lock; blocks T2). T14 added (`m4a/v1/` legacy-directory policy; blocks T5/T6, depends on T4). Halt-points list extended (T11 escalation criteria sharpened; T14 added as halt #6). Rejected brief items (`_registry.md` artifact, post-prod-as-rename-owner) documented in review §3.4–3.5 — no ledger change needed since they were never in the plan. No code executed.
- **2026-05-26 (workspace-root hygiene)** — T15 added and immediately closed. Vacuum spec extended with Section 9 (Workspace-root hygiene: canonical KEEP list, sprawl categories, finding codes `VAC-PLAN-SPRAWL` / `VAC-PLAN-AMBIGUOUS` / `VAC-PLAN-ARCHIVE-MISSING`, standalone `--workspace-root` invocation, runs pre-flight on every vacuum call). Podcast-auditor extended with Axis E + probe AU-H1 (Workspace-root sprawl) which delegates to vacuum on detection. Initial cleanup executed: 21 files moved to `_workspace/plan/_archive/2026-05-26/` (5 dated event/audit reports including `STUDIO-ALIGNMENT-2026-05-22.md`, `cohesion-audit-2026-05-23.md`, `2026-05-19-redesign-{audit,proposal}-from-air.md`, `v4-doctrine-propagation.md`; 9 kashkole rollout artifacts; 2 landed F-item drafts `f25-*` + `f27-*`; 1 folded plan `numeric-symbolic-disambiguation-plan.md`; 1 book-specific handoff `handoff-kar-archetype-pivot.md`; 3 older proposals `podcast-intelligence-enhancements.md` + `podcast-plan-DoR.md` + `podcast-plan-DoR-appendix.md`). Plan/ root now holds 14 active files; `_drivers/`, `research/`, `view/` subfolders left untouched (research/ pruned of 2 dated "from-air" files).
- **2026-05-26 (universal subfolder rule)** — T16 added. Asif's stricter rule locked: every file lives in a subfolder; root is reserved for whitelisted categories only (`README.md`, `VERSION`, tool-required configs at fixed paths, index entry files, `CLAUDE.md` at repo root). Vacuum spec §9 gained the addendum with the root-legit whitelist + a worked-example mapping for `_workspace/plan/` topical subfolders. Auditor probe AU-H1 updated to enforce the universal rule across ALL folder roots, not just `_workspace/plan/`. Immediate execution scoped to `_workspace/` root: `.DS_Store` deleted (was git-ignored anyway); `README.md` retained as whitelist exception. `_workspace/` root now holds exactly one file: `README.md`.
- **2026-05-26 (plan/ root reorganization + no-version-markers rule)** — Asif confirmed the 5-bucket structure via AskUserQuestion (5 topical subfolders over broader or umbrella layouts). Created `conventions/`, `pipeline/`, `ship-criteria/`, `podcast-reader/`, `postprod-vacuum/`. Moved 12 files from `_workspace/plan/` root into their topical buckets via `git mv` (one untracked file moved with plain `mv` + `git add`). Plan-root README rewritten as a clean bucket index. Cross-folder relative paths in moved files updated (`../../infra/` → `../../../infra/` to account for the extra depth). T17 added and immediately closed: no version markers in filenames. Renamed `postprod-vacuum-v2-review.md` → `postprod-vacuum-review.md`; renamed `feedback_response_format_v2.md` → `feedback_response_format.md`; cleaned "v2" used as a version label from the response-format spec + global `~/.claude/CLAUDE.md` + global `~/.claude/response-template.md`. One residual versioned artifact flagged for follow-up: `content/drafts/BOOKS/the-master-and-the-disciple/audits/v2.2-vs-v2.1-diff.md` (its purpose is literally a version-comparison document; per the new rule, that belongs in `git diff` not in a persisted file). Plan/ root now holds only `README.md` + `VERSION`.
- **2026-05-26 (commit + merge develop + apply rule to develop's adds)** — Initial commit `fd79c98` landed all the above work. Pushed `book/the-master-and-the-disciple` to origin. Merged `origin/develop` into the branch (29 commits behind; auto-merged with no conflicts). Develop's three new plan-root files violated the just-locked subfolder rule, so vacuum's rule was applied to them too: `intelligence-pipeline-wave1-spec.md` → `pipeline/`; `kashkole-macstudio-preflight.md` → `kashkole/macstudio-preflight.md` (new bucket; redundant `kashkole-` prefix dropped from filename); `kashkole-translation-cost-ledger.jsonl` → `kashkole/translation-cost-ledger.jsonl`. Residual versioned audit file deleted (`v2.2-vs-v2.1-diff.md`). Final state: plan/ root holds only `README.md` + `VERSION`. Branch ready to merge to develop.
- **2026-05-26 (switched to develop + cherry-picked unique work)** — Tried `git merge --no-ff book/the-master-and-the-disciple` into develop; hit a wall of rename/rename + rename/delete conflicts because develop had independently consolidated its own plan folder (different bucket names: `debt/` vs `pipeline/`, `operations/` vs `ship-criteria/`, `reader/` vs `podcast-reader/`, plus a new `architecture.md` and `refactor/plan.md`). Aborted the merge and did a surgical cherry-pick instead: brought `infra/claude-agents/vacuum.md` (new), `infra/claude-agents/postprod-review.md` (new), the `AU-H1` probe + Axis E delta on `infra/claude-agents/podcast-auditor.md`, and this ledger pair into `_workspace/plan/postprod-vacuum/` on develop. Commit `22857b1` on develop. Plan-folder bucket-renames intentionally NOT brought across (duplicative with develop's parallel structure); the universal subfolder rule + no-version-markers rule are already represented on develop as DR-009 in `architecture.md`.
- **2026-05-26 (project-steward integration into the plan)** — Asif's previously-landed `project-steward` agent (commit `0e9bb7a` on develop) factored into the architecture: `architecture.md` Agent Ecosystem updated to 9 agents with steward shown as the strategic coordinator that composes tactical agents (`podcast-auditor`, `repo-surgeon`, `reconcile`) via dotted edges to a cited source corpus. New DR-014 added: *Strategic-tactical agent split: steward composes, doesn't reimplement*. Repo `CLAUDE.md` Tier 0 list updated to include `/steward <scope>` as a read-only protocol; corpus edits are Tier 2. No conflict with the postprod-vacuum agents — steward operates one layer above as a meta-coordinator, not as a peer.

---

## Update protocol

Every time I (or a future session) change a task's status, edit this file in the same turn:
1. Flip the status icon (⬜ → 🔄 → ✅ or 🛑/⚠)
2. Append a line to the change log with date + what changed
3. If new tasks discovered, append rows (T13+) — never renumber existing ones
4. If task obsoleted, mark ✅ with a note "obsoleted because…" — don't delete

This file is the canonical state. The in-session TaskCreate list is a convenience mirror; if the two disagree, this file wins.
