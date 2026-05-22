# Air machine sync — Phase 8 of the repo-split runbook

**Purpose:** bring Asif's MacBook Air into sync with Studio Mac's post-split state. Paste this entire file (everything from the `---` below to end-of-file) into a fresh Claude Code session on Air to execute.

**Companion runbook:** [`repo-split.md`](repo-split.md) — Air's Claude can read it after Phase B completes the pull.

**Authored on Studio 2026-05-22 after Studio completed Phases 1–7, 9, and 9.5 (incl. KaR EP10 first promotion).**

---

You are Claude Code running on Asif's MacBook Air ("Air"). Your job: bring this Mac into sync with the post-split state of Studio Mac (Asif's primary podcast-factory machine). When you finish, Air has the same two-repo layout Studio has:

- `~/Code/podcast-factory/` — repo with `main/` + linked worktrees, mirroring Studio's contained-parent layout
- `~/Code/journal/` — single clone of the new memoir repo, no worktrees

**Context (what changed on Studio that you must catch up to):**

On 2026-05-22 Asif ran the `Journal` repo split on Studio. End state:

- `github.com/asifhussain60/Journal` was renamed to `github.com/asifhussain60/podcast-factory` (GitHub auto-redirect from the old URL).
- New `github.com/asifhussain60/journal` repo created via `git filter-repo` — holds only memoir + site files. No book/feat branches; just `develop` + `main`.
- Studio reorganized its worktrees: `~/Code/Journal{,-book-asaas,-book-islr,-feat-w1}` → `~/Code/podcast-factory/{main,book-asaas,book-islr,feat-w1}`.
- Phase 9.5 hoist: `content/podcast/library/<category>/` moved to root-level `_workspace/<category>/`; new top-level `library/` holds only shipped artifacts; `scripts/podcast/ship_to_library.py` is the only writer of `library/`; `.github/workflows/library-readonly.yml` enforces this on every PR.
- First promotion: `library/books/kitab-al-riyad/` populated with EP10 (motion-stillness-hyle-and-form, SHIP-WITH-CAUTION verdict).

**Authorization model:** auto-mode for mechanical steps (`git fetch`, `ls`, `cat`, parsing manifests). HALT and surface to Asif before:
- Any `rm -rf`, `git reset --hard`, force-flag operation
- The Phase D filesystem `mv` chain (worktree reorganization)
- Anything that touches GitHub state (`gh repo *`, force-push) — Studio handled all GitHub-side changes; Air's role is local-only

**Do not push, do not force, do not delete remote refs.** If you discover unpushed local commits on any branch, halt and surface — Asif decides whether to push first or rely on the backup tar.

**Reading material (after Phase B's pull lands):**
- `_workspace/runbooks/repo-split.md` §11 (Phase 8) is the canonical reference for this work
- `_workspace/runbooks/repo-split.md` §2A.6 shows the target on-disk layout
- `_workspace/runbooks/repo-split.md` §14.8 (Path G) is the rollback procedure if Air-side gets confused

## Step 0 — Confirm you're on the right machine + set $DATE

```bash
hostname            # should be Asif's Air machine
test -d ~/Code/Journal && echo "OK: pre-split layout present" \
                       || { echo "ABORT: ~/Code/Journal not found"; exit 1; }

# Studio used DATE=2026-05-22 for backup paths. Air mirrors that for cross-machine parity.
DATE=2026-05-22
echo "DATE: $DATE"
[[ "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "DATE format wrong"; exit 1; }
mkdir -p ~/Backups/repo-split-$DATE
```

Report findings to Asif before continuing. If Air's path layout differs (e.g., the main clone is somewhere other than `~/Code/Journal/`), surface that and ask — do not improvise.

## Step 1 — Pre-flight: clean worktrees + no unpushed commits

```bash
cd ~/Code/Journal
git worktree list
git worktree list --porcelain > ~/Backups/repo-split-$DATE/air-worktree-manifest-pre-move.txt

# Confirm every worktree is clean
for w in $(git worktree list --porcelain | grep "^worktree " | awk '{print $2}'); do
  echo "--- $w ---"
  ( cd "$w" && git status --short )
done

# Refresh remote state
git fetch origin --prune

# Check for unpushed local commits on every locally-existing branch
for br in $(git branch --format='%(refname:short)'); do
  if git rev-parse --verify "origin/$br" >/dev/null 2>&1; then
    unpushed=$(git rev-list --count "origin/$br..$br" 2>/dev/null || echo 0)
    [[ "$unpushed" -gt 0 ]] && echo "UNPUSHED: $br has $unpushed local-only commit(s)"
  else
    echo "LOCAL-ONLY BRANCH: $br (no origin counterpart)"
  fi
done
```

If `git status --short` shows uncommitted/untracked changes Asif cares about, OR if any branch has unpushed local commits, **halt and surface** before proceeding. The backup in Step 2 will capture filesystem state via tar (defense-in-depth), but Asif may prefer to push first.

## Step 2 — Backup (Air-local; independent restore path)

```bash
DATE=2026-05-22
mkdir -p ~/Backups/repo-split-$DATE

# Layer 1: mirror clone of Air's current Journal repo
cd ~/Backups/repo-split-$DATE
git clone --mirror ~/Code/Journal Journal-air-mirror.git
echo "Mirror size: $(du -sh Journal-air-mirror.git | cut -f1)"
echo "Refs: $(git -C Journal-air-mirror.git for-each-ref | wc -l)"

# Layer 2: filesystem tar of all Air-side Journal* directories
# (BSD tar requires --exclude flags BEFORE the paths)
cd ~/Code
tar --exclude='*/node_modules' \
    --exclude='*/.venv' \
    --exclude='*/_workspace/Books' \
    --exclude='**/.DS_Store' \
    -czf ~/Backups/repo-split-$DATE/air-worktrees-snapshot.tar.gz \
    $(ls -d Journal Journal-* 2>/dev/null)

ls -lh ~/Backups/repo-split-$DATE/
```

Verify both files exist and are non-empty. If either layer is missing, **halt and surface**. Do not proceed to destructive steps without both backup layers landed.

## Step 3 — Update remote URL + pull develop (no destructive change)

```bash
cd ~/Code/Journal
git remote -v
git remote set-url origin https://github.com/asifhussain60/podcast-factory.git
git remote -v   # confirm

git fetch origin --prune

# Switch to develop FIRST so --ff-only lands on the right branch
git checkout develop
git pull --ff-only origin develop

# Show the post-pull state
git log --oneline -5
```

If `--ff-only` fails (develop diverged locally on Air — unlikely but possible), **halt and surface to Asif** — do NOT silently create a merge commit during the sync.

## Step 4 — Verify the post-Phase-9.5 file layout landed

```bash
# Journal surface removed
test ! -d content/babu-memoir && echo "OK: babu-memoir removed" || echo "WARN: babu-memoir still present"
test ! -d site && echo "OK: site/ removed" || echo "WARN: site/ still present"
test ! -d server && echo "OK: server/ removed (API proxy retired)" || echo "WARN: server/ still present"
test ! -d scripts/memoir && echo "OK: scripts/memoir removed" || echo "WARN: scripts/memoir still present"

# Phase 9.5 hoist landed
test -d library && echo "OK: library/ at top level" || echo "WARN: library/ missing"
test -d _workspace/books && echo "OK: _workspace/books/ workspace" || echo "WARN: _workspace/books missing"
test ! -d content/podcast/library && echo "OK: content/podcast/library gone" || echo "WARN: content/podcast/library still present"
test -f scripts/podcast/ship_to_library.py && echo "OK: ship_to_library.py present" || echo "WARN: ship_to_library.py missing"
test -f .github/workflows/library-readonly.yml && echo "OK: library-readonly.yml present" || echo "WARN: library-readonly.yml missing"

# First promotion landed
test -f library/books/kitab-al-riyad/index.md && echo "OK: KaR EP10 promotion present" || echo "WARN: KaR EP10 missing"
test -f library/_meta/catalog.md && echo "OK: catalog.md present" || cat library/_meta/catalog.md

# Book + feat branches still resolve
git branch -a | grep -E "(book/|feat/)" | head -20
```

If any "WARN" appears, halt and surface — that means develop on origin is not what we expected, and the worktree reorganization in the next step would be unsafe.

## Step 5 — HALT GATE: contained-parent worktree reorganization

Surface to Asif before running the `mv` chain. Show the planned moves first, then wait for explicit go-ahead.

**Target layout** (mirrors Studio's, but uses Air's actual worktree names — discovered from the manifest captured in Step 1):

```
~/Code/podcast-factory/
├── main/              ← current ~/Code/Journal (owns .git/ database)
└── <discovered linked worktrees, mapped: Journal-<name> → <name>>
```

**Generate the move plan:**

```bash
DATE=2026-05-22
LINKED_WORKTREES=$(grep "^worktree " ~/Backups/repo-split-$DATE/air-worktree-manifest-pre-move.txt \
                   | awk '{print $2}' | grep -v "/Journal$" | xargs -n1 basename)

echo "Planned moves (verify with Asif before executing):"
echo "  ~/Code/Journal → ~/Code/podcast-factory/main"
for src in $LINKED_WORKTREES; do
  dst="${src#Journal-}"
  echo "  ~/Code/$src → ~/Code/podcast-factory/$dst"
done

# Sanity: target parent must not exist
test -e ~/Code/podcast-factory && \
  echo "ERROR: ~/Code/podcast-factory already exists — halt and inspect"
```

**HALT and surface the move plan to Asif. Wait for explicit "go" before executing the move chain below.**

**On Asif's go (only):**

```bash
# Close VS Code / Finder windows on ~/Code/Journal* first (manual step)
DATE=2026-05-22
MOVED_FILE=~/Backups/repo-split-$DATE/air-moved-worktrees.txt
: > "$MOVED_FILE"

cd ~/Code
mkdir ~/Code/podcast-factory

# Move main clone (the one with .git/ directory)
mv Journal podcast-factory/main || {
  echo "ERROR: failed to move Journal → podcast-factory/main"
  rmdir ~/Code/podcast-factory 2>/dev/null
  exit 1
}

# Move each linked worktree using the discovered list from Step 5's plan
for src in $LINKED_WORKTREES; do
  dst="${src#Journal-}"
  if mv "$src" "podcast-factory/$dst"; then
    echo "$dst" >> "$MOVED_FILE"
    echo "Moved: $src → podcast-factory/$dst"
  else
    echo "ERROR: failed to move $src → podcast-factory/$dst"
    echo "  Partial state: see $MOVED_FILE for completed moves."
    echo "  Recovery: §14.8 Path F (filesystem tar restore) — do NOT attempt manual repair."
    exit 1
  fi
done

cat "$MOVED_FILE"

# Repair worktree linkage from the new main clone path
cd ~/Code/podcast-factory/main
REPAIR_PATHS=()
while IFS= read -r dst; do
  REPAIR_PATHS+=("$HOME/Code/podcast-factory/$dst")
done < "$MOVED_FILE"

git worktree repair "${REPAIR_PATHS[@]}"
git worktree list   # verify all paths now under ~/Code/podcast-factory/

# Sanity check each worktree
for d in main $(cat "$MOVED_FILE"); do
  echo "--- $d ---"
  (cd ~/Code/podcast-factory/"$d" && git status --short && git log -1 --oneline)
done
```

If `git worktree repair` errors or any worktree shows `fatal: not a git repository`, **HALT** — use `repo-split.md` §14.8 Path F (filesystem tar restore from `~/Backups/repo-split-$DATE/air-worktrees-snapshot.tar.gz`). Do NOT attempt manual `.git` file edits.

## Step 6 — Clone the new `journal` repo

```bash
test -e ~/Code/journal && {
  echo "ERROR: ~/Code/journal already exists — halt and inspect"
  exit 1
}

cd ~/Code
git clone https://github.com/asifhussain60/journal.git
cd journal

git status
git log --oneline -3
ls -la
```

Verify:
- branch is `develop` (default)
- `CLAUDE.md` exists and mentions memoir (not podcast)
- `content/babu-memoir/` exists
- `site/` exists
- `scripts/memoir/` exists
- NO `content/podcast/`, NO `scripts/podcast/`, NO `infra/azure/`, NO `server/`, NO `wrangler.toml`

If any verification fails, surface and stop.

## Step 7 — Final sync verification (Air-side mirror of runbook §13)

```bash
echo "=== podcast-factory ==="
cd ~/Code/podcast-factory/main
git worktree list
git remote -v
git log --oneline -3
test -f library/_meta/catalog.md && cat library/_meta/catalog.md

echo "=== journal ==="
cd ~/Code/journal
git remote -v
git log --oneline -3
git branch -a

echo "=== disk layout ==="
ls -la ~/Code/ | grep -E "podcast-factory|journal"
```

Report the output back to Asif as the final summary.

## Optional: Step 8 — Update Air's VS Code workspace bookmarks

If Air has `.code-workspace` files referencing the old paths, edit them so the `path` fields point at `~/Code/podcast-factory/<name>` instead of `~/Code/Journal*`. Air's Claude can grep for the old paths if needed; surface findings before editing.

## Rollback (if something goes wrong)

- **Failure in Step 3** (remote URL / pull): restore from Step 2's mirror via `git clone --no-local ~/Backups/repo-split-$DATE/Journal-air-mirror.git ~/Code/Journal-restore`.
- **Failure in Step 5** (worktree reorg): quarantine the partial state (`mv ~/Code/podcast-factory ~/Code/podcast-factory.BROKEN.$(date +%s)`) and tar-restore from `~/Backups/repo-split-$DATE/air-worktrees-snapshot.tar.gz`. See `repo-split.md` §14.8 Path F for the full procedure.
- **Failure in Step 6** (journal clone): just delete the partial clone and retry (`rm -rf ~/Code/journal && git clone https://github.com/asifhussain60/journal.git`).

---

**End of prompt.** When Air's Claude finishes, the final summary in Step 7 should match Studio's two-repo layout: `~/Code/podcast-factory/{main,…linked worktrees…}` + `~/Code/journal/`, both pointed at their respective canonical GitHub URLs.
