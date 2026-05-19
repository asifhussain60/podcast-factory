# Plan Conventions

Cross-cutting conventions that don't belong in any one phase block but bind the whole plan together. Each section is load-bearing — if you're a future Claude session reading this for the first time, honor these literally unless the operator overrides in conversation.

## Machine routing — branch is the assignment

When the operator asks **"what's next"** / **"execute next"** / **"where am I"** on any machine, the assistant:

1. Reads the current git branch via `git branch --show-current`.
2. If the branch is `book/<slug>`, reads `content/podcast/library/**/<slug>/_system/orchestrator-state.json` for that book's current phase + status.
3. If the branch is `feat/*` or `develop` or `main`, treats it as plan/pipeline-source work and recommends the next acceptance-criteria row to ship or the next phase to launch.
4. **Runs the artifact-readiness check** (see below) — identifies which on-disk artifacts the next action requires, checks whether each is present, and ASKS the operator for any that are missing.
5. Once all required artifacts are present, recommends a single concrete next action (a command to run, a decision to make, or a file to read).
6. On operator confirmation, executes it.

### Artifact-readiness check

Before recommending or executing the next action, the assistant enumerates **required artifacts** for the action and asks the operator interactively for any missing ones. Don't fail silently or recommend a command that will error on a missing input — surface the gap up front.

**Required-artifact lookup by action:**

| Action | Required artifacts | Where each lives | If missing, ask operator |
|---|---|---|---|
| Launch Phase 0a (new book) | source PDF | `content/podcast/library/<category>/<slug>/_system/source/<filename>.pdf` | "Where is the source PDF for `<slug>`? Paste a path or confirm you've dropped it at `<expected path>`." |
| Resume Phase 0c+ on Arabic-scan book | refined-english.md + (optional) content-range.md + (optional) operator-review.md | `_system/source/text/` + book top-level | If content-range.md missing on a halted-for-transcript-review book: "Want to declare a content range before resume, or run on the whole transcript?" |
| Phase 0f operator gate | series-plan.md (orchestrator writes), persona override + tier decision (operator inputs) | `_system/series-plan.md` (orchestrator) | "Persona override (Mentor+Student, Skeptic+Believer, Two Practitioners, default Curious+Scholar)? Tier (default_deep_dive, longer, extended)? Episode count + boundaries OK as auto-suggested?" |
| Ship book to NotebookLM | episodes/EP##-*.txt + transcripts/ directory | book top-level | "Confirm you've uploaded EP## to NotebookLM and dropped the Audio Overview transcript into `transcripts/`?" |
| Land plan-source edit | (varies — usually none) | n/a | n/a — proceed |

**The operator never has to remember which file goes where.** When they say `what's next` and the next action needs an artifact that isn't on disk, the assistant asks for it. Examples:

- Operator on Mac Studio after fresh checkout of `feat/podcast-w1-foundation`, says `what's next`. Assistant detects Asaas preflight artifacts present, source PDF missing. Asks: *"To launch Asaas Phase 0a, I need the source PDF. Where is it? Either paste the full path and I'll copy it to `content/podcast/library/books/asaas-al-taveel/_system/source/`, or drop it there yourself and reply 'done'."*

- Operator on Mac Air, branch is `book/kitab-al-riyad`, state shows `phase=0f, phase_status=halted`. Assistant asks: *"Phase 0f gate. Three decisions needed: (a) persona override; (b) tier; (c) episode count + boundaries. Want to do them interactively now or paste a series-plan.md you already drafted?"*

- Operator on either Mac, branch is `feat/*`, says `what's next`. Assistant looks at the acceptance checklist + plan, recommends the next-highest-priority unshipped row. No artifact ask — plan work doesn't need physical inputs beyond the file itself.

### Add new actions here

When a new action type is introduced (e.g., "launch trainer dry-run", "promote vocabulary cache"), append a row to the table above so future Claude sessions know the artifact prerequisites and the operator phrasing for the ask.

The git branch IS the machine assignment. The state file IS the position within that book's pipeline. No per-machine config files (`hostname` matching is brittle); no separate runbook (duplicates what git + state files already encode).

If the operator has multiple machines and wants different books on each, the workflow is just:
- Mac A: `git checkout book/<slug-A>` → KaR-style work
- Mac B: `git checkout book/<slug-B>` → Asaas-style work
- Both push to `origin/book/<slug-X>` on their own schedule
- Plan / pipeline-source work happens on `feat/podcast-w1-foundation` via worktree on either Mac

The pipeline doesn't enforce one-machine-per-book today (P12 in W4 ships the formal mutation API + worker pool); manual coordination via branch checkout is the convention until then.

## Operator-invocable shorthand

The operator can use any of these phrasings; they all trigger the same convention:

- `what's next`
- `execute next`
- `where am I`
- `next action`
- `/next`

The assistant should NOT ask clarifying questions about what to do — it should read state and recommend. The operator can redirect if the recommendation is wrong.
