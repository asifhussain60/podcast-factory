# Air machine sync — Phase 8 of the repo-split runbook + ongoing-sync bootstrap

> **HISTORICAL — DO NOT EXECUTE.** This runbook documents the 2026-05-22 Phase 8
> sync from the pre-split layout to the *original* post-split layout
> (`podcast-factory/main/` as the main worktree, linked worktrees as siblings).
> That sync ran successfully; Air is now several layout iterations beyond what
> this runbook describes. Current canonical layout is **Option 2 container**:
> the main worktree lives at `podcast-factory/worktrees/main/`, with siblings
> `podcast-factory/worktrees/{book-asaas, book-islr, book-kar}/` and
> filesystem-only `podcast-factory/{library, raw}/` above. See
> [`../plan/operators/setup/machines.md`](../plan/operators/setup/machines.md)
> for the current per-machine layout and `git log` on develop for the migration
> commits (44e339c → a130746 → 8937501 → ce92396).
> Path references below (`podcast-factory/main`, `/PROJECTS/journal`, etc.)
> reflect the layout that was being migrated TO at the time of writing, not
> the current state. Kept for historical context.

**Purpose:** bring Asif's MacBook Air ("Air") into sync with Studio Mac's post-split state, AND wire up the cross-machine workflow so future sessions are seamless. Paste the contents of this file from the next `---` to end-of-file into a fresh Claude Code session on Air.

**Companion docs (Air's Claude can read them after Step 3 pulls develop):**
- [`_workspace/runbooks/repo-split.md`](repo-split.md) — canonical reference for the split, §11 = Phase 8, §2A.6 = target layout
- [`_workspace/plan/operators/coordination-protocol.md`](../plan/operators/coordination-protocol.md) — write/push/session/concurrency rules
- [`_workspace/plan/operators/macbook-air-secondary.md`](../plan/operators/macbook-air-secondary.md) — Air's own operator file (Air writes; Studio reads)
- [`_workspace/plan/operators/start-session.sh`](../plan/operators/start-session.sh) — canonical daily session opener
- [`_workspace/plan/operators/setup/recreate-from-scratch.md`](../plan/operators/setup/recreate-from-scratch.md) — full recreate documentation
- [`docs/multi-mac-runbook.md`](../../docs/multi-mac-runbook.md) — multi-mac philosophy + Phase 1 per-Mac bootstrap

**Authored on Studio 2026-05-22** after Studio completed Phases 1–7, 9, and 9.5 of the repo split (incl. KaR EP10 first promotion) and pushed all of it to `origin/develop` on `asifhussain60/podcast-factory`.

---

You are Claude Code running on Asif's MacBook Air. Your job has two halves:

1. **Sync the split** — catch Air up to the post-Phase-9.5 state of `origin/develop` on the renamed repo, give Air the contained-parent worktree layout, and clone the new memoir repo separately.
2. **Bootstrap the seamless workflow** — set `~/.machine-id`, install Claude Code skills + git hooks + Azure secrets, document the daily session-open, so Asif can move between Studio and Air without per-session friction.

End state on Air:

```
<Air's-parent-dir>/
├── podcast-factory/
│   └── main/                       ← formerly <Air's-parent>/<old-clone>/, owns .git/
│       (+ any linked worktrees Air had, mapped to siblings of main/)
└── journal/                        ← new clone of github.com/asifhussain60/journal
```

`<Air's-parent-dir>` = whatever parent directory Air's existing clone currently sits in (per the operator file, this is `/Users/asifhussain/PROJECTS/` — but VERIFY by discovery in Step 0; don't hard-code).

**Authorization model:** auto-mode for mechanical steps (`git fetch`, `ls`, `cat`, parsing manifests, reading state files). **HALT and surface to Asif before:**
- Any `rm -rf`, `git reset --hard`, force-flag operation
- Step 5 — the filesystem `mv` chain that reorganizes Air's worktree(s)
- Step 7's Azure bootstrap (if Air's `az` is not yet logged in — surface so Asif can decide whether to log in interactively)
- Step 8 (merge `develop` → `book/kitab-al-riyad`) — this is a coordination decision, NOT a mechanical sync step; surface and wait

**Do not push, do not force, do not delete remote refs.** Studio has already handled all GitHub-side state. Air's role is local-only.

**Discovery, not assumption.** Air's filesystem may differ from what the Studio-authored operator file records. Discover the current clone path via `git -C` lookups, parse `git worktree list --porcelain` for the actual worktree set, and verify each assumption before acting.

---

## Step 0 — Identify the machine + discover Air's filesystem layout

```bash
hostname              # expect something like Asifs-MacBook-Air.local
whoami                # likely asifhussain (NOT ahmac, which is Studio's user)

# Studio recorded Air's path as /Users/asifhussain/PROJECTS/journal in
# macbook-air-secondary.md. Confirm or correct via discovery.
CANDIDATES=(
  "/Users/asifhussain/PROJECTS/journal"
  "$HOME/PROJECTS/journal"
  "$HOME/Code/Journal"
  "$HOME/Code/journal"
)
AIR_CLONE=""
for c in "${CANDIDATES[@]}"; do
  if [ -d "$c/.git" ] || [ -f "$c/.git" ]; then
    AIR_CLONE="$c"
    break
  fi
done
test -n "$AIR_CLONE" || { echo "ABORT: cannot find Air's existing clone — surface to Asif"; exit 1; }
echo "Air's clone: $AIR_CLONE"

# Derive parent dir (where podcast-factory/ + journal/ will end up)
AIR_PARENT="$(dirname "$AIR_CLONE")"
echo "Air's parent dir: $AIR_PARENT"

# Studio's backup date — Air mirrors this for cross-machine parity
DATE=2026-05-22
mkdir -p "$HOME/Backups/repo-split-$DATE"
echo "DATE=$DATE  BACKUP_DIR=$HOME/Backups/repo-split-$DATE"
```

Report all four values (`hostname`, `whoami`, `AIR_CLONE`, `AIR_PARENT`) to Asif before continuing. If `AIR_CLONE` doesn't resolve, surface and stop — do not improvise the path.

## Step 1 — Pre-flight: clean working tree(s) + no unpushed commits

```bash
cd "$AIR_CLONE"
git worktree list
git worktree list --porcelain > "$HOME/Backups/repo-split-$DATE/air-worktree-manifest-pre-move.txt"

# Confirm every worktree is clean
for w in $(git worktree list --porcelain | grep "^worktree " | awk '{print $2}'); do
  echo "--- $w ---"
  ( cd "$w" && git status --short )
done

# Refresh remote-tracking refs
git fetch origin --prune

# Detect unpushed local commits on every branch
for br in $(git branch --format='%(refname:short)'); do
  if git rev-parse --verify "origin/$br" >/dev/null 2>&1; then
    unpushed=$(git rev-list --count "origin/$br..$br" 2>/dev/null || echo 0)
    [[ "$unpushed" -gt 0 ]] && echo "UNPUSHED: $br has $unpushed local-only commit(s)"
  else
    echo "LOCAL-ONLY BRANCH: $br (no origin counterpart — captured by Layer 2 tar only)"
  fi
done
```

If any worktree shows changes Asif cares about, OR any branch has unpushed local commits, **halt and surface** before continuing. The backup in Step 2 captures filesystem state via tar (defense-in-depth), but Asif may prefer to push first.

## Step 2 — Backup (Air-local; two independent restore layers)

```bash
cd "$HOME/Backups/repo-split-$DATE"

# Layer 1: mirror clone (captures every ref)
git clone --mirror "$AIR_CLONE" Journal-air-mirror.git
echo "Mirror: $(du -sh Journal-air-mirror.git | cut -f1)"
echo "Refs in mirror: $(git -C Journal-air-mirror.git for-each-ref | wc -l)"

# Layer 2: filesystem tar of Air's parent dir (captures untracked + IDE state)
# BSD tar wants --exclude flags BEFORE the paths
cd "$AIR_PARENT"
tar --exclude='*/node_modules' \
    --exclude='*/.venv' \
    --exclude='*/_workspace/Books' \
    --exclude='**/.DS_Store' \
    -czf "$HOME/Backups/repo-split-$DATE/air-worktrees-snapshot.tar.gz" \
    $(basename "$AIR_CLONE") \
    $(ls -d "$(basename "$AIR_CLONE")"-* 2>/dev/null)

ls -lh "$HOME/Backups/repo-split-$DATE/"
```

Both layers must exist and be non-empty before you proceed. If either is missing, halt.

## Step 3 — Update remote URL + pull develop (the actual sync)

```bash
cd "$AIR_CLONE"
git remote -v
git remote set-url origin https://github.com/asifhussain60/podcast-factory.git
git remote -v   # confirm

git fetch origin --prune

# Switch to develop FIRST so --ff-only lands on the right branch
git checkout develop
git pull --ff-only origin develop

git log --oneline -5
```

If `--ff-only` fails (develop diverged locally on Air — unlikely but possible if Air had unpushed develop commits), **halt and surface**. Do NOT create a merge commit silently.

## Step 4 — Verify the post-Phase-9.5 layout landed on develop

```bash
# Journal surface removed
test ! -d content/babu-memoir && echo "OK: babu-memoir removed"           || echo "WARN: babu-memoir still present"
test ! -d site                && echo "OK: site/ removed"                  || echo "WARN: site/ still present"
test ! -d server              && echo "OK: server/ removed"                || echo "WARN: server/ still present"
test ! -d scripts/memoir      && echo "OK: scripts/memoir removed"         || echo "WARN: scripts/memoir still present"

# Phase 9.5 hoist landed
test -d library                              && echo "OK: library/ at top level"        || echo "WARN: library/ missing"
test -d _workspace/books                     && echo "OK: content/drafts/ workspace"  || echo "WARN: content/drafts/ missing"
test ! -d content/podcast/library            && echo "OK: content/podcast/library gone" || echo "WARN: content/podcast/library still present"
test -f scripts/podcast/ship_to_library.py   && echo "OK: ship_to_library.py present"   || echo "WARN: ship_to_library.py missing"
test -f .github/workflows/library-readonly.yml && echo "OK: library-readonly CI present" || echo "WARN: library-readonly CI missing"

# First promotion landed
test -f content/published/books/kitab-al-riyad/index.md && echo "OK: KaR EP10 promotion present" || echo "WARN: KaR EP10 promotion missing"
cat library/_meta/catalog.md 2>/dev/null

# Book + feat branches still resolve
git branch -a | grep -E "(book/|feat/)" | head -20
```

Any "WARN" means develop on origin is not what we expected — halt and surface. The structural moves in Step 5 would be unsafe without a known-good baseline.

## Step 5 — HALT GATE: contained-parent reorganization (with discovery)

Show the planned moves to Asif. Wait for explicit go-ahead before executing.

**Generate the plan from Air's actual worktree manifest:**

```bash
DATE=2026-05-22
CLONE_BASENAME="$(basename "$AIR_CLONE")"           # e.g., "journal" on Air
# Discover Air's linked worktrees from the manifest captured in Step 1
LINKED=$(grep "^worktree " "$HOME/Backups/repo-split-$DATE/air-worktree-manifest-pre-move.txt" \
         | awk '{print $2}' | grep -vF "$AIR_CLONE$" | xargs -n1 basename 2>/dev/null || true)

echo "Planned moves:"
echo "  $AIR_CLONE → $AIR_PARENT/podcast-factory/main"
for src in $LINKED; do
  # Each linked worktree dir on Air is likely named like "<clone>-<branch>" — strip the
  # "<clone>-" prefix for the target name. Adjust if Air's naming convention differs.
  dst="${src#${CLONE_BASENAME}-}"
  echo "  $AIR_PARENT/$src → $AIR_PARENT/podcast-factory/$dst"
done

# Pre-check the target parent doesn't already exist
test -e "$AIR_PARENT/podcast-factory" && \
  echo "ERROR: $AIR_PARENT/podcast-factory already exists — halt and inspect"
```

**HALT here.** Show Asif the move plan + the target parent pre-check result. Wait for explicit "go". The move chain is reversible only via Step 2's tar restore — be intentional.

**On Asif's "go":**

```bash
DATE=2026-05-22
MOVED_FILE="$HOME/Backups/repo-split-$DATE/air-moved-worktrees.txt"
: > "$MOVED_FILE"

# Close VS Code / Finder windows on $AIR_CLONE first (Asif handles this manually)

cd "$AIR_PARENT"
mkdir podcast-factory

# Move the main clone (the one that owns .git/)
mv "$CLONE_BASENAME" podcast-factory/main || {
  echo "ERROR: failed to move $CLONE_BASENAME → podcast-factory/main"
  rmdir podcast-factory 2>/dev/null
  exit 1
}

# Move each linked worktree (if any)
for src in $LINKED; do
  dst="${src#${CLONE_BASENAME}-}"
  if mv "$src" "podcast-factory/$dst"; then
    echo "$dst" >> "$MOVED_FILE"
    echo "Moved: $src → podcast-factory/$dst"
  else
    echo "ERROR: failed to move $src → podcast-factory/$dst"
    echo "  Partial state captured in $MOVED_FILE"
    echo "  Recovery: tar-restore from Step 2 (repo-split.md §14.8 Path F)"
    exit 1
  fi
done

# Repair worktree linkage from the new main location
cd "$AIR_PARENT/podcast-factory/main"
REPAIR_PATHS=()
while IFS= read -r dst; do
  REPAIR_PATHS+=("$AIR_PARENT/podcast-factory/$dst")
done < "$MOVED_FILE"

if [ "${#REPAIR_PATHS[@]}" -gt 0 ]; then
  git worktree repair "${REPAIR_PATHS[@]}"
fi
git worktree list

# Sanity check each moved location
for d in main $(cat "$MOVED_FILE"); do
  echo "--- $d ---"
  (cd "$AIR_PARENT/podcast-factory/$d" && git status --short && git log -1 --oneline)
done
```

If `git worktree repair` errors, **HALT** — restore via Step 2's tar (`repo-split.md §14.8 Path F`). Do NOT hand-edit `.git` files.

## Step 6 — Clone the new `journal` (memoir) repo into the freed namespace

```bash
test -e "$AIR_PARENT/journal" && {
  echo "ERROR: $AIR_PARENT/journal already exists — halt and inspect"
  exit 1
}

cd "$AIR_PARENT"
git clone https://github.com/asifhussain60/journal.git
cd journal

git status
git log --oneline -3
ls -la

# Sanity check: this is the memoir repo, NOT podcast-factory
test -d content/babu-memoir   && echo "OK: babu-memoir present"
test -d site                  && echo "OK: site/ present"
test -d scripts/memoir        && echo "OK: scripts/memoir present"
test ! -d content/podcast     && echo "OK: no podcast surface"
test ! -d infra/azure         && echo "OK: no Azure surface"
test ! -d server              && echo "OK: no server/ (API proxy retired)"
test ! -f wrangler.toml       && echo "OK: no Cloudflare scaffold"
```

Any failed check → surface and stop.

## Step 7 — Bootstrap for seamless cross-machine work

This is where the prompt diverges from a pure split-sync into setup-for-ongoing-work. Each sub-step is idempotent; safe to re-run.

### 7a. Machine identity (required by `start-session.sh` + coordination protocol)

```bash
test -f ~/.machine-id || echo macbook-air-secondary > ~/.machine-id
cat ~/.machine-id   # expect: macbook-air-secondary
```

If `~/.machine-id` already exists with a different value, **halt and surface** — do not overwrite without Asif's go-ahead.

### 7b. Install Claude Code skills + agents (podcast-factory side)

```bash
cd "$AIR_PARENT/podcast-factory/main"
bash scripts/install-claude-skills.sh --dry-run   # preview
# On clean dry-run output:
bash scripts/install-claude-skills.sh
```

This materializes `.github/agents/*` + `skills-staging/*` into Air's Claude Code runtime (`~/Library/Application Support/Claude/skills/<name>/SKILL.md` and `.claude/agents/<name>.md`). Re-runnable safely.

### 7c. Install git hooks (post-commit auto-push, pre-commit checks)

```bash
cd "$AIR_PARENT/podcast-factory/main"
bash scripts/install-git-hooks.sh
ls -la .git/hooks/ | grep -v sample
```

The post-commit hook auto-pushes operator-file commits (per the runbook's coordination model). Pre-commit hooks live in `scripts/git-hooks/`.

### 7d. Install skills in the journal repo too

```bash
cd "$AIR_PARENT/journal"
test -f scripts/install-claude-skills.sh && bash scripts/install-claude-skills.sh \
                                          || echo "(no installer in journal — skip)"
```

The journal repo has its own independent skill set per the split (Phase 4); installing it makes the journal skills (memoir-orchestrator, memoir-challenger, journal `/journal` skill) callable.

### 7e. Azure stack bootstrap (only if Air will run the pipeline)

If Air is going to drive `orchestrate_book.py` runs, Azure secrets must land in Air's Keychain. Two paths:

**Path 1 — one-shot bootstrap script (~30 min on a fresh Mac):**

```bash
cd "$AIR_PARENT/podcast-factory/main"
bash infra/azure/bootstrap-new-mac.sh
```

Surfaces an `az login` browser prompt if Air isn't logged in. **Halt and surface to Asif** if `az login` is needed — Asif decides whether to do it now.

**Path 2 — already-Azure-logged-in machine:**

```bash
cd "$AIR_PARENT/podcast-factory/main"
make store-keys        # fetches Azure secrets into Keychain
make verify            # checks resources + Keychain entries
make azure-probe       # live connectivity round-trip
```

Expected on success: `make azure-probe` shows 5/5 PASS (Translator credentials + live `en→fr` round-trip, Doc Intelligence reachable, Speech credentials present). `make verify` may report Keychain entries under alternate names — that's cosmetic if `azure-probe` passes.

If Air does NOT need to drive pipeline runs (e.g., Air is read-only for the foreseeable future), skip 7e entirely. Pipeline work can stay on Studio.

### 7f. Quick functional probes

```bash
cd "$AIR_PARENT/podcast-factory/main"

# Orchestrator can read state from the new workspace path
python3 scripts/podcast/orchestrate_book.py --status kitab-al-riyad

# Ship script is callable + parses series-plan from the new workspace
python3 scripts/podcast/ship_to_library.py --book kitab-al-riyad --episode EP10 --dry-run
# Expected: lists EP10 outputs that are ALREADY present in library/ (idempotent re-promotion)

# Journal repo loads cleanly
cd "$AIR_PARENT/journal"
test -f CLAUDE.md && head -5 CLAUDE.md
```

## Step 8 — Coordination: pending merge of develop → book/kitab-al-riyad

**Read first, surface, do NOT execute:**

```bash
cd "$AIR_PARENT/podcast-factory/main"
git fetch origin --prune

# Read Air's own operator file from origin/develop (avoids local-vs-remote confusion)
git show origin/develop:_workspace/plan/operators/macbook-air-secondary.md | head -120

# Read Studio's view from origin/develop
git show origin/develop:_workspace/plan/operators/mac-studio-primary.md | head -60

# Check: did Studio re-push book/kitab-al-riyad with the archetype-driven manual finish?
git log --oneline origin/book/kitab-al-riyad | head -20
```

The Air operator file's `next_action` lists pending sync tasks: (a) merge `origin/develop` → `book/kitab-al-riyad`, (b–d) operator-file housekeeping. These are coordination decisions, NOT mechanical syncs:

- **If Studio is still driving the KaR archetype-driven manual finish** (status: HALTED-BY-OPERATOR), wait. Air is parked; Studio re-pushes when ready.
- **If Studio has finished and re-pushed `book/kitab-al-riyad`**, then `git checkout book/kitab-al-riyad && git pull --ff-only` brings Air to Studio's HEAD. From there, merging develop into the branch picks up Phase 9.5 in Air's KaR working tree too.

**HALT and surface the state. Wait for Asif's decision before any merge.**

## Step 9 — Final verification + summary

```bash
echo "=== podcast-factory ==="
cd "$AIR_PARENT/podcast-factory/main"
git remote -v
git worktree list
git log --oneline -3
test -f library/_meta/catalog.md && cat library/_meta/catalog.md

echo "=== journal ==="
cd "$AIR_PARENT/journal"
git remote -v
git log --oneline -3

echo "=== Air-local config ==="
cat ~/.machine-id
ls "$AIR_PARENT/" | grep -E "(podcast-factory|journal)"
```

Report the output back to Asif as the final summary. Compare with Studio's two-repo layout (`~/Code/podcast-factory/{main,book-asaas,book-islr,feat-w1}` + `~/Code/journal/`) — Air's set should be `$AIR_PARENT/podcast-factory/main` (plus any linked worktrees that were discovered) + `$AIR_PARENT/journal/`.

---

## Daily workflow after this sync — how Air opens a session

From now on, every Air session should start with:

```bash
cd "$AIR_PARENT/podcast-factory/main"   # or whichever podcast-factory worktree is active
bash _workspace/plan/operators/start-session.sh
```

That script reads `~/.machine-id`, switches to Air's assigned book branch, `git pull --ff-only`, and prints `next_action` + orchestrator state. It's the canonical session opener — use it instead of manual `git fetch && git checkout && git pull` choreography.

For memoir work, sessions open in the journal repo:

```bash
cd "$AIR_PARENT/journal"
git pull --ff-only origin develop
# then invoke /journal skill or open the chapter you're working on
```

The two repos are fully independent post-split; nothing flows between them automatically. If Asif wants a memoir edit and a podcast edit in the same session, open two Claude Code windows — one per repo.

---

## Rollback (if any step fails)

| Failure point | Path |
|---|---|
| Step 1 — dirty tree / unpushed commits found | Stop. Surface. Asif decides whether to commit, push, stash, or ignore. |
| Step 2 — backup layer missing | Stop. Re-run the missing layer. Do NOT proceed without both. |
| Step 3 — `--ff-only` pull fails | Stop. Surface — develop diverged locally; Asif investigates. |
| Step 4 — verification warnings | Stop. Develop on origin is not what we expected; do not reorganize. |
| Step 5 — `mv` chain fails partway | Tar-restore from Step 2: `mv $AIR_PARENT/podcast-factory $AIR_PARENT/podcast-factory.BROKEN.$(date +%s)` then `cd $AIR_PARENT && tar -xzf $HOME/Backups/repo-split-$DATE/air-worktrees-snapshot.tar.gz`. See `repo-split.md` §14.8 (Path F). |
| Step 5 — `git worktree repair` errors | Same as above — tar restore, do NOT hand-edit `.git` files. |
| Step 6 — journal clone fails partway | `rm -rf "$AIR_PARENT/journal"` and retry. Pure local; no risk. |
| Step 7 — install scripts or Azure bootstrap error | Re-runnable individually. Surface and Asif decides per sub-step. |

If everything is unrecoverable: see `repo-split.md` §14.10 (NUCLEAR), but Air-side specifically — Air's mirror clone (Step 2 Layer 1) is the canonical restore source.

---

**End of prompt.** When Air's Claude finishes, expect: `$AIR_PARENT/podcast-factory/main` + (any of Air's linked worktrees as siblings) + `$AIR_PARENT/journal/`, both repos at canonical HTTPS URLs, `~/.machine-id` populated, Claude Code skills + git hooks installed, Azure stack reachable (if 7e ran), and Air's daily flow centered on `_workspace/plan/operators/start-session.sh`.
