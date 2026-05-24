# From-scratch operator setup — blank Mac → working operator

Use this procedure when:
- Adding a new physical Mac to the operator pool
- Rebuilding after a wipe / reinstall
- Onboarding a new operator user account on an existing Mac

Walks from blank macOS to a Claude Code session that can run `start-session.sh` and pick up work.

## Prerequisites

- macOS (any recent version; tested on Darwin 24+)
- A GitHub account with read/push access to `asifhussain60/Journal`
- (Only if this Mac will drive Azure pipeline phases) An Azure account with permissions in the `Journal AI — primary` subscription

## Step 1 — Install command-line tools

```bash
xcode-select --install
git --version    # Confirm git is available
```

## Step 2 — Install Homebrew + project dependencies

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Required:
brew install python@3.11 jq azure-cli gh
# Recommended:
brew install ripgrep fd

# Verify:
python3 --version    # Must be ≥ 3.11 (cost-ledger silently fails on <3.11)
jq --version
az --version
gh --version
```

## Step 3 — Install Claude Code

```bash
# Either Homebrew:
brew install --cask claude-code
# Or Anthropic's official installer per https://claude.com/claude-code

# Authenticate:
claude login
# Follow the OAuth flow in browser. Auth is local to this Mac (not shared across Macs).

# Verify:
claude -p "Reply with exactly the word PONG."
# Expect: PONG
```

## Step 4 — Set up GitHub auth

```bash
# Option A — SSH (recommended for development machines):
ssh-keygen -t ed25519 -C "<your-email>"
# Hit Enter for default path, set a passphrase if desired
eval "$(ssh-agent -s)"
ssh-add --apple-use-keychain ~/.ssh/id_ed25519  # macOS-specific; stores passphrase in Keychain

gh auth login --git-protocol ssh --hostname github.com --web

# Verify:
gh auth status
ssh -T git@github.com   # Expect: "Hi <user>! You've successfully authenticated..."

# Option B — HTTPS via gh CLI token (if SSH is blocked):
gh auth login --git-protocol https --hostname github.com --web
```

## Step 5 — Clone the repo and set up worktrees

Pick a primary working directory. Convention so far:
- Studio: `~/Code/podcast-factory/book-asaas`
- Air: `~/PROJECTS/journal`
- New Mac: whatever's natural for that Mac's user

```bash
# Pick a base directory:
mkdir -p ~/PROJECTS    # or ~/Code, your call
cd ~/PROJECTS

git clone git@github.com:asifhussain60/Journal.git journal
cd journal

# You start on main; switch to develop:
git checkout develop
git pull --ff-only origin develop
```

### Install the post-commit auto-push hook

The repo has a post-commit hook that auto-pushes commits touching `_workspace/plan/operators/*`. It lives in `.git/hooks/` which is NOT tracked, so install it once per fresh clone:

```bash
# The canonical hook content (lives in coordination-protocol.md §2):
cat > .git/hooks/post-commit <<'EOF'
#!/usr/bin/env bash
# Auto-push commits touching operator files
if git diff-tree --no-commit-id --name-only -r HEAD | grep -qE '^_workspace/plan/operators/'; then
  branch=$(git rev-parse --abbrev-ref HEAD)
  echo "[post-commit] operator-file change detected on ${branch} — auto-pushing"
  git push origin "${branch}" && echo "[post-commit] push OK" || echo "[post-commit] push FAILED"
fi
EOF
chmod +x .git/hooks/post-commit
```

Verify by editing your (eventual) operator file: a commit there should trigger an auto-push line in the output.

## Step 5c — Materialize any in-flight content worktrees (only if joining work in progress)

Per [CLAUDE.md "Worktree workflow"](../../CLAUDE.md), every in-flight content branch lives in its own sibling worktree at `<projects-root>/git-worktrees/<slug>/` — NOT in the primary clone. The primary clone stays on `develop`; each content branch gets its own working directory.

**Projects-root convention**:
- Mac Air → `~/PROJECTS/git-worktrees/`
- Mac Studio → `~/Code/git-worktrees/`

(The auto-detection in `scripts/start-content-worktree.sh` resolves the right one from where the primary clone lives, so the same command works on both machines.)

### Pulling an existing content branch (joining another machine's work)

List what's in flight on the remote:

```bash
git -C <primary-clone> branch -r | \
    grep -E 'origin/(book|doc|lecture|article|letter|interview|draft)/' | \
    sed 's|origin/||'
```

For each branch you want to work on locally:

```bash
# Mac Air paths shown; substitute ~/Code on Mac Studio.
PRIMARY=~/PROJECTS/podcast-factory
SLUG=kitab-al-riyad                  # example
REF=book/kitab-al-riyad              # full <prefix>/<slug>

git -C "$PRIMARY" fetch origin --prune
git -C "$PRIMARY" worktree add ~/PROJECTS/git-worktrees/"$SLUG" "origin/$REF"
git -C ~/PROJECTS/git-worktrees/"$SLUG" branch --unset-upstream
git -C ~/PROJECTS/git-worktrees/"$SLUG" branch --set-upstream-to="origin/$REF"
```

The `--unset-upstream` then explicit `--set-upstream-to` dance fixes the upstream that `worktree add` sets to the source ref (`origin/develop` by default). After this, `git push` from the worktree pushes the content branch correctly, not `develop`.

### Starting a new piece of content

Use the helper — never hand-roll `git worktree add` for new content branches:

```bash
cd <primary-clone>
scripts/start-content-worktree.sh <category> <slug>
# Examples:
scripts/start-content-worktree.sh books   kitab-al-riyad
scripts/start-content-worktree.sh letters ayyuhal-walad
```

The helper fetches origin/develop, creates the typed branch via the prefix map in [scripts/podcast/_branching.py](../../scripts/podcast/_branching.py), creates the worktree at `<projects-root>/git-worktrees/<slug>/`, and unsets the upstream foot-gun. Idempotent — re-running for an existing branch prints where it's already checked out.

### Listing and cleanup

```bash
git worktree list                              # from any checkout, shows them all
git worktree remove <path>                     # after the branch is shipped/merged
git worktree prune                             # garbage-collect stale .git/worktrees entries
```

## Step 6 — Assign machine identity

Pick a machine slug. Convention: `<role>-<location>` (`mac-studio-primary`, `macbook-air-secondary`, `macbook-pro-asif-home`).

```bash
echo "<your-slug>" > ~/.machine-id
cat ~/.machine-id    # Verify
```

## Step 7 — Create your operator file

```bash
cd <repo>
git checkout develop

# Copy an existing operator file as a template:
cp _workspace/plan/operators/macbook-air-secondary.md \
   _workspace/plan/operators/<your-slug>.md

# Edit the new file's frontmatter:
#   - machine_id: <your-slug>
#   - hostname_hint: <your hostname; check with `hostname`>
#   - operator: <your name + email>
#   - worktree_layout: list of paths + branches on this Mac
#   - current_branch / current_book: leave as IDLE for now
#   - status_tag: IDLE
#   - current_phase: ""
#   - last_verified_at: <current UTC ISO>
#
# Edit the body sections to match your context. The §0 (session-start)
# and §1 (identity) sections need the most attention.

git add _workspace/plan/operators/<your-slug>.md
git commit -m "coord(<your-slug>): create operator file"
git push origin develop
```

Also update [../index.md](../index.md) to add your machine as a new column in the Machine Status table.

## Step 8 — Azure setup (ONLY if this Mac will drive Azure phases)

See [azure-stack.md](azure-stack.md) for the full reference. Briefly:

```bash
cd <repo>/infra/azure
az login
az account set --subscription "Journal AI — primary"
bash store-keychain-keys.sh    # Pulls keys from Azure → macOS Keychain
bash verify-azure.sh           # Live probe of all enabled resources
```

If `verify-azure.sh` is all green, Azure is wired for this Mac.

## Step 9 — Run session-starter and claim a book

```bash
cd <repo>
bash _workspace/plan/operators/start-session.sh

# Exit code 0 → ready (sitting on your assigned book branch)
# Exit code 1 → pre-flight failed (dirty tree / missing machine-id) — fix and retry
# Exit code 2 → IDLE (no book assigned) — claim one from book-queue.md
```

If IDLE, follow the claim protocol in [../book-queue.md](../book-queue.md):

```bash
# 1. Pull develop, read book-queue.md
git checkout develop
git pull --ff-only origin develop
cat _workspace/plan/book-queue.md

# 2. Pick the top of the Queue section, edit book-queue.md:
#    - REMOVE the chosen row from Queue
#    - ADD a row to In-flight with your machine_id, branch=book/<slug>, phase=pending,
#      started=<today UTC>, your notes
git add _workspace/plan/book-queue.md
git commit -m "book-queue: claim <slug> for <your-slug>"
git push origin develop   # If rejected, another machine claimed first — pull, pick new top, retry

# 3. Create the book branch:
git checkout -b book/<slug>
git push -u origin book/<slug>
```

## Step 10 — End-to-end verification

```bash
cd <your-primary-worktree>
git rev-parse --abbrev-ref HEAD      # Should be book/<slug> or develop
python3 --version                     # ≥ 3.11
claude -p "Reply with exactly the word PONG."   # Anthropic auth working
security find-generic-password -s azure-journal-language-endpoint -w   # If Azure set up
```

If all four checks pass, you're operational. Hand off to a Claude Code session to drive the work.

## Step 11 — Install the `podcast-operator` convenience aliases (optional but recommended)

The `podcast-operator` agent is Asif's unified entry-point — auto-detects machine, picks up where work was left off, surfaces drift + recap in the 4-part At-a-glance template. Three ways to invoke; pick whichever fits your workflow (or install all three):

```bash
# CLI flag — works from any terminal (no setup needed; already shipped via the agent file)
claude --agent podcast-operator

# Slash command in Claude Code chat (auto-registered after scripts/install-claude-skills.sh runs)
/podcast-operator

# Bash alias — shortest, requires adding to ~/.zshrc (or ~/.bashrc)
echo 'alias po="claude --agent podcast-operator"' >> ~/.zshrc
echo 'alias op="claude --agent podcast-operator"' >> ~/.zshrc   # alternative shorter alias
source ~/.zshrc
po --report-only    # quick drift table
po                  # full recap
po --execute-safe   # discovery + auto-execute safe ops
```

Full contract + safety rules at [../../../.github/agents/podcast-operator.agent.md](../../../.github/agents/podcast-operator.agent.md). Distinct from `podcast-orchestrator` (autonomous pipeline driver) — see the agent's intro paragraph for the workflow split.

## Common pitfalls

| Symptom | Fix |
|---|---|
| `claude: command not found` after install | Restart shell or `export PATH="$HOME/.local/bin:$PATH"` (path depends on installer) |
| `claude -p` hangs forever | Auth expired; `claude login` again |
| `security: command not found` | You're not on macOS — this whole flow assumes macOS. Linux/Windows operators are not supported (see [runtime-compatibility.md](runtime-compatibility.md)) |
| Azure `Unauthorized` on probe | Key rotated in portal; re-run [../../../../infra/azure/store-keychain-keys.sh](../../../../infra/azure/store-keychain-keys.sh) |
| Git push rejected on operator file | Peer machine pushed first; `git pull --rebase` and retry |
| Multiple worktree folders confuse you | They're the same git repo with one `.git/`; delete unused ones via `git worktree remove <path>` (the branch survives) |
| `start-session.sh` says IDLE forever | You haven't claimed a book; see Step 9 |
| Post-commit hook doesn't fire | `ls -la .git/hooks/post-commit` should show executable; recreate per Step 5 if missing |
| `~/.machine-id` not detected by start-session.sh | File must contain only the slug (no trailing newlines, no quotes); `cat ~/.machine-id` to verify |

## Where to go after setup

- [../coordination-protocol.md](../coordination-protocol.md) — the cross-machine rules
- [../book-queue.md](../book-queue.md) — what's queued for work
- [runtime-compatibility.md](runtime-compatibility.md) — which UIs work and which don't
- [machines.md](machines.md) — the current per-machine inventory (update it to add yourself)
