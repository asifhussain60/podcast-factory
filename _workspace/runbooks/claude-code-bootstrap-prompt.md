# Claude Code capability bootstrap — first-session audit

**Purpose:** when you open a fresh Claude Code session on either Mac (Studio
or Air) and you want Claude to confirm — before any real work — that it can
(a) call the **Anthropic API + Claude CLI**, (b) commit/push to **GitHub**,
(c) reach the **Azure stack** (Translator + Doc Intelligence + Speech via
macOS Keychain), and (d) use the **VS Code integration** (open files in
the IDE pane, run tasks, drive the terminal), paste the contents of this
file from the next `---` to end-of-file into the chat box of a new session.

This is a **capability audit + missing-piece report**, not a sync runbook
and not an orchestrator run. It performs:

- Tier 0 read-only probes (filesystem, `git status`, `gh auth status`,
  `az account show`, `security find-generic-password` existence checks,
  `claude --version`, `code --version`)
- One *Tier 1* mechanical action: `git fetch --all --prune` (no working-tree
  mutation, no push)
- **HALTS** before anything that costs money, touches Keychain values,
  triggers `az login`, or installs anything

At the end, Claude responds in the canonical 4-part At-a-glance template
with a concrete list of what (if anything) you need to provide for it to
become fully operational — credentials to enter, commands to authorize,
files to create. If nothing is missing, it says so and gives the one-line
session-opener you should use going forward.

**Companion docs Claude will read once at the top of the session:**
- [`../../CLAUDE.md`](../../CLAUDE.md) — standing brief for the repo
- [`../plan/operators/coordination-protocol.md`](../plan/operators/coordination-protocol.md) — write/push/branch discipline
- [`../plan/operators/setup/machines.md`](../plan/operators/setup/machines.md) — per-machine layout
- [`../plan/operators/setup/azure-stack.md`](../plan/operators/setup/azure-stack.md) — Azure resource + Keychain naming
- [`../plan/operators/setup/recreate-from-scratch.md`](../plan/operators/setup/recreate-from-scratch.md) — blank-Mac procedure (only consulted if a gap is found)

**Authorization model:** auto-mode for the read-only audit; **HALT** before
any state-mutating recovery step (creating `~/.machine-id`, running
installer scripts, `az login`, `gh auth login`, installing Homebrew
packages, writing Keychain values). Each halt produces a one-paragraph ask
with the exact command Claude would run if authorized.

---

You are Claude Code running in a fresh VS Code session on one of Asif's
Macs. Your job is to **audit your own capabilities** across four domains
(Anthropic, GitHub, Azure, VS Code), report the result in the canonical
4-part At-a-glance template, and ask exactly the questions you need
answered for any missing piece — and nothing more.

Read [`CLAUDE.md`](../../CLAUDE.md), [`_workspace/plan/operators/coordination-protocol.md`](../plan/operators/coordination-protocol.md), and [`_workspace/plan/operators/setup/machines.md`](../plan/operators/setup/machines.md) once before you begin. They define this repo's conventions, the response template, and the per-machine layout. If you're already in this repo's working tree, your CWD already gave you `CLAUDE.md` via auto-load — don't re-read it.

Do NOT use the `podcast-orchestrator` agent. Do NOT run `start-session.sh`
yet — that's the next step *after* this audit confirms you're operational.
Do NOT push anything, do NOT create commits, do NOT install anything
without confirmation.

## Step 0 — Identify the machine + working directory

```bash
hostname
whoami
uname -a
pwd
cat ~/.machine-id 2>/dev/null || echo "MISSING"
```

Report the four values plus the machine-id status. If `~/.machine-id` is
missing, **flag it** for Step 9 (the gap-report). Do NOT create it yet —
the slug depends on which physical Mac this is, and the convention is
documented in [`machines.md`](../plan/operators/setup/machines.md).

Also capture the repo root and current branch:

```bash
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git status --porcelain | head -5
```

If `git rev-parse --show-toplevel` fails, you're not inside a git repo —
halt and surface; the rest of the audit assumes you are. If the working
tree is dirty, **note it** (the daily `start-session.sh` requires a clean
tree); do NOT clean it.

## Step 1 — Anthropic capability (Claude CLI + API)

```bash
claude --version            # CLI installed?
claude -p "Reply with exactly the word PONG." 2>&1 | head -5   # auth + roundtrip
```

Expected: `claude --version` prints a version, and the prompt returns
exactly `PONG`. If the CLI is missing, flag for install (`brew install --cask claude-code` per [recreate-from-scratch.md §3](../plan/operators/setup/recreate-from-scratch.md)). If auth fails, flag for `claude login` (interactive — you cannot do this for the operator).

Then check Anthropic *SDK* (Python) reachability, since the pipeline's
cost-ledger uses it:

```bash
python3 -c "import anthropic; print('anthropic SDK', anthropic.__version__)" 2>&1 | head -3
python3 --version   # must be ≥ 3.11; cost-ledger silently fails on 3.10
```

Check for `ANTHROPIC_API_KEY` (used only by the SDK paths, not by `claude`
CLI which uses its own OAuth):

```bash
test -n "${ANTHROPIC_API_KEY:-}" && echo "ANTHROPIC_API_KEY: present (len=${#ANTHROPIC_API_KEY})" || echo "ANTHROPIC_API_KEY: MISSING"
```

Missing key is acceptable **if** the operator only uses the `claude` CLI;
flag it as informational only. Most of the podcast pipeline goes through
`claude -p`, not the raw SDK.

## Step 2 — GitHub capability (git + gh + auth)

```bash
git --version
gh --version
gh auth status 2>&1 | head -10
git config user.name
git config user.email
git remote -v
```

Expected: `gh auth status` shows "Logged in to github.com" with token
scopes including `repo`. The repo's origin should point to
`https://github.com/asifhussain60/podcast-factory.git` (or the SSH form
`git@github.com:asifhussain60/podcast-factory.git`). If origin is the old
`Journal` URL, **flag for `git remote set-url`** — that's the leftover
from the 2026-05-22 split.

Probe push capability without actually pushing:

```bash
git fetch --all --prune          # tier-1 mechanical; no working-tree change
git log --oneline -3 origin/develop
git ls-remote --heads origin | head -5
```

If `git fetch` fails on auth, that's the actionable gap (likely SSH key
missing or HTTPS token expired). Show the failing command + first 5 lines
of stderr verbatim in the gap report.

Check that the post-commit auto-push hook exists (per
[coordination-protocol.md §2](../plan/operators/coordination-protocol.md)):

```bash
ls -la "$(git rev-parse --git-common-dir)/hooks/post-commit" 2>&1 | head -3
test -x "$(git rev-parse --git-common-dir)/hooks/post-commit" && echo "hook: present + executable" || echo "hook: MISSING"
```

If missing, flag it; the hook content is in `recreate-from-scratch.md §5`
and the installer is `scripts/install-git-hooks.sh`.

## Step 3 — Azure capability (CLI + Keychain + connectivity probe)

```bash
az --version 2>&1 | head -3
az account show --query '{name:name, id:id, state:state}' -o table 2>&1 | head -5
```

Expected: `az` shows a version and `account show` lists the
`Journal AI — primary` subscription (or whichever subscription is current)
in `Enabled` state. If `az account show` says "Please run 'az login'", do
**not** run it — flag it; `az login` opens a browser and needs operator
authorization.

Probe Keychain entries for the required secrets (per
[azure-stack.md](../plan/operators/setup/azure-stack.md) — naming convention `azure-<app>-<resource>-<field>`).
Use existence checks only (`-s` without `-w`), never extract the values:

```bash
for k in \
  azure-translator-key \
  azure-translator-region \
  azure-translator-endpoint \
  azure-docintel-key \
  azure-docintel-endpoint \
  azure-speech-key \
  azure-speech-region \
; do
  if security find-generic-password -s "$k" >/dev/null 2>&1; then
    echo "  $k: present"
  else
    echo "  $k: MISSING"
  fi
done
```

Adjust the key list to match what `infra/azure/store-keychain-keys.sh`
actually stores on this repo — read that script first to get the
authoritative list rather than guessing, since names may have shifted.

Finally, the **live connectivity probe** — but only if the `azure-probe`
make target exists AND every Keychain entry above was present:

```bash
test -f Makefile && grep -q "^azure-probe:" Makefile && echo "make azure-probe: available" || echo "make azure-probe: NOT available"
```

Do NOT run `make azure-probe` yet — that's a Tier 1 action that makes a
live Translator round-trip. **Flag it as the recommended next step** if
all credentials are present; let the operator authorize the run.

## Step 4 — VS Code integration

You're inside VS Code's Claude Code extension already (the `ide_selection`
context in your conversation confirms it). Verify the extras:

```bash
which code 2>&1 | head -2          # the `code` CLI launcher
code --version 2>&1 | head -3      # version + commit + arch
```

If `which code` returns nothing, the `code` shell command isn't on PATH.
That's the usual `Cmd+Shift+P → "Shell Command: Install 'code' command in PATH"` fix; flag it. Without `code` on PATH, you can still edit files via your Read/Edit tools, but you can't shell-out `code path/to/file` to pop something open for the operator.

VS Code extensions that this project relies on (Claude Code itself + any
helper extensions the operator has installed) — you can list them only if
`code` is on PATH:

```bash
code --list-extensions 2>&1 | head -20
```

Don't install anything; just enumerate.

## Step 5 — Repo orientation (no mutation)

```bash
test -f CLAUDE.md && echo "CLAUDE.md: present" || echo "CLAUDE.md: MISSING"
test -f _workspace/plan/operators/start-session.sh && echo "start-session.sh: present" || echo "start-session.sh: MISSING"
test -f scripts/install-claude-skills.sh && echo "install-claude-skills.sh: present" || echo "install-claude-skills.sh: MISSING"

# Identify this machine's expected operator file from ~/.machine-id (if set)
MID="$(cat ~/.machine-id 2>/dev/null || echo unknown)"
test -f "_workspace/plan/operators/${MID}.md" && echo "operator file: present (${MID}.md)" || echo "operator file: MISSING for machine-id '${MID}'"

# Have skills been installed for THIS Claude Code session?
ls "$HOME/Library/Application Support/Claude/skills/" 2>/dev/null | head -10 || echo "skills dir: not found"
ls .claude/agents/ 2>/dev/null | head -10 || echo "agents dir: not found"
```

If the skills/agents directories are empty or absent, flag a recommendation
to run `bash scripts/install-claude-skills.sh --dry-run` first, then the
real install — but **do not run it yet**; that's a state change requiring
confirmation.

## Step 6 — Branch + assignment sanity (read-only)

```bash
git show origin/develop:_workspace/plan/operators/index.md 2>&1 | head -40
git show origin/develop:_workspace/plan/book-queue.md 2>&1 | head -40
MID="$(cat ~/.machine-id 2>/dev/null || echo unknown)"
git show "origin/develop:_workspace/plan/operators/${MID}.md" 2>&1 | head -60
```

Note (don't act on) the current in-flight assignment for this machine, the
queue depth, and any HALT-AT-GATE state in `next_action`. This is purely
context for the operator's report — `start-session.sh` is the right tool
to actually switch branches once the audit is green.

## Step 7 — Compute the gap list

Aggregate findings from Steps 0–6 into three buckets:

| Bucket | Meaning | Examples |
|---|---|---|
| **🟢 Green** | works now, no action needed | `claude -p` returned PONG, `gh auth status` ok, all Keychain entries present |
| **🟡 Yellow** | works but with a caveat worth surfacing | python is 3.11 exactly (close to the silent-fail boundary), one optional Keychain entry missing, `code` not on PATH |
| **🔴 Red** | actionable gap — operator must authorize a recovery step | `~/.machine-id` missing, `gh auth status` fails, `az account show` says login required, the post-commit hook is missing |

For each Red, write the **exact command** you would run if authorized. Use
the form `Recovery: <one-line bash>`. Do NOT execute it.

## Step 8 — Respond in the canonical 4-part template

Follow [`_workspace/plan/response-template.md`](../plan/response-template.md) precisely. Shape:

```
## At a glance — <🟢/🟡/🔴> <one-phrase status>
1. <terse one-liner — Anthropic status>
2. <terse one-liner — GitHub status>
3. <terse one-liner — Azure status>
4. <terse one-liner — VS Code + skills status>
5. <terse one-liner — top recommendation>

---

### 1. Anthropic 🤖
<PROSE paragraph — 2-4 sentences — what worked, what didn't, where to look>

### 2. GitHub 🔧
<PROSE paragraph — same shape>

### 3. Azure ☁️
<PROSE paragraph — same shape>

### 4. VS Code + skills 🧩
<PROSE paragraph — same shape>

### 5. Gap list 📋
<numbered list of Red items only, each with the exact Recovery command — no PROSE here, this section legitimately enumerates>

---

## Next: 👤 Asif
<Single-path if the audit is all-green: "Run `bash _workspace/plan/operators/start-session.sh` and tell me what it prints.">
<Multi-path if there are Reds: alphabetized list — A. (Recommended) Authorize the highest-impact recovery / B. Fix a different one first / C. Skip Azure for this session / Do all of the above (A + B + C in sequence)>
```

**Important formatting rules** (from [coordination-protocol.md §13](../plan/operators/coordination-protocol.md)):
- No `**TL;DR:**` opener
- No `## Project Status` block
- No `*Plain English:* / *Impact:* / *Fix:* / *Where:*` literal sub-bullets — those four words are guidance for what to convey, NOT visible markup
- No custom section labels like "Deviation from plan", "Verification", "Coord doc", "What changed"
- Status emoji embedded in the H2 At-a-glance header
- Final `## Next:` is H2 (matches At-a-glance weight, bookends the response)

## Step 9 — What I need from Asif (the return prompt)

If the gap list (Step 7's Red bucket) is non-empty, **also emit a separate
self-contained follow-up prompt block** at the very end of your response,
labeled exactly:

```
---
### Follow-up prompt for the operator to paste back

If you authorize the recovery steps above, paste THIS block back to me as
your next message:

<```bash>
# 1. <first recovery command — only included if Asif explicitly said yes>
# 2. <second>
# ...
<```>

For each command, include:
- The exact one-line bash
- Whether it requires browser interaction (claude login, az login, gh auth login)
- Whether it writes to Keychain (and what name)
- Whether it touches the working tree, the .git/ dir, or the home directory
```

If the gap list is empty (all-green), do NOT emit a follow-up prompt block;
just close on the `## Next: 👤 Asif` line with the `start-session.sh`
single-path Next.

If the audit cannot complete (e.g., not inside a git repo, no shell access,
critical tool missing that blocks even read-only probes), report exactly
what blocked you in the At-a-glance and ask one clarifying question via
AskUserQuestion (one question, recommended option first, "(Recommended)"
label).

## Step 10 — One final discipline rule

You may run **only** the commands listed in Steps 0–6 of this prompt and
the file-reads of the companion docs explicitly named in the preamble.
Do not browse the filesystem looking for more context, do not spawn
sub-agents, do not write any file (operator file, MEMORY.md entry, or
otherwise), do not invoke any other skill. The audit is intentionally
narrow; the operator's `start-session.sh` is the gateway to actual work.

---

**End of prompt.** Paste from the `---` after the preamble through this
line into a fresh Claude Code chat to bootstrap a new session's capability
audit. The audit's output tells you (and Claude) exactly what to do next.
