# infra/claude-agents — tracked Claude Code agent wrappers

This directory is the **tracked source-of-truth for the subagent registration wrappers** that Claude Code reads from `.claude/agents/<name>.md` at runtime.

`.claude/` is gitignored (`.gitignore` line 10) because it carries per-machine state. The wrappers themselves are *not* per-machine — they are deterministic content (frontmatter + a pointer to the canonical spec at `.github/agents/<name>.agent.md`). Tracking them here lets every Mac materialize the same wrappers via `scripts/install-claude-skills.sh`.

## Installation

```sh
scripts/install-claude-skills.sh
```

The install script:
- Copies every `infra/claude-agents/*.md` into `.claude/agents/<name>.md`
- Skips this `_README.md`
- Reports `--dry-run` mode when called with that flag

## Wrappers shipped here

| Wrapper | Canonical spec | Skill that drives it |
|---|---|---|
| `journal-challenger.md` | `.github/agents/journal-challenger.agent.md` | `/journal` Phase 4 step 2 (HARD GATE) |
| `podcast-challenger.md` | `.github/agents/podcast-challenger.agent.md` | `/podcast` Phase 4 step 3 (HARD GATE) |
| `podcast-extract.md` | `.github/agents/podcast-extract.agent.md` | `/podcast` Phase 0d extraction |
| `refine-prompt.md` | `.github/agents/refine-prompt.agent.md` | `/refine-prompt` |
| `ui-reviewer.md` | (no canonical spec; self-contained) | Post-`site/` edits (via `.claude/hooks/ui-reviewer-stop.sh`) |

## Adding or editing a wrapper

1. Edit (or add) the file under `infra/claude-agents/`.
2. Re-run `scripts/install-claude-skills.sh`.
3. Commit the change.

Editing `.claude/agents/<name>.md` directly is **not durable** — the next install will overwrite it. Always edit here.
