# Claude Code capability bootstrap — first-session audit

**Purpose:** when you open a fresh Claude Code session on this Mac and want Claude to confirm — before any real work — that it can (a) call the **Anthropic API + Claude CLI**, (b) commit/push to **GitHub**, (c) reach the **Azure stack** (Translator + Doc Intelligence + Speech via macOS Keychain), and (d) use the **VS Code integration** (open files in the IDE pane, run tasks, drive the terminal) — paste the contents of this file from the next `---` to end-of-file into the chat box of a new session.

This is a **capability audit + missing-piece report**, not a sync runbook and not an orchestrator run. It performs:

- Tier 0 read-only probes (filesystem, `git status`, `gh auth status`, `az account show`, `security find-generic-password` existence checks, `claude --version`, `code --version`)
- One *Tier 1* mechanical action: `git fetch --all --prune` (no working-tree mutation, no push)
- **HALTS** before anything that costs money, touches Keychain values, triggers `az login`, or installs anything

At the end, Claude responds in the canonical 4-part At-a-glance template with a concrete list of what (if anything) you need to provide for it to become fully operational. If nothing is missing, it says so and gives the one-line session-opener you should use going forward.

**Companion docs Claude reads once at the top of the session:**
- [`../../CLAUDE.md`](../../CLAUDE.md) — standing brief for the repo
- [`../../framework.md`](../../framework.md) — pipeline framework spec
- [`../setup/azure-stack.md`](../setup/azure-stack.md) — Azure resources + Keychain naming
- [`../setup/bootstrap.md`](../setup/bootstrap.md) — blank-Mac procedure (only consulted if a gap is found)

**Authorization model:** auto-mode for the read-only audit; **HALT** before any state-mutating recovery step (running installer scripts, `az login`, `gh auth login`, installing Homebrew packages, writing Keychain values). Each halt produces a one-paragraph ask with the exact command Claude would run if authorized.

---

You are Claude Code running in a fresh VS Code session on Asif's Mac. Your job is to **audit your own capabilities** across four domains (Anthropic, GitHub, Azure, VS Code), report the result in the canonical 4-part At-a-glance template, and ask exactly the questions you need answered for any missing piece — and nothing more.

Read [`CLAUDE.md`](../../CLAUDE.md) and [`framework.md`](../../framework.md) once before you begin. They define this repo's conventions, the response template, and the pipeline shape. If you're already in this repo's working tree, your CWD already gave you `CLAUDE.md` via auto-load — don't re-read it.

Do NOT use the `podcast-orchestrator` agent. Do NOT run `start-session.sh` yet — that's the next step *after* this audit confirms you're operational. Do NOT push anything, do NOT create commits, do NOT install anything without confirmation.

## Step 0 — Identify the working directory

```bash
hostname
whoami
uname -a
pwd
```

Capture the repo root and current branch:

```bash
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git status --porcelain | head -5
```

If `git rev-parse --show-toplevel` fails, you're not inside a git repo — halt and surface; the rest of the audit assumes you are. If the working tree has uncommitted changes, **note them** but proceed (the audit itself doesn't mutate state).

## Step 1 — Claude CLI

```bash
claude --version
```

If the command isn't found, **halt** and surface "Claude Code CLI not installed". Don't try to install it — Homebrew install requires sudo on first run and crosses into Tier-2.

## Step 2 — GitHub

```bash
gh --version
gh auth status
git remote -v
git fetch --all --prune    # Tier-1 mechanical
git log --oneline -5
```

If `gh auth status` reports "not logged in", **halt** and surface — that's a `gh auth login` ask. Don't run it automatically.

## Step 3 — Azure stack

```bash
az --version
az account show              # Returns subscription + tenant if logged in
security find-generic-password -s azure-journal-docintel-key1 -w 2>&1 | head -1
security find-generic-password -s azure-journal-translator-key1 -w 2>&1 | head -1
security find-generic-password -s azure-journal-speech-key1 -w 2>&1 | head -1
```

If `az account show` errors with "Please run 'az login'", **halt** and surface — that's the user's call. If any Keychain query returns "The specified item could not be found", note it for the gap report.

When credentials exist, run the connectivity probe:

```bash
python3 scripts/podcast/test_azure_connectivity.py
```

Expect 5 PASS lines (Translator creds + Doc Intel creds + Translator live + Doc Intel reachable + Speech creds). Speech is optional and prints `PASS (skipped)` if not provisioned — that's not a gap.

## Step 4 — VS Code integration

```bash
code --version
echo $TERM_PROGRAM
```

If `code` isn't found, the user can install the `code` shell command from VS Code's command palette ("Shell Command: Install 'code' command in PATH"). Surface as a low-priority gap.

## Step 5 — Optional: pipeline scripts importable

```bash
python3 -c "import sys; sys.path.insert(0,'scripts/podcast'); from _azure import probe; print('podcast scripts importable: OK')"
```

If this fails with `ModuleNotFoundError`, you're not in the repo root — fix `pwd` and retry. Otherwise, surface the import error.

## Step 6 — Report

Respond in the canonical 4-part At-a-glance template (see [`../plan/response-template.md`](../plan/response-template.md)):

**Part 1 (At a glance):** severity emoji + one-phrase status + ~5 punchy summary lines (clickable links for any docs/commands).

**Part 2 (body sections):** one short PROSE section per domain audited (Claude / GitHub / Azure / VS Code / Scripts). Each section names the result and any blocker. No literal `*Plain English:*` / `*Impact:*` / `*Fix:*` / `*Where:*` sub-bullets.

**Part 3 (horizontal rule):** `---`.

**Part 4 (`## Next:`):** if no gaps — name the one-line session-opener (`bash scripts/start-session.sh`). If gaps — list them as alphabetized options with `A. (Recommended) Do all of the below in the order shown (B → C → D)` as the default recommended path.

## What this audit explicitly DOES NOT do

- No `~/.machine-id` check — single-machine repo since 2026-05-23
- No operator-file authoring — that model was retired
- No `~/.coordination-protocol.md` consultation — also retired
- No book-queue claim — pick a book directly from `content/drafts/` listings in `start-session.sh` output

If any of these come up in older docs you cite, treat them as historical references and follow [`CLAUDE.md`](../../CLAUDE.md) instead.
