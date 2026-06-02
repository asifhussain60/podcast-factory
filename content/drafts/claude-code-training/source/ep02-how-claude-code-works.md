# EP02 Source: How Claude Code Actually Works — The Agentic Mental Model

**Series:** Claude Code: From Copilot to Agentic AI  
**Episode:** 2 of 3  
**Target length:** 20 minutes  
**Audience:** Developers currently using GitHub Copilot — they've heard episode 1, they know Copilot well  
**Source type:** Synthesized from official Anthropic documentation  
**Research date:** 2026-06-02

---

## Episode Intent

Episode 1 told listeners *that* Claude Code is different. This episode explains *why* — the mechanics behind the agent model. Building the correct mental model here prevents frustration in episode 3. The Copilot contrast should be used as a recurring anchor: "Copilot does X at the token level; Claude Code does Y at the tool level."

---

## PART 1 — THE AGENTIC LOOP

### What "Agentic" Means Structurally

From official Anthropic documentation:

> "Claude Code is an agentic coding tool that reads your codebase, edits files, runs commands, and integrates with your development tools."

The agent loop is structurally simple. Claude Code runs a `while(tool_call)` loop:
1. Receive a goal (your prompt)
2. Choose a tool to call
3. Execute the tool and get the result
4. Incorporate the result into context
5. Decide whether to call another tool or stop
6. Repeat until the goal is met or a blocker is hit

This is the structural difference from Copilot: **a language model completing text** vs. **an agent executing a plan across multiple tools and multiple steps.**

### Before / After Scenario

**Copilot / autocomplete paradigm:**
You type `function getUserById(` — Copilot suggests the function body based on surrounding code. You accept or reject. One round-trip, one suggestion.

**Claude Code agentic paradigm:**
You type: `"The auth tests are failing. Fix them."`
Claude Code then:
1. Runs `npm test -- --grep auth` (Bash)
2. Reads the error output
3. Reads the failing test file (Read)
4. Reads the implementation being tested (Read)
5. Makes a targeted edit (Edit)
6. Runs the tests again (Bash)
7. Reads the new error if still failing, iterates
8. Stops when tests pass — or surfaces a specific blocker to you

---

## PART 2 — THE TOOL SYSTEM

### Core Built-In Tools

From official documentation, the core built-in tools available to Claude Code:

| Tool | What It Does |
|---|---|
| **Bash** | Universal adapter — runs any shell command |
| **Read** | Reads files from the filesystem |
| **Edit / Write** | Makes targeted edits or creates new files |
| **Grep** | Searches across files by pattern |
| **Glob** | Lists files matching a pattern |
| **Task** | Spawns sub-agents for parallel work |
| **TodoWrite** | Maintains an in-context task checklist |
| **WebFetch** | Fetches content from URLs |
| **ToolSearch** | Discovers MCP tools on demand |

### Write Access Is Scoped

From official security documentation:

> "Claude Code can only write to the folder where it was started and its subfolders — it cannot modify files in parent directories without explicit permission. While Claude Code can read files outside the working directory... write operations are strictly confined to the project scope."

### Read-Only Commands Run Without Prompting

From permissions documentation: a fixed set of read-only commands — including `ls`, `cat`, `echo`, `pwd`, `head`, `tail`, `grep`, `find`, `wc`, `diff`, `stat`, `du`, `cd`, and read-only git forms — **execute without a permission prompt in every mode.** The set is not configurable.

### Multi-Agent: Claude Can Spawn Sub-Agents

The Task tool lets Claude spawn parallel sub-agents. "A lead agent coordinates the work, assigns subtasks, and merges results" — this is how Claude Code handles tasks too large for a single context window, like a 50,000-line migration.

---

## PART 3 — CLAUDE.md AND PERSISTENT MEMORY

### The Session Problem

From official memory documentation:

> "Each Claude Code session begins with a fresh context window. Two mechanisms carry knowledge across sessions: CLAUDE.md files (instructions you write) and auto memory (notes Claude writes itself)."

### What CLAUDE.md Is

A plain markdown file at your project root (`./CLAUDE.md` or `./.claude/CLAUDE.md`). Claude Code **reads it at the start of every session** and loads it into context before your first prompt.

From official docs:

> "`CLAUDE.md` is a markdown file you add to your project root that Claude Code reads at the start of every session. Use it to set coding standards, architecture decisions, preferred libraries, and review checklists."

### Four Scopes of CLAUDE.md

| Scope | Location | Shared? |
|---|---|---|
| Managed policy | `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) | All org users |
| User | `~/.claude/CLAUDE.md` | Just you, all projects |
| Project | `./CLAUDE.md` or `./.claude/CLAUDE.md` | Team (commit to repo) |
| Local | `./CLAUDE.local.md` | Just you, this project only (gitignore) |

Files closer to the working directory take precedence for specificity. All are concatenated, not overriding.

### Auto Memory

Claude Code also has auto-memory: Claude writes notes to `~/.claude/projects/<project>/memory/MEMORY.md` on its own, saving things like build commands, debugging insights, and preferences it discovered. The first 200 lines (or 25KB) load into every session. Editable and deletable at any time.

**Important architecture note:** CLAUDE.md content is "delivered as a user message after the system prompt, not as part of the system prompt itself." It shapes behavior but is not a hard enforcement layer. For enforcement, use Hooks (see Part 5).

### When to Use Each Memory Mechanism

- "Fact Claude should hold every session" → CLAUDE.md
- "Multi-step procedure or on-demand workflow" → Skills (custom slash commands)
- "Something that must run at a specific lifecycle point" → Hooks

---

## PART 4 — SLASH COMMANDS

From official commands reference (`code.claude.com/docs/en/commands`):

> "Commands control Claude Code from inside a session. They provide a quick way to switch models, manage permissions, clear context, run a workflow, and more."

Slash commands are recognized only at the start of a message. Type `/` to see all available commands.

### Key Built-In Commands

| Command | What It Does |
|---|---|
| `/init` | Generate a starter CLAUDE.md by analyzing the codebase |
| `/compact [instructions]` | Summarize conversation to free context window |
| `/clear` | Start a new conversation (keeps project memory) |
| `/plan [description]` | Enter plan-only mode — reads files, no edits |
| `/model [model]` | Switch Claude model mid-session |
| `/permissions` | View and manage tool allow/deny rules |
| `/mcp` | Manage MCP server connections |
| `/memory` | Edit CLAUDE.md files and auto-memory |
| `/hooks` | View configured hooks |
| `/context` | Visualize context window usage |
| `/usage` | Show session cost and plan limits |
| `/sandbox` | Toggle OS-level filesystem/network sandboxing |
| `/code-review [level]` | Review current diff; optionally apply fixes |
| `/batch <instruction>` | Decompose a large change into parallel sub-agents |
| `/resume [session]` | Resume a previous conversation |
| `/rewind` | Roll back code and conversation to a checkpoint |

### Skills vs. Commands

Custom slash commands have been merged into the Skills system. A `SKILL.md` file in `.claude/skills/<name>/` creates a `/<name>` command. **Key design choice:** CLAUDE.md is always-on context (loads every session); skills are on-demand context (load only when invoked). This keeps the context window efficient.

---

## PART 5 — HOOKS: THE ENFORCEMENT LAYER

From official hooks documentation (`code.claude.com/docs/en/hooks`):

> "Hooks are user-defined shell commands, HTTP endpoints, or LLM prompts that execute automatically at specific points in Claude Code's lifecycle. They allow users to inspect events, take action, and optionally return decisions that control behavior."

Where CLAUDE.md says "please do X," a hook says "block unless X." Hooks are the deterministic enforcement layer that CLAUDE.md cannot be.

### Hook Events (35 Total)

**Once per session:** `SessionStart`, `Setup`, `SessionEnd`

**Once per turn:** `UserPromptSubmit`, `UserPromptExpansion`, `Stop`, `StopFailure`

**Every tool call (the agentic loop):**
- `PreToolUse` — fires before a tool executes; can **block** the tool call
- `PermissionRequest` — fires when a permission dialog appears
- `PostToolUse` — fires after a tool succeeds
- `PostToolBatch` — fires after a parallel batch of tool calls

**Async events:** `SubagentStart`, `SubagentStop`, `FileChanged`, `PreCompact`, `PostCompact`, and more

### Five Hook Types

1. `command` — runs a shell command; receives JSON on stdin, responds with JSON
2. `http` — sends an HTTP POST to an endpoint
3. `mcp_tool` — calls a tool on an MCP server
4. `prompt` — runs a single-turn LLM evaluation
5. `agent` — spins up a full sub-agent with tool access

### Hook Decision Control

A `PreToolUse` hook can return:
- `permissionDecision: "allow"` — skip the prompt, proceed
- `permissionDecision: "deny"` — block the tool call with a reason
- `permissionDecision: "ask"` — force a prompt even if the tool was pre-approved
- Exit code 2 → blocking error; stderr is fed back to Claude

**Practical use cases from official documentation:**
- Block any `rm -rf` command before it runs
- Auto-format files after every Edit (PostToolUse on file edits)
- Run lint before every commit (PreToolUse on `git commit`)
- Inject git status into every new session (SessionStart)
- Log every tool call to an audit trail for compliance
- Auto-approve safe read-only commands to reduce prompt fatigue

Hooks are configured in settings files at user scope (`~/.claude/settings.json`), project scope (`.claude/settings.json`), or managed policy, using a matcher that filters by tool name or regex.

---

## PART 6 — MODEL CONTEXT PROTOCOL (MCP)

From the official MCP announcement (Anthropic blog, November 25, 2024):

> "Today, we're open-sourcing the Model Context Protocol (MCP), a new standard for connecting AI assistants to the systems where data lives, including content repositories, business tools, and development environments."

> "a universal, open standard for connecting AI systems with data sources, replacing fragmented integrations with a single protocol."

### What MCP Solves

Without MCP: getting Claude to act on external data means copy-pasting into chat. With MCP:

> "Connect a server when you find yourself copying data into chat from another tool, like an issue tracker or a monitoring dashboard. Once connected, Claude can read and act on that system directly instead of working from what you paste."

**Concrete examples from official docs:**
- "Implement features from issue trackers: 'Add the feature described in JIRA issue ENG-4521 and create a PR on GitHub.'"
- "Analyze monitoring data: 'Check Sentry and Statsig to check the usage of feature ENG-4521.'"
- "Query databases: 'Find emails of 10 random users who used feature ENG-4521, based on our PostgreSQL database.'"
- "Integrate designs: 'Update our standard email template based on the new Figma designs that were posted in Slack.'"

### MCP Scopes

MCP servers can be scoped:
- **Local** — private to you, current project
- **Project** — committed to `.mcp.json`, shared with team
- **User** — all your projects, private

### Tool Search: Solving Context Bloat

From official docs on Tool Search:

> "Tool search keeps MCP context usage low by deferring tool definitions until Claude needs them. Only tool names and server instructions load at session start, so adding more MCP servers has minimal impact on your context window."

From Anthropic engineering: Tool Search produces an **85% reduction in MCP token usage** while maintaining access to the full tool library. Accuracy improvement: "Opus 4 improved from 49% to 74%, and Opus 4.5 improved from 79.5% to 88.1%" on MCP evaluations when Tool Search was enabled.

---

## PART 7 — THE PERMISSIONS MODEL

### Architecture

From official security documentation:

> "Claude Code uses strict read-only permissions by default. When additional actions are needed (editing files, running tests, executing commands), Claude Code requests explicit permission. Users control whether to approve actions once or allow them automatically."

**Critical architectural fact:**

> "Instructions in your prompt or CLAUDE.md shape what Claude tries to do, but they don't change what Claude Code allows. To grant or revoke access, use /permissions, the rules described here, a permission mode, or a PreToolUse hook."

### Permission Rule Syntax

Rules follow `Tool` or `Tool(specifier)` format:
- `Bash(npm run *)` — allow any npm run command
- `Bash(git push *)` in deny list — block all git push
- `WebFetch(domain:github.com)` — allow fetches only to github.com
- `Read(./.env)` — deny reading the .env file
- `mcp__puppeteer__*` — all tools from the puppeteer MCP server

Rules evaluated in order: **deny → ask → allow.** First match wins. Deny always beats allow.

### Six Permission Modes

| Mode | Description |
|---|---|
| `default` | Prompts on first use of each tool |
| `acceptEdits` | Auto-accepts file edits + safe filesystem commands within working directory |
| `plan` | Read-only — Claude explores but cannot edit source files |
| `auto` | Model-based classifiers approve/deny (research preview) |
| `dontAsk` | Auto-denies unless pre-approved |
| `bypassPermissions` | Skips all prompts — only for isolated containers/VMs |

### The Approval Fatigue Problem

From the Anthropic engineering blog on auto mode:

> "Telemetry showed users approved roughly 93% of permission prompts."

A 93% approval rate means most prompts are rubber-stamps. This motivated the auto mode and sandboxing work.

### Sandboxing: The Defense-in-Depth Layer

From the Anthropic engineering blog on sandboxing:

> "In our internal usage, we've found that sandboxing safely reduces permission prompts by 84%."

Sandboxing is built on OS primitives: **macOS seatbelt** and **Linux bubblewrap**.

> "Filesystem isolation ensures that Claude can only access or modify specific directories. This is particularly important in preventing a prompt-injected Claude from modifying sensitive system files."

> "Network isolation ensures that Claude can only connect to approved servers. This prevents a prompt-injected Claude from leaking sensitive information or downloading malware."

These restrictions apply to "any scripts, programs, or subprocesses spawned by the command" — not just Claude Code itself.

---

## PART 8 — COST AND CONTEXT MODEL

### Context Window

Claude Code sessions use Claude's full context window — up to **1 million tokens** on current Sonnet/Opus models. For comparison, GitHub Copilot's context window is 32K–128K tokens.

### Context Compaction

When the context window fills, `/compact` or automatic compaction summarizes the conversation, preserving CLAUDE.md, skills, and key facts. After compaction, CLAUDE.md is re-read from disk and re-injected. Compaction itself is a Claude API call that costs tokens.

From official docs: "Most best practices are based on one constraint: Claude's context window fills up fast, and performance degrades as it fills."

### Token Cost vs. Copilot

Claude Code is **token-billed** for API usage. Every agentic loop iteration — every tool call and its result — goes through the context window. A single "fix the auth tests" request might involve 10–20 tool calls, each contributing to the context.

**The critical framing for Copilot users:** Copilot charges a flat monthly subscription per seat for unlimited completions. Claude Code's agentic loops consume more tokens per "task" — but they also accomplish tasks that would require many back-and-forth completion cycles. The comparison is task completion vs. text prediction, not tokens-for-tokens.

---

## SOURCES

- Claude Code Overview — code.claude.com/docs/en/overview
- Claude Code MCP Docs — code.claude.com/docs/en/mcp
- Claude Code Security — code.claude.com/docs/en/security
- Claude Code Permissions — code.claude.com/docs/en/permissions
- Claude Code Memory / CLAUDE.md — code.claude.com/docs/en/memory
- Claude Code Hooks — code.claude.com/docs/en/hooks
- Claude Code Commands Reference — code.claude.com/docs/en/commands
- Introducing Claude Code — anthropic.com/product/claude-code
- Claude Code Auto Mode — anthropic.com/engineering/claude-code-auto-mode
- Claude Code Sandboxing — anthropic.com/engineering/claude-code-sandboxing
- Introducing MCP — anthropic.com/news/model-context-protocol
- Advanced Tool Use — anthropic.com/engineering/advanced-tool-use
- Framework for Safe and Trustworthy Agents — anthropic.com/news/our-framework-for-developing-safe-and-trustworthy-agents
