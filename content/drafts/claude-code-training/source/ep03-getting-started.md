# EP03 Source: Getting Up and Running with Claude Code — Your First Session

**Series:** Claude Code: From Copilot to Agentic AI  
**Episode:** 3 of 3  
**Target length:** 20 minutes  
**Audience:** Developers who have listened to episodes 1 and 2 and are ready to install  
**Source type:** Synthesized from official Anthropic documentation  
**Research date:** 2026-06-02

---

## Episode Intent

This is the hands-on episode. Listeners should finish it able to install, authenticate, and complete a real task in Claude Code. Every section should acknowledge the Copilot user's existing intuitions and redirect them where needed. The ten gotchas section (Part 9) is high-value — these are the exact friction points that will trip up Copilot users in their first week.

---

## PART 1 — PREREQUISITES

From `code.claude.com/docs/en/setup`:

**Operating systems:**
- macOS 13.0 or later
- Windows 10 build 1809+ or Windows Server 2019+
- Ubuntu 20.04+, Debian 10+, Alpine Linux 3.19+

**Hardware:**
- 4 GB+ RAM
- x64 or ARM64 processor

**Shell:**
- Bash, Zsh, PowerShell, or CMD

**Plan requirement:** The free Claude.ai plan does **not** include Claude Code access. Required: Claude Pro, Max, Teams, Enterprise, or a Console (API) account with pre-paid credits.

**Node.js:** Required only for the legacy npm install method. Native installers have no Node.js dependency.

---

## PART 2 — INSTALLATION

From `code.claude.com/docs/en/setup` and `code.claude.com/docs/en/quickstart`:

The recommended installation method is the **native installer** — not npm. npm is the legacy path.

### Recommended (Native Installer)

**macOS, Linux, WSL:**
```bash
curl -fsSL https://claude.ai/install.sh | bash
```

**Windows PowerShell:**
```powershell
irm https://claude.ai/install.ps1 | iex
```

**Windows CMD:**
```batch
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

### Package Managers

**Homebrew (macOS):**
```bash
brew install --cask claude-code         # stable channel
brew install --cask claude-code@latest  # rolling channel
```

**WinGet (Windows):**
```powershell
winget install Anthropic.ClaudeCode
```

**Linux:** Signed apt, dnf, and apk repositories are available.

### VS Code Extension

`Cmd+Shift+X` (Mac) / `Ctrl+Shift+X` (Win/Linux) → search "Claude Code" → Install.
Publisher: `anthropic.claude-code`.
Also installs in Cursor, Windsurf, Kiro.
**The extension includes the CLI** — no separate native install needed.

### Legacy npm (Not Recommended)
```bash
npm install -g @anthropic-ai/claude-code
```
Do NOT use `sudo npm install -g`.

### Post-Install Verification
```bash
claude --version
claude doctor    # detailed health check
```

**Update behavior:** Native installations auto-update in the background. Homebrew and WinGet require manual `brew upgrade` / `winget upgrade`.

**Windows note:** Git for Windows is recommended (optional) for the Bash tool. Without it, Claude Code uses PowerShell. WSL 2 is recommended over WSL 1 for sandboxing support.

---

## PART 3 — AUTHENTICATION

From `code.claude.com/docs/en/authentication` and `code.claude.com/docs/en/setup`:

### First Login

1. Run `claude` in the terminal
2. Claude Code opens a browser window for OAuth authorization
3. If the browser doesn't open, press `c` to copy the login URL
4. In WSL2/SSH/containers: the browser may show a code — paste it at the `Paste code here if prompted` prompt
5. To re-authenticate or switch accounts later: type `/login` inside a running session

### Plans That Grant Claude Code Access
- Claude Pro subscription
- Claude Max subscription
- Claude for Teams
- Claude for Enterprise
- Claude Console (API with pre-paid credits)
- Amazon Bedrock, Google Vertex AI, Microsoft Foundry

### Authentication Precedence (Highest to Lowest)

1. Cloud provider credentials (`CLAUDE_CODE_USE_BEDROCK`, etc.)
2. `ANTHROPIC_AUTH_TOKEN` environment variable
3. `ANTHROPIC_API_KEY` environment variable
4. `apiKeyHelper` script output
5. `CLAUDE_CODE_OAUTH_TOKEN` environment variable
6. Subscription OAuth credentials from `/login` (the default for Pro/Max/Teams/Enterprise)

**Critical gotcha for developers:** If `ANTHROPIC_API_KEY` is set in your environment (common for developers who use the API directly), it takes precedence over your subscription and causes **per-token API charges**. Run `unset ANTHROPIC_API_KEY` to use subscription credentials instead.

### Credential Storage
- macOS: encrypted macOS Keychain
- Linux: `~/.claude/.credentials.json` (mode 0600)
- Windows: `%USERPROFILE%\.claude\.credentials.json`

### CI/CD (Non-Interactive)
```bash
claude setup-token   # generates a one-year OAuth token
export CLAUDE_CODE_OAUTH_TOKEN=your-token
```

---

## PART 4 — VS CODE INTEGRATION

From `code.claude.com/docs/en/vs-code`:

**Requirements:** VS Code 1.98.0 or higher.

**What the extension provides:**
- Native graphical chat panel (not terminal-based by default; can be switched in settings)
- Changes show as side-by-side diffs before accepting
- Plan mode opens the plan as a full markdown document for inline editing
- Auto-accept mode for iterative work
- @-mention files with fuzzy matching
- Selected text in the editor is automatically visible to Claude

**The extension can be docked:** editor toolbar, activity bar, primary sidebar, secondary sidebar, or as a tab.

### Key VS Code Shortcuts

| Command | Shortcut |
|---|---|
| Toggle focus editor/Claude | `Cmd+Esc` / `Ctrl+Esc` |
| Open new conversation tab | `Cmd+Shift+Esc` / `Ctrl+Shift+Esc` |
| Reopen closed session | `Cmd+Shift+T` / `Ctrl+Shift+T` |
| Insert @-mention reference | `Option+K` (Mac) / `Alt+K` (Win/Linux) |

**Permission modes in VS Code:** Click the mode indicator at the bottom of the prompt box to cycle: "Ask before edits" → "Edit automatically" → "Plan mode" → "Auto mode."

**Rewind/checkpoints in VS Code:** Hover over any message to reveal the rewind button. Options: fork conversation, rewind code only, or both.

---

## PART 5 — FIRST SESSION WALKTHROUGH

From `code.claude.com/docs/en/quickstart`:

```bash
cd /path/to/your/project
claude
```

The welcome screen shows session information, recent conversations, and latest updates.

**Official recommended first questions:**
- `what does this project do?`
- `what technologies does this project use?`
- `where is the main entry point?`
- `explain the folder structure`

From official docs: "Claude Code reads your project files as needed. You don't have to manually add context."

**First code change:**
```
add a hello world function to the main file
```
Claude Code will: (1) find the appropriate file, (2) show proposed changes as a diff, (3) ask for approval, (4) make the edit.

---

## PART 6 — DAY-ONE WORKFLOWS

From `code.claude.com/docs/en/common-workflows` and `code.claude.com/docs/en/best-practices`:

### Understanding an Existing Codebase

```
give me an overview of this codebase
explain the main architecture patterns used here
what are the key data models?
how is authentication handled?
find the files that handle user authentication
trace the login process from front-end to database
```

From official best practices: "Use Claude Code for learning and exploration. You can ask Claude the same sorts of questions you would ask another engineer."

**Official workflow — Explore first, then plan, then code:**
1. Enter plan mode → Claude reads files and answers without making changes
2. Ask for a detailed implementation plan
3. Press `Ctrl+G` to open the plan in your text editor for direct editing
4. Switch out of plan mode and let Claude code

### Making Changes

```
add input validation to the user registration form
there's a bug where users can submit empty forms - fix it
refactor the authentication module to use async/await instead of callbacks
```

### Permission Modes — Your Control Dial

From `code.claude.com/docs/en/permission-modes`:

| Mode | What Auto-Approves | Switch |
|---|---|---|
| `default` | Reads only | — |
| `acceptEdits` | Reads + file edits + common filesystem commands | `Shift+Tab` once |
| `plan` | Reads only; proposes plan before editing | `Shift+Tab` twice; or `--permission-mode plan` |
| `auto` | Everything with background classifier | Enable in settings |
| `bypassPermissions` | Everything | Explicit flag only; containers/VMs |

In plan mode, Claude presents its plan and asks how to proceed. Options:
- Approve and start in auto mode
- Approve and accept edits
- Approve and review each edit manually
- Keep planning with feedback
- Press `Ctrl+G` to edit the plan directly in your text editor

---

## PART 7 — UNDOING AND RECOVERY

From `code.claude.com/docs/en/best-practices` and `code.claude.com/docs/en/permission-modes`:

| Action | Result |
|---|---|
| `Esc` | Stop Claude mid-action; context is preserved |
| `Esc + Esc` or `/rewind` | Open rewind menu; restore conversation and/or code to any checkpoint |
| `"Undo that"` | Ask Claude to revert its changes via git |
| `/clear` | Reset context window; use between unrelated tasks |

From official documentation: "Claude automatically snapshots files before each change so a checkpoint can restore them." And: "Checkpoints persist across sessions, so you can close your terminal and still rewind later."

**Important warning from official docs:** "Checkpoints only track changes made by Claude, not external processes. This isn't a replacement for git."

**Git as the safety net** — make git operations conversational:
```
what files have I changed?
commit my changes with a descriptive message
```

---

## PART 8 — CLAUDE.md SETUP

From `code.claude.com/docs/en/memory`:

### Generate It on Day One
```
/init
```
"Run `/init` to generate a starting CLAUDE.md automatically. Claude analyzes your codebase and creates a file with build commands, test instructions, and project conventions it discovers." Refine from there.

### What to Include

| Include | Exclude |
|---|---|
| Bash commands Claude can't guess | Things Claude can figure out by reading code |
| Code style rules that differ from defaults | Standard language conventions |
| Testing instructions and preferred test runners | Long tutorials or API docs (link instead) |
| Branch naming and PR conventions | Information that changes frequently |
| Required environment variables | Self-evident practices like "write clean code" |
| Non-obvious project quirks | File-by-file descriptions of the codebase |

**Size recommendation:** "Target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence."

**Official sample CLAUDE.md:**
```markdown
# Code style
- Use ES modules (import/export) syntax, not CommonJS (require)
- Destructure imports when possible (eg. import { foo } from 'bar')

# Workflow
- Be sure to typecheck when you're done making a series of code changes
- Prefer running single tests, and not the whole test suite, for performance
```

**Include other files with:**
```markdown
See @README.md for project overview and @package.json for available npm commands.
```

**File locations:**
- `~/.claude/CLAUDE.md` — your personal rules for all projects
- `./CLAUDE.md` — project rules, commit to git, shared with team
- `./CLAUDE.local.md` — personal project overrides, gitignored

**Auto memory:** Claude Code v2.1.59+ writes its own notes to `~/.claude/projects/<project>/memory/MEMORY.md`. First 200 lines or 25KB load every session. Manage via `/memory`.

---

## PART 9 — COPILOT USER GOTCHAS

These are the ten friction points Copilot users consistently hit in their first week with Claude Code:

**1. No inline completions.** Claude Code has no inline completion. It does not suggest code as you type. If you expect tab-autocomplete while typing, Claude Code will feel absent. You describe what you want; Claude Code writes it.

**2. Human-in-the-loop defaults.** Claude Code defaults to requesting permission before each file change. Copilot users are accustomed to accepting inline suggestions instantly. Use `acceptEdits` mode (`Shift+Tab`) to reduce friction; review `git diff` afterward.

**3. Terminal-first paradigm.** Claude Code is terminal-first. The VS Code extension is a native panel (not inline), and the strongest experience is the CLI.

**4. No native GitHub workflow integration.** Copilot is deeply embedded in GitHub: PR summaries, reviewer suggestions, commit messages in the web UI. Claude Code interacts with GitHub through standard git commands and the `gh` CLI. No native GitHub PR review from the web UI.

**5. Cost model difference.** Copilot is a flat subscription per seat. Claude Code on Pro/Max includes usage within plan limits. If you hit limits, the session pauses. Claude Code via Console API is pay-per-token with no soft rate limit.

**6. Context window management is your job.** Copilot manages context automatically (small sliding window). With Claude Code, as the context window fills, performance degrades. Use `/clear` between unrelated tasks. Use plan mode to scope exploration. Use sub-agents for large investigations.

**7. CLAUDE.md is your Copilot settings equivalent.** Copilot has no persistent project-level memory. CLAUDE.md is how you give Claude persistent context across sessions — treat it like an onboarding doc for the AI.

**8. Rate limits on subscriptions.** Heavy agentic use on Pro/Max can hit rate limits. The session pauses until limits reset. Console API has no soft rate limit.

**9. Model is always Claude.** Unlike Copilot, which lets you switch to GPT-4o, Gemini, etc., Claude Code only uses Claude models (Sonnet/Haiku/Opus).

**10. Run `/init` immediately.** Copilot needs no per-project setup. With Claude Code, run `/init` at the start of every new project. It auto-generates CLAUDE.md from the codebase. Treat this as your "configure the linter" step.

---

## PART 10 — KEY COMMANDS REFERENCE

### Essential CLI Commands

| Command | What It Does |
|---|---|
| `claude` | Start interactive mode |
| `claude "task"` | Run a one-time task |
| `claude -p "query"` | Run one-off query, then exit |
| `claude -c` | Continue most recent conversation |
| `claude --resume` | Resume a previous conversation (picker) |
| `claude --permission-mode plan` | Start in plan mode |
| `claude doctor` | Check installation health |

### Essential Session Commands

| Command | What It Does |
|---|---|
| `/help` | Show available commands |
| `/clear` | Clear conversation history |
| `/init` | Generate CLAUDE.md for the project |
| `/config` | Open settings GUI |
| `/memory` | Browse / edit CLAUDE.md and auto-memory |
| `/compact` | Compact conversation history |
| `/plan` | Switch to plan mode for current prompt |
| `/rewind` | Open rewind/checkpoint menu |
| `/permissions` | Manage allow/deny rules |
| `/model` | Switch model |
| `/usage` | View context window usage and costs |
| `/login` | Re-authenticate |

### CLI Keyboard Shortcuts

| Key | Action |
|---|---|
| `Shift+Tab` | Cycle permission mode (default → acceptEdits → plan) |
| `Esc` | Stop Claude mid-action |
| `Esc + Esc` | Open rewind menu |
| `Ctrl+G` | Open current plan in text editor |
| `Ctrl+D` / `exit` | Exit Claude Code |
| `↑` | Command history |
| `Ctrl+r` | Searchable prompt history |

---

## PART 11 — CONFIGURATION

From `code.claude.com/docs/en/settings`:

**Settings file locations:**

| Scope | Location | Shared? |
|---|---|---|
| User | `~/.claude/settings.json` | No |
| Project | `.claude/settings.json` | Yes (git) |
| Local | `.claude/settings.local.json` | No (gitignored) |

**Settings precedence:** Managed (highest) → command line → local → project → user (lowest).

**Day-one settings to configure:**
```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "defaultMode": "acceptEdits",
    "allow": ["Bash(npm run lint)", "Bash(npm test)", "Bash(git status)"],
    "deny": ["Read(./.env)"]
  },
  "autoUpdatesChannel": "stable",
  "editorMode": "vim"
}
```

Configure via GUI: `/config` inside Claude Code.

**Custom slash commands:** Put `.md` files in `.claude/commands/` → they become slash commands available via `/commandname`. Commit to git for team sharing. Use `$ARGUMENTS` for parameters.

---

## PART 12 — DAY-ONE CHECKLIST

For a Copilot user completing their first Claude Code session:

1. **Install:** `curl -fsSL https://claude.ai/install.sh | bash` (macOS/Linux) or VS Code extension
2. **Authenticate:** run `claude` → browser login with Claude.ai subscription account
3. **Check for API key conflict:** run `echo $ANTHROPIC_API_KEY`; if set, run `unset ANTHROPIC_API_KEY`
4. **Navigate to your project:** `cd /path/to/project`
5. **Initialize memory:** `/init` → review and refine the generated CLAUDE.md
6. **Explore first:** `give me an overview of this codebase`
7. **Make a small change in plan mode:** `Shift+Tab` twice to enter plan mode, describe a change, review the plan before Claude touches any files
8. **Set acceptEdits for iterative work:** `Shift+Tab` once, then `git diff` to review afterward
9. **Commit CLAUDE.md to git** so your team benefits from the project memory

---

## SOURCES

- Advanced setup — code.claude.com/docs/en/setup
- Quickstart — code.claude.com/docs/en/quickstart
- How Claude remembers your project — code.claude.com/docs/en/memory
- Claude Code Configuration / Settings — code.claude.com/docs/en/settings
- Use Claude Code in VS Code — code.claude.com/docs/en/vs-code
- Authentication — code.claude.com/docs/en/authentication
- Best practices for Claude Code — code.claude.com/docs/en/best-practices
- Common workflows — code.claude.com/docs/en/common-workflows
- Choose a permission mode — code.claude.com/docs/en/permission-modes
- Commands — code.claude.com/docs/en/commands
- Claude Code plan access — support.anthropic.com/en/articles/11145838
