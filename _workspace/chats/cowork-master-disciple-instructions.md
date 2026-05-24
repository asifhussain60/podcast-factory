# Cowork Instructions — `the-master-and-the-disciple` analysis (parallel session)

**Context for the coworker:** Another Claude Code session is actively running long LLM work on the `book/kitab-al-riyad` branch — currently in Phase 0d (chapter contract regeneration) with an autonomous orchestrator running in the background, headed toward Phase 0e (enrichment) and 0f halt. A third session (Mac Studio) is concurrently working on `book/asaas-al-taveel`. **Your job is to stay completely off both of those branches and out of any path they touch.**

---

## 1. Branch isolation (DO THIS FIRST)

Before any other work:

```bash
# Confirm you are NOT on book/kitab-al-riyad or book/asaas-al-taveel
git rev-parse --abbrev-ref HEAD
```

If the output is `book/kitab-al-riyad` or `book/asaas-al-taveel` → **stop**, do not touch anything, and switch to a different branch.

Recommended setup: create or check out a dedicated branch for master-and-disciple work, ideally in a separate git worktree so the parallel sessions don't fight over the working tree:

```bash
# From the main worktree at /Users/asifhussain/PROJECTS/journal:
git worktree add ../journal-master-disciple book/the-master-and-the-disciple
# (creates the branch if it doesn't exist yet; if it does, just checks it out)

cd ../journal-master-disciple
git rev-parse --abbrev-ref HEAD   # → book/the-master-and-the-disciple
```

If `book/the-master-and-the-disciple` doesn't exist on remote yet, branch it from `develop` (not `main`, not from a `book/*` branch — those carry per-book artifacts you don't want).

---

## 2. Path lanes — where you can write, where you cannot

### ✅ Safe to read AND write

| Path | Notes |
|---|---|
| `content/drafts/the-master-and-the-disciple/**` | Your entire scope. Chapter prose, scaffolding, _notebooklm/, any new analysis files. |
| `_workspace/audit/the-master-and-the-disciple/` | Use this for local scratch — diffs, drafts, comparison files. Already gitignored. |
| Your own session-scratch in your worktree's local-only paths | Anything you create in `_workspace/logs/`, `_workspace/orchestrator-logs/`, `_workspace/audit/` is gitignored. |

### ✅ Safe to READ only (never write or edit)

| Path | Why |
|---|---|
| `scripts/podcast/**` | Pipeline framework shared by all books. Edits here would collide with both other sessions. |
| `content/podcast/.skill/**` | Skill handbook. Read for reference; do not modify. |
| `content/_shared/**` | Shared Arabic manifest, pronunciation key, etc. Read-only authority. |
| `skills-staging/**` | Read for reference. |
| `_workspace/plan/operators/*.md` | Cross-machine coordination layer. Read your peer's view; do not write any operator file other than (eventually) one for yourself if Asif sets you up. |
| `.gitignore`, `CLAUDE.md`, root config files | Do not edit. |

### 🚫 Hard-forbidden — never touch under any circumstances

| Path | Reason |
|---|---|
| `content/drafts/kitab-al-riyad/**` | Active book on a peer session. Any write collides. |
| `content/drafts/asaas-al-taveel/**` | Studio's book. Same reason. |
| Branches `book/kitab-al-riyad` and `book/asaas-al-taveel` | Hands off entirely. |
| `~/.claude/projects/-Users-asifhussain-PROJECTS-journal/memory/**` | Cross-session memory store (if applicable to your machine). |

---

## 3. Forbidden commands

Do NOT run any of these — they would either invoke the orchestrator (which is already running for KaR) or alter shared state:

```bash
# DO NOT run
python3 scripts/podcast/orchestrate_book.py --resume <anything>
python3 scripts/podcast/orchestrate_book.py --initial <anything>

# DO NOT run /podcast skill end-to-end (it invokes the orchestrator)
# Specifically avoid: /podcast, /podcast-extract on KaR or asaas

# DO NOT cherry-pick from book branches
git cherry-pick <any-hash-from-book/kitab-al-riyad-or-book/asaas-al-taveel>

# DO NOT merge anything into main, develop, or peer book branches
git merge ...
git push origin main
git push origin develop
git push origin book/kitab-al-riyad
git push origin book/asaas-al-taveel

# DO NOT force-push your own branch (or any branch)
git push --force ...
```

Safe commands you CAN use:

```bash
# Push only your own branch
git push origin book/the-master-and-the-disciple

# Read peer state without writing
git log origin/book/kitab-al-riyad --oneline | head
git show origin/book/asaas-al-taveel:_workspace/plan/operators/mac-studio-primary.md
```

---

## 4. LLM cost awareness

Anthropic API quota is **shared** across all three concurrent sessions:

- Mac Studio (primary): asaas Phase 0a → 0c+ work
- Mac Air (secondary, peer of yours): kitab-al-riyad Phase 0d → 0e → 0f (running RIGHT NOW)
- You: master-and-disciple analysis (this session)

Phase 0d on KaR is mid-flight and Phase 0e (13 chapter enrichments at ~$0.50 each) is queued right after. Plus Studio's asaas work. **Heavy LLM work on your side now could throttle the orchestrator.**

Recommended: front-load read-only / analysis / drafting work (anything that doesn't shellout to `claude -p` or hit the API directly). If your task genuinely needs LLM calls (e.g., per-chapter review of master-and-disciple), batch them into short bursts rather than continuous loops.

The KaR session will halt at the 0f gate. After that, quota contention drops. Check with Asif before kicking off any large LLM-spending pass on master-and-disciple.

---

## 5. Architecture note for master-and-the-disciple specifically

This book is in **Pre-Refined Source Mode** (per `skills-staging/podcast/SKILL.md` §198) — Asif has already refined the chapter prose by hand. The pipeline's Phase 0a-0e MUST NOT be re-run on it (the orchestrator would re-refine + re-segment and destroy the editorial work).

- Canonical prose: `content/drafts/the-master-and-the-disciple/Ch-*-Refined.md` (frozen)
- Scaffolding: `_notebooklm/ch##-scaffolding.md` (this is where new authoring lands)
- Pronunciation: `_notebooklm/01-pronunciation-guide.md` (standing reference uploaded to NotebookLM)
- Per-episode customize prompts go in `_notebooklm/` or `episodes/` per the skill's pre-refined-source-mode spec

If your task involves editing chapter prose, ask Asif first.

---

## 6. Verification checklist before any write

Run these as a sanity gate before any tool that modifies a file:

```bash
# 1. I am on the right branch
git rev-parse --abbrev-ref HEAD       # → book/the-master-and-the-disciple

# 2. I am in the right worktree (not /Users/asifhussain/PROJECTS/journal)
pwd                                    # → e.g., /Users/asifhussain/PROJECTS/journal-master-disciple

# 3. The path I'm about to write is in my lane
echo "$TARGET_PATH" | grep -E '^(content/drafts/the-master-and-the-disciple|_workspace/audit/the-master-and-the-disciple)/' \
  || echo "STOP — write target is outside my lane"
```

If any of those three checks fails → stop, do not write, ask Asif.

---

## 7. If you discover something useful for the framework

Cross-cutting findings (e.g., a bug in `scripts/podcast/orchestrate_book.py`, a missing instruction in the skill handbook, a useful improvement to the shared Arabic manifest) — **do not patch them directly**. Instead:

1. Write the finding as a note under `_workspace/audit/the-master-and-the-disciple/findings-NNN.md` (gitignored).
2. Tell Asif about it in your next response so he can route it to the right session (Studio or the KaR-driver Air session) when their work-in-flight settles.

This avoids the three-way edit conflict the framework files would otherwise see.

---

## 8. End-of-session handoff

When you stop work:

1. Commit your changes on `book/the-master-and-the-disciple` (do not touch other branches).
2. Push: `git push origin book/the-master-and-the-disciple`.
3. Leave a one-paragraph status note for Asif in `_workspace/chats/cowork-master-disciple-status.md` (or wherever Asif directs).

Do NOT open a PR or merge to main without explicit instruction.
