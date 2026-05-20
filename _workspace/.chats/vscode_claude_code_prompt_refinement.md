# Refined Prompt for VS Code Claude Code Extension

```markdown
# BLUF

You are working in VS Code using the Claude Code extension. Reevaluate the journal repo holistically, then realign the podcast skill, agent architecture, orchestration workflow, HTML plan, and pending fixes into one deterministic, regression-safe todo list.

Do not skip work. Do not scatter tasks across separate plans. Fold every finding, previous implementation, pending issue, and requested fix into one prioritized todo list with status, safety notes, dependencies, and acceptance criteria.

# Objective

Make the repo reflect this intended architecture:

1. **Journal agent / journal skill**
   - Sole boundary: build and maintain `babu-memoirs`.
   - It should not be fed automatically by the podcast pipeline.

2. **Podcast agent / podcast skill**
   - Sole boundary: convert source content — PDF, TXT, MP3, DOCX, transcripts, etc. — into refined, rewritten, reformatted chapter/episode source files designed for Google NotebookLM consumption.
   - Output should include episode hints/customization guidance.
   - Remove, not merely disable, podcast functionality that automatically feeds journal, clinical, and quote libraries.
   - Any transfer into those libraries becomes a manual process.

# Required Research First

Before editing files:

1. Review the current repo structure, git history, branches, and recent commits.
2. Review the existing podcast skill end-to-end:
   - ingestion
   - OCR / translation
   - refinement
   - phonetics
   - chapter design
   - enrichment
   - series plan
   - registry
   - per-chapter processing
   - trainer
   - merge
3. Review the journal skill boundary and confirm whether it is isolated to `babu-memoirs`.
4. Review the attached prior-work transcript and treat completed work as already done unless the repo proves otherwise.
5. Consult current online documentation for Claude Code, Claude Code VS Code extension, subagents, skills, hooks, background tasks, checkpoints, and best practices.
6. Synthesize findings into a concrete understanding before implementation.

Claude Code VS Code supports plan review, inline diffs, @-mentions, multiple conversations, checkpoints, and CLI interop; use those workflows intentionally. Skills should follow progressive disclosure: concise `SKILL.md` metadata and instructions, with larger references/scripts split into supporting files when needed.

# Prior Work to Fold In

Treat the following as prior work that must be verified, not blindly repeated:

1. `book/kitab-al-riyad` branch was pushed to remote.
2. Podcast orchestrator large-book fixes were implemented:
   - 0b / 0c chunking.
   - 0d map-reduce by source chapter.
   - 0e per-chapter enrichment loop.
   - Resume-safe checkpoints.
   - `unit_mode: chapter | section | auto`.
   - `--retry-phase`.
3. Async orchestration was running for `kitab-al-riyad`.
4. A wait-banner format was chosen and should be used whenever asking the user to wait on async work.
5. Duplicate agents were identified as a likely problem from overlapping discovery paths:
   - `.github/agents/*.agent.md`
   - `infra/claude-agents/*.md`
   - local `.claude/agents/*.md`
6. Phase names like `0a`, `0b`, `0c` should be evaluated for migration to meaningful sequential names.
7. A progress/heartbeat mechanism should be researched and added to the todo list before implementation.
8. API tests must become true E2E tests and must be included in the plan.

# Safety Rule for Async Work

Before any file edits, check whether an async process is running.

If async work is running:

1. Do not touch files under the active book path, especially:
   - `_system/orchestrator-state.json`
   - `_system/source/text/**`
   - `_system/source/text/_chunks/**`
   - `chapters/**`
   - `chapter-contracts/**`
   - `episodes/**`
   - transcripts or trainer outputs
2. Read-only inspection is allowed.
3. Do not run another LLM-heavy orchestrator or competing `claude -p` process.
4. If the requested task is unsafe during the async process, add it to the todo list and explicitly mark it `BLOCKED UNTIL ASYNC COMPLETE`.

When asking the user to wait, use this exact banner style:

```text
╔══════════════════════════════════════════════════════════════════╗
║  ⏸  WAITING ON ASYNC WORK — DO NOT START NEW LLM RUNS            ║
╠══════════════════════════════════════════════════════════════════╣
║  BOOK     │ {title}                                              ║
║  AUTHOR   │ {author or unknown}                                  ║
║  PAGES    │ {page_count or unknown}  │  SOURCE  │ {type/size}    ║
║  BRANCH   │ {branch}                                             ║
╠══════════════════════════════════════════════════════════════════╣
║  RUNNING                                                         ║
║   • {process name} ({terminal/process id}) — {current phase}      ║
║     log: {log path}                                              ║
║                                                                  ║
║  NEXT GATE   │ {next human or automated gate}                    ║
║  PROGRESS    │ {phase/unit count/percent if available}           ║
║  SAFE WORK   │ {paths safe to edit}                              ║
║  DO NOT      │ {paths not safe to touch}                         ║
╚══════════════════════════════════════════════════════════════════╝
```

# Primary Todo List Requirements

Create one consolidated todo list before implementation. Every item must include:

- ID
- priority
- status
- scope
- safe-to-run-while-async: yes/no
- dependencies
- acceptance criteria
- verification command or concrete check

The todo list must include, at minimum:

## P0 — Safety and Current-State Verification

1. Detect any active async orchestrator process.
2. Identify current branch and git status.
3. Confirm remote status for all `book/*` branches.
4. Confirm whether `kitab-al-riyad` async run completed, failed, or is still running.
5. Confirm current orchestrator state file and latest log tail.
6. Do not execute unsafe tasks while async is active.

## P0 — Podcast Skill Boundary Cleanup

1. Confirm podcast skill currently only produces NotebookLM-ready source chapters and episode customization artifacts.
2. Locate all code paths that automatically feed:
   - journal library
   - clinical library
   - quote library
3. Remove those code paths entirely if they exist.
4. Replace automatic transfer with a documented manual export/import handoff.
5. Verify no dead flags or disabled-but-still-present code remains.

## P0 — Journal Skill Boundary Cleanup

1. Confirm journal agent/skill boundary is only `babu-memoirs`.
2. Remove or reroute any podcast-specific responsibilities from journal agents.
3. Verify journal agent docs, skill docs, and HTML plan reflect the boundary.

## P0 — E2E API Test Plan

1. Identify the API test referenced by the current repo.
2. Convert or extend it into a true E2E test.
3. Ensure the test exercises real content-to-podcast orchestration boundaries, not just mocks.
4. Include sunny-day and rainy-day cases.
5. Add the E2E test to the validation gate.

Acceptance criteria:
- Test can be run from a documented command.
- It fails on broken orchestration.
- It validates generated artifacts, state transitions, and expected failure handling.

## P1 — Podcast Orchestrator Functional Verification

Verify the current end-to-end podcast flow after the prior large-book changes:

1. `0b` chunked refinement.
2. `0c` chunked phonetics.
3. `0d` map-reduce chapter design.
4. `0e` per-chapter enrichment.
5. `0f` human-review series plan gate.
6. `0g` registry.
7. per-chapter processing.
8. trainer.
9. merge.
10. final done state.

Do not claim the flow is fully functional until a real or representative end-to-end run passes.

## P1 — Large PDF Strategy

Evaluate and document:

1. Current Azure / OCR size limits and failure modes.
2. Whether PDF splitting is necessary now or only after Phase 0a failures.
3. Whether intelligent PDF splitting by context can be safely added later.
4. Whether current map-reduce orchestration is sufficient for large Arabic PDFs.
5. Guardrails for resume-safe processing.

Recommended default:
- Keep PDF intact unless OCR/ingestion fails.
- Prefer map-reduce after OCR.
- Add PDF splitting only as an additive pre-stage with clear checkpoints.

## P1 — Async Progress Tracking

Research only first, then add implementation to todo list.

Best recommended design:
1. Add a read-only status helper that can summarize:
   - current phase
   - phase status
   - completed chunks
   - total chunks
   - elapsed time
   - current log tail
2. Add a future heartbeat file:
   - `_system/heartbeat.json`
   - atomically written
   - updated before and after each meaningful unit of work
3. Keep structured logs as JSONL if useful:
   - `_system/orchestrator-events.jsonl`
4. Ensure status tracking is safe, resume-friendly, and does not corrupt state.

Do not implement this while an unsafe async process is writing related files unless the change is clearly isolated and approved.

## P1 — Duplicate Agent Cleanup

Investigate why duplicate agents appear in VS Code.

Required checks:
1. List all agent discovery locations.
2. Compare `.github/agents/*.agent.md`, `infra/claude-agents/*.md`, and `.claude/agents/*.md`.
3. Identify canonical source of truth.
4. Preserve any unique agent that exists only in a stale location.
5. Delete stale duplicates only after migration.
6. Update installer scripts so duplicates do not regenerate.
7. Verify VS Code/Claude Code agent list shows only the intended primary agents.

Recommended canonical source:
- `.github/agents/*.agent.md` for VS Code/Copilot-style agents.
- Generate `.claude/agents/*.md` from that source only if Claude Code requires it.
- Remove `infra/claude-agents` after unique content is migrated.

## P1 — Primary Agent List Alignment

Realign the visible primary agent list to the user’s intended design.

Use the screenshot as evidence, but verify against repo files. The visible list should not show duplicate stale agents.

Primary visible agents should map cleanly to the two repo boundaries:
1. Journal agent / journal skill
2. Podcast agent / podcast skill

Supporting agents may exist internally, but the primary VS Code list should be minimal and non-duplicative.

## P1 — Phase Name Migration

Evaluate renaming phase IDs from `0a`, `0b`, etc. to meaningful sequential names.

Proposed mapping:

| Old | New |
|---|---|
| `pre-flight` | `01-preflight` |
| `branch` | `02-branch` |
| `scaffold` | `03-scaffold` |
| `0a` | `04-ocr-translate` |
| `0b` | `05-refine-english` |
| `0c` | `06-phonetics` |
| `0d` | `07-chapter-design` |
| `0e` | `08-enrichment` |
| `0f` | `09-series-plan` |
| `0g` | `10-register-series` |
| `per-chapter` | `11-per-chapter` |
| `trainer` | `12-trainer` |
| `merge` | `13-merge` |
| `done` | `14-done` |

Migration requirements:
1. Add backward-compatible aliases.
2. Migrate existing `orchestrator-state.json` safely.
3. Keep old phase IDs accepted by `--retry-phase` for at least one transition period.
4. Update docs, HTML, logs, and reports.
5. Do not break active or resumable book runs.

## P1 — HTML Plan Realignment

Update the plan/HTML to reflect:

1. Two-agent/two-skill architecture.
2. Podcast-only content conversion boundary.
3. Manual handoff to journal/clinical/quote libraries.
4. Large-book orchestration design.
5. E2E API test requirement.
6. Async status/heartbeat plan.
7. Duplicate-agent cleanup.
8. Sequential phase naming plan.
9. Clear acceptance criteria.

## P2 — Journal and Podcast Intelligence Sources

Create a list of journals and podcasts that synthesize knowledge from source materials and build durable intelligence.

Purpose:
- Ensure agent work is deterministic.
- Ensure source-derived knowledge is always consulted.
- Prevent ineffective, context-free work.

This should not be a generic media list. It should be repo-integrated guidance:
1. What knowledge source exists.
2. Where it lives.
3. Which agent/skill should consult it.
4. When it must be consulted.
5. How freshness or staleness is detected.

# Implementation Rules

1. Work in small, reviewable commits.
2. Before edits, show the todo list and wait for approval if async safety is uncertain.
3. Use git checkpoints frequently.
4. Do not remove files until replacements are verified.
5. Prefer additive migration layers before destructive cleanup.
6. Never claim success without verification.
7. When deleting stale duplicates, prove:
   - canonical replacement exists
   - no unique content is lost
   - installer scripts do not recreate duplicates
8. When changing phase names, preserve resume compatibility.
9. When changing orchestration, preserve the invariant:
   - one episode = one source file = one contract/customization artifact = one NotebookLM upload

# Output Format

Produce the following:

## 1. Understanding

Briefly confirm the intended repo architecture and the two agent boundaries.

## 2. Current-State Findings

Summarize:
- git status
- active async processes
- current book orchestration state
- relevant branches/remotes
- current duplicate-agent sources
- current phase naming risks

## 3. Consolidated Todo List

A single prioritized todo list containing every task above and any additional repo-discovered tasks.

## 4. Safety Assessment

Explicitly mark:
- safe now
- unsafe while async is running
- blocked pending user approval
- blocked pending async completion

## 5. Execution Plan

Group work into safe batches:
- Batch A: read-only verification
- Batch B: safe docs/todo updates
- Batch C: code changes after async clears
- Batch D: migration/deletion work
- Batch E: E2E validation

## 6. Acceptance Criteria

Include observable checks for:
- no duplicate visible agents
- podcast no longer feeds journal/clinical/quote libraries automatically
- journal boundary limited to `babu-memoirs`
- content-to-podcast orchestration passes E2E
- large book resume works
- phase aliases preserve old state files
- async progress can be polled
- HTML plan matches implementation

## 7. Final Recommendation

Give one recommended next action.
Do not execute destructive changes until approved.
```

## Notes on Sources Folded In

The attached prior-work transcript records the already-completed and pending orchestration work, including the large-book chunking/map-reduce changes, duplicate-agent research, phase-renaming concern, async wait-banner preference, and heartbeat/progress-tracking research.

The refined prompt also aligns with current Claude Code VS Code guidance: the extension supports plan review, inline diffs, @-mentions, multiple conversations, checkpoints, and CLI interop, while Anthropic’s Skills guidance emphasizes concise `SKILL.md` metadata, progressive disclosure, bundled scripts/resources, and evaluation-driven iteration.

