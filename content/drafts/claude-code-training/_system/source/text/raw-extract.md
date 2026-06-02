<!-- source: ep01-claude-code-vs-copilot.md -->

# EP01 Source: Claude Code for Copilot Users — Understanding the Shift

**Series:** Claude Code: From Copilot to Agentic AI  
**Episode:** 1 of 3  
**Target length:** 20 minutes  
**Audience:** Developers currently using GitHub Copilot in VSCode  
**Source type:** Synthesized from official Anthropic and GitHub documentation  
**Research date:** 2026-06-02

---

## Episode Intent

This episode answers the question every Copilot user has when they first hear about Claude Code: "Where does this fit in what I already do?" Use the audience's Copilot knowledge as a foundation to build on throughout — not as a foil to argue against. The goal is not to displace Copilot in the listener's workflow; it is to show them what Claude Code adds and where it fits alongside what they already use.

---

## PODCAST FORMAT GUIDANCE

**Episode opening — use this to begin the episode:**
> Welcome to *Claude Code: From Copilot to Agentic AI* — a three-part series for developers who use GitHub Copilot and want to understand where Claude Code fits in. I'm joined today by a senior developer who has been using Copilot daily for years and wants honest answers, not a sales pitch. In this first episode, we're covering what Claude Code actually is, how it compares architecturally to what you already use, and — spoiler — why the comparison ends in a more interesting place than you might expect.

**Format:** Teacher-student dialogue, approximately 20 minutes.

**Teacher (male voice):** An experienced Claude Code practitioner who has made the Copilot-to-Claude-Code transition himself. He explains through concrete scenarios and never talks down. He understands Copilot well enough to respect what it does — he is not dismissive of it.

**Student (female voice):** A senior software developer with two or more years of daily Copilot use. Her questions come from expertise, not ignorance. Her core stance is: "I use Copilot every day and it works well. I want to understand what Claude Code adds to my workflow — not replace what I have, but understand what I might be missing." She knows Copilot's agent mode exists. She knows Copilot now supports Claude models. She is asking from a position of competence, not frustration with her current tools. She is not hostile — she is genuinely curious but precise. She will ask pointed questions because she wants accurate answers, not because she needs to be won over.

**Narrative arc for this episode:** Start from Copilot fluency as shared ground, build through the architectural difference (what the tools are actually designed to do), and land on the genuine insight that reframes everything — these tools are not rivals. They are complementary, and sophisticated teams already use both.

**Student question hooks — plant these throughout:**
- "Copilot also does multi-file edits now with agent mode. So what's the actual architectural difference?"
- "I work entirely in VS Code. If Claude Code is terminal-first, is this even practical for my workflow?"
- "No inline completions — how does that change how I write code day to day? That's a real shift."
- "If I wanted to run both, does that actually make sense or does it get confusing fast?"
- [Episode insight question] "Wait — if GitHub's own cloud agent runs on the Claude Agent SDK, and I can already use Claude models inside Copilot — what am I actually choosing between?"

**The insight moment (end of episode):** The episode builds a clear picture of what each tool is designed to do. Then the student asks the natural question: given that Copilot's cloud agent runs on the Claude Agent SDK, and Copilot Business users can already select Claude as their model — where does that leave the comparison? The teacher's answer: the tools were never rivals. Inline completion and agentic task execution are different jobs. Understanding that is the actual takeaway. This should land as clarity, not surprise — the logical conclusion of everything the episode has explained.

**Tone note:** The teacher and student share a foundation — they both understand Copilot well and respect what it does. The teacher's job is to build accurately on that foundation, not to argue against it. Every Copilot strength gets acknowledged before the architectural difference is introduced.

---

## PART 1 — WHAT EACH TOOL ACTUALLY IS

### Claude Code (Official Definition)

From `code.claude.com` (official Anthropic documentation):

> "Claude Code is an agentic coding tool that reads your codebase, edits files, runs commands, and integrates with your development tools. Available in your terminal, IDE, desktop app, and browser."

From `anthropic.com/product/claude-code`:

> "Claude Code is an agentic coding system that reads your codebase, makes changes across files, runs tests, and delivers committed code."

The key architectural facts:
- Operates at the **project level** — reads entire codebases, plans across multiple files, executes changes
- Default safety posture: asks before making changes to files or running commands (configurable)
- Primary interface: terminal CLI (`claude` command) with an official VS Code extension on top
- Follows Unix philosophy — composable, pipeable (`tail -200 app.log | claude -p "..."`)
- Can run in CI/CD (GitHub Actions, GitLab CI/CD)
- Supports parallel sub-agents: "a lead agent coordinates and assigns subtasks"
- Checkpoint/rewind: "automatically saves your code state before each change"
- Uses Model Context Protocol (MCP) to connect to external tools (Jira, Slack, GitHub, databases)

### GitHub Copilot (Official Definition)

From `docs.github.com`:

> "GitHub Copilot transforms the developer experience by providing contextualized assistance throughout the software development lifecycle."

GitHub calls Copilot an **"AI pair programmer"** and a **"suite of features"** in three categories: assistive features, agentic features, and customization features.

**The three distinct Copilot surfaces:**

1. **Inline suggestions (autocomplete):** "Autocomplete-style suggestions from Copilot in supported IDEs." Surrounding code is combined with contextual information from open tabs and sent to a language model. Suggestions appear as "ghost text" and are only added when the user explicitly accepts them.

2. **Copilot Chat:** "A chat interface that lets you ask coding-related questions." Three modes: Ask (questions), Plan (proposes before executing), Agent (multi-file autonomous changes within the IDE).

3. **Copilot cloud agent:** Operates "autonomously in a GitHub Actions-powered environment." Hard limit: 59 minutes per session. Only works on "repositories hosted on GitHub."

---

## PART 2 — THE MENTAL MODEL SHIFT (TEACH THIS BEFORE THE COMPARISON TABLES)

This section should come before the feature tables. Without this frame, the tables read as a spec sheet. With it, every row makes sense.

### From Autocomplete to Agentic

**Copilot's mental model:** You write code; Copilot *suggests* the next tokens. You remain the author at all times; the AI is the passenger. The interaction rhythm is per-keystroke. You never leave your editor. Your Copilot subscription charges a flat monthly rate regardless of how much you use it.

**Claude Code's mental model:** You describe a *goal*; Claude Code plans and executes toward that goal across multiple files and multiple tool calls. Claude Code is the implementer on well-scoped tasks; you are the reviewer of outcomes. The interaction rhythm is per-task, not per-keystroke — tasks take minutes to hours. You review *results*, not *suggestions*.

From Anthropic's official documentation: "The developer sets the objective... Claude Code operates at the project level, reads the full codebase, plans an approach across multiple files, executes changes, runs tests, and iterates on failures."

**The thing to say plainly to the student here:** Claude Code has no inline completion. It does not suggest code as you type. This is a deliberate architectural choice — not an oversight, not a feature gap. If the student only wants faster autocomplete, Claude Code is the wrong tool. The teacher should say this without flinching, because it's honest and it earns trust for everything else.

### Enterprise Evidence (Official Anthropic Case Studies)

These are Anthropic-published, named-enterprise case studies — not hypothetical benchmarks:
- **Stripe:** 10,000-line Scala-to-Java migration in 4 days
- **Ramp:** 80% reduction in incident investigation time
- **Wiz:** 50,000-line Python-to-Go migration in approximately 20 hours
- **Rakuten:** Feature delivery time reduced from 24 to 5 working days

These tasks require understanding the full codebase, planning across many files, running tests, and iterating on failures — the agentic loop that Claude Code is designed around. They are not the kind of work that inline completion was designed to handle, which is why they illustrate the architectural difference cleanly.

### When Each Tool Fits

**Claude Code is architecturally stronger for:**
- Large-scale refactoring across many files
- Migration projects (language, framework, database)
- Writing tests for untested codebases (runs tests, fixes failures, iterates)
- Debugging across services (reads logs, traces call chains)
- Automating development workflows in CI/CD
- Tasks where you want to set a goal and review the outcome rather than guide every step

**GitHub Copilot is architecturally stronger for:**
- Real-time inline completion while actively writing code
- Quick in-editor code explanations and fixes
- PR summaries, code review, and GitHub-native workflows
- Teams needing multi-model flexibility (GPT-4o, Gemini, Claude all available)
- Organizations with existing GitHub Enterprise infrastructure

---

## PART 3 — THE ARCHITECTURAL DIFFERENCE

### Suggest vs. Execute

| Dimension | GitHub Copilot (inline) | Claude Code |
|---|---|---|
| Primary model | Suggest → developer accepts/rejects | Plan → execute → iterate autonomously |
| Context scope | Open tabs + cursor (32k–128k tokens) | Entire codebase (up to 1M tokens) |
| File access | Read-only surrounding context | Read + write (permission required by default) |
| Command execution | Copilot agent mode only, user-approved | Native bash; runs commands autonomously |
| Lives in | IDE (VSCode, JetBrains, etc.) | Terminal + optional VS Code extension |
| Interaction model | Reactive (waits for cursor/keypress) | Goal-directed (works toward completion) |

### Copilot Agent Mode: What Changed in 2025

GitHub's agent mode was announced **February 6, 2025** and released in VS Code v1.99 (March 2025):

> "developers can generate, refactor and deploy code across the files of any organization's codebase with a single prompt command."

Agent mode "enables Copilot to iterate on its own output as well as the results of that output to complete a user's entire request at once."

**Key limitation:** Terminal commands are *suggested* to the user for approval, not fully autonomously executed. The cloud agent has a hard 59-minute cap per session.

### Claude Code's Agentic Model

- **Sub-agents:** Claude can spawn parallel agents (Task tool) to work on different parts simultaneously
- **Hooks:** Automatically trigger actions at lifecycle points (run tests after every file edit, block `rm -rf`, etc.)
- **Routines:** Run on Anthropic-managed infrastructure on a schedule, even when your computer is off
- **Checkpoint system:** Rewind to any previous state (code or conversation)
- **MCP:** Connect to 300+ external tools via open protocol

---

## PART 3 — VS CODE INTEGRATION

### Claude Code in VS Code

From `code.claude.com/docs/en/vs-code`:

> "The VS Code extension provides a native graphical interface for Claude Code, integrated directly into your IDE. This is the recommended way to use Claude Code in VS Code."

What the extension adds over terminal-only:
- Side-by-side inline diffs (review before accepting)
- @-mention files with specific line ranges
- Plan mode (Claude proposes plan, user approves before any changes)
- Conversation history with session search
- Multiple concurrent Claude conversations in separate tabs
- Checkpoint/rewind UI
- `@terminal:name` references to bring terminal output into context

**Architectural difference:** Copilot is built *into* the IDE as a first-class extension, tightly coupled with editor events (cursor movement, keypress, file save). Claude Code's VS Code extension is a *graphical wrapper* on the CLI — same underlying engine and capabilities, with VS Code UI layered on top.

The official VS Code extension (`anthropic.claude-code`) has over 2 million installs as of 2026.

---

## PART 4 — CAPABILITY COMPARISON

| Capability | Claude Code | GitHub Copilot |
|---|---|---|
| Inline autocomplete while typing | **No** | **Yes** (core feature) |
| Chat / Q&A about code | Yes | Yes |
| Multi-file edits | Yes (autonomous) | Yes (agent mode / plan mode) |
| Execute terminal commands | Yes (with permission by default) | Agent mode only (suggested, not fully autonomous) |
| Run tests autonomously | Yes | Agent mode (user-approved) |
| Create commits / PRs | Yes (native git integration) | Yes (deep GitHub integration) |
| CI/CD integration | Yes (GitHub Actions, GitLab) | Yes (native GitHub Actions) |
| Codebase context | Up to 1M tokens | 32k–128k tokens |
| Model choice | Claude only | Claude, GPT-4o, Gemini, xAI Grok, Codex |
| Works outside GitHub repos | Yes (any local repo, any git host) | Inline yes; cloud agent only on GitHub-hosted repos |
| Parallel agent teams | Yes (sub-agents) | Specialized agents (Explore, Task, Review, Plan) |
| MCP tool integrations | Yes (300+ servers) | Yes (MCP support added) |
| PR / issue summarization | Via git + `gh` commands | Native (PR summary, review, issue assignment) |

---

## PART 5 — PRICING

### Claude Code (as of June 2026, source: `claude.com/pricing`)

| Plan | Monthly Cost | Claude Code Access |
|---|---|---|
| Free | $0 | **No** |
| Pro | $20/month ($17 annual) | **Yes** |
| Max 5x | $100/month | Yes |
| Max 20x | $200/month | Yes |
| Team (standard seat) | $25/month ($20 annual) | Yes |
| Team (premium seat) | $125/month ($100 annual) | Yes |

When subscription limits are exhausted, users can continue at standard API token rates (requires explicit opt-in to billing).

Usage limits are **shared** across Claude web, mobile, and Claude Code — all activity counts against the same pool.

### GitHub Copilot (as of June 2026, source: `docs.github.com/en/copilot`)

| Plan | Monthly Cost | Notes |
|---|---|---|
| Free | $0 | 2,000 completions/month; limited chat/agent |
| Pro | $10/month | Unlimited completions; 1,500 AI credits/month |
| Pro+ | $39/month | Premium models; 7,000 AI credits/month |
| Business | $19/seat/month | Org management, policy controls |
| Enterprise | $39/seat/month | Priority models; larger credits pool |

Note: GitHub migrated to **usage-based billing** with "GitHub AI Credits" on June 1, 2026. Agent mode and code review consume credits.

---

## PART 7 — WHERE THIS LEAVES YOU: COMPLEMENTARY TOOLS

**[This is the episode's landing point. The student now understands what each tool is designed to do. The teacher's job here is to make the practical conclusion explicit: these tools serve different jobs, and understanding that removes the either/or framing entirely.]**

**GitHub's Copilot cloud agent is built on the Claude Agent SDK.** From `docs.github.com/en/copilot/concepts/agents/anthropic-claude`: GitHub's cloud agent "leverages the Claude Agent SDK." As of February 2026, GitHub Copilot Business and Pro users can select Anthropic Claude (Opus 4.5/4.6, Sonnet 4.5/4.6) as their coding model within GitHub Copilot under their existing subscription.

This is not a footnote — it's the clearest expression of what these tools actually are relative to each other. They share underlying infrastructure. The question was never "which one" — it was always "which job."

**Claude Code has no inline autocomplete.** This is a deliberate architectural choice, not a gap. Developers who need real-time inline completion while writing and agentic task execution for larger work use both tools. That is the mainstream pattern at engineering teams that have adopted Claude Code.

---

## PART 8 — USING BOTH TOGETHER

**[This section is the practical bridge. After explaining the architectural difference, give the listener a concrete picture of what a dual-tool workflow looks like. This is the most useful thing the episode can leave them with.]**

The "better together" workflow is straightforward once you understand the architectural difference:

**Copilot continues to handle:**
- Real-time inline completion while actively writing code
- Quick in-editor explanations and fixes
- PR summaries, code review, and GitHub-native workflows
- Model flexibility when you want GPT-4o or Gemini for a specific task

**Claude Code handles:**
- Tasks you describe as a goal: "fix the failing auth tests," "migrate this module to async/await," "write tests for the payment service"
- Work that spans multiple files and requires planning before touching code
- Automation in CI/CD — running in GitHub Actions without you present
- Large-scale changes where you want to review outcomes, not guide every step

**In practice:** A developer using both keeps Copilot active in VS Code for the writing experience, and opens Claude Code in a terminal (or the VS Code panel) when they have a well-scoped task to hand off. The two sessions are independent — they don't interfere with each other.

**The transition question this series is answering** is not "should I switch" — it is "how do I learn to use this second tool well, given what I already know from Copilot." Episodes 2 and 3 answer that question directly.

---

## SOURCES

- Claude Code Overview — code.claude.com/docs/en/overview
- Claude Code VS Code extension — code.claude.com/docs/en/vs-code
- Claude Code product page — anthropic.com/product/claude-code
- Claude pricing — claude.com/pricing
- Claude Code plan access — support.claude.com
- GitHub Copilot features — docs.github.com/en/copilot/get-started/features
- GitHub Copilot plans — docs.github.com/en/copilot/get-started/plans
- Copilot inline suggestions — docs.github.com/en/copilot/responsible-use/copilot-code-completion
- Copilot Chat in IDE — docs.github.com/en/copilot/using-github-copilot/copilot-chat/asking-github-copilot-questions-in-your-ide
- Copilot cloud agent — docs.github.com/copilot/concepts/agents/coding-agent/about-coding-agent
- Anthropic Claude in GitHub Copilot — docs.github.com/en/copilot/concepts/agents/anthropic-claude
- Copilot agent mode press release — github.com/newsroom/press-releases/agent-mode
- Claude and Codex in Copilot — github.blog/changelog/2026-02-26


<!-- source: ep02-how-claude-code-works.md -->

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

## PODCAST FORMAT GUIDANCE

**Episode opening — use this to begin the episode:**
> Welcome back to *Claude Code: From Copilot to Agentic AI*. In episode one we covered what Claude Code is and where it fits alongside Copilot. This episode goes one level deeper: how does it actually work? We're going to walk through the agentic loop, the tools that power it, how Claude Code remembers your project across sessions, and how you enforce rules that go beyond just asking nicely. By the end of this episode, you'll have the mental model you need to use Claude Code deliberately — not just experimentally.

**Format:** Teacher-student dialogue, approximately 20 minutes.

**Teacher (male voice):** Builds the agentic mental model from scratch, using concrete tool-by-tool explanations. His job this episode is to give the student an accurate working model — not "Claude Code is like Copilot but more," but something genuinely useful for understanding how to use it well.

**Student (female voice):** She's listened to Episode 1. She understands the architectural difference conceptually. Now she wants the mechanics — how does it actually do what it does? Her questions this episode are "how does that actually work?", "what's the closest Copilot analogy for this?" and, at key moments, "so this is genuinely new territory — how do developers handle it?" She is engaged and building understanding actively, not being converted.

**Narrative arc:** Start with the agentic loop (the engine), build through the tools that power it, arrive at CLAUDE.md as persistent memory, Hooks as the enforcement layer, and MCP as extensibility. End with the practical picture of what it costs to run and how to keep it manageable.

**Student question hooks — plant these throughout:**
- "So every time it reads a file, that costs tokens? How does that scale compared to Copilot's context window?"
- "When you say it can run tests autonomously — what stops it from running in a loop indefinitely?"
- "Copilot just works without any per-project setup. Why do I need CLAUDE.md? What's the tradeoff?"
- "Hooks sound like real configuration work. Is this something most developers set up, or is it advanced?"
- "Copilot also supports MCP now — is MCP still a meaningful differentiator for Claude Code?"

**Where Claude Code has no direct Copilot analogy — frame these as "new capabilities to learn," not gaps in Copilot:**
- CLAUDE.md: Copilot has no persistent project-level memory that travels across sessions. This is something to set up and maintain — it is effort, but it is also the reason Claude Code behaves consistently on your project over time.
- Hooks: Copilot has no lifecycle enforcement layer. Hooks are genuinely new — they let you hard-block actions regardless of what the prompt says, which CLAUDE.md cannot do.
- Sub-agents (Task tool): Copilot has specialized agents but no user-defined parallel sub-agent spawning within a task. This is advanced capability; don't oversell it for day-one use.

**Tone note:** The student is honest about the learning curve and the teacher should be too. When something requires effort — Hooks configuration, CLAUDE.md maintenance, context window discipline — acknowledge it plainly and explain why it is worth the effort. Do not oversell. The student will trust the teacher more for being accurate about costs than for downplaying them.

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

### Multi-Agent: Claude Can Spawn Sub-Agents (What Claude Code Adds: Parallelism at Scale)

The Task tool lets Claude spawn parallel sub-agents. "A lead agent coordinates the work, assigns subtasks, and merges results" — this is how Claude Code handles tasks too large for a single context window, like a 50,000-line migration. This is advanced capability; the teacher should introduce it as a ceiling of what's possible, not a day-one feature to configure.

---

## PART 3 — CLAUDE.md AND PERSISTENT MEMORY (WHAT CLAUDE CODE ADDS: SESSION CONTINUITY)

**[This is a clean teaching moment. The student will ask "why do I need this when Copilot just works?" The honest answer: Copilot's short context window means it has never carried project knowledge across sessions — it works from what's in your open tabs. Claude Code has a 1M-token context window and is explicitly designed to operate across your entire codebase — which means the responsibility of carrying your project conventions falls to you. CLAUDE.md is how you do that. Frame it as the natural consequence of having a bigger, more capable context: more power, more responsibility to direct it well.]**

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

## PART 5 — HOOKS: THE ENFORCEMENT LAYER (WHAT CLAUDE CODE ADDS: DETERMINISTIC CONTROL)

**[This section introduces something genuinely new — not a gap in Copilot, but a capability class that doesn't exist in the inline completion model at all. The distinction to land clearly: CLAUDE.md is instruction — "please don't do X." A Hook is enforcement — "block any command matching X, regardless of what the prompt says." These are different in kind, not degree. The teacher should make this concrete with an example before going into the technical details. Something like: "If you want Claude to never run git push on a certain branch, CLAUDE.md is a reminder. A Hook is a lock."]**

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


<!-- source: ep03-getting-started.md -->

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

## PODCAST FORMAT GUIDANCE

**Episode opening — use this to begin the episode:**
> Welcome to the final episode of *Claude Code: From Copilot to Agentic AI*. In episodes one and two we covered what Claude Code is, where it fits alongside Copilot, and how its core mechanics work. This episode is the practical one. We're going to walk through installation, authentication, your first real session, and the ten things that will trip you up in your first week if nobody warns you. By the end, you'll have an action plan you can follow today.

**Format:** Teacher-student dialogue, approximately 20 minutes.

**Teacher (male voice):** In practical mode. This episode is a walkthrough. He's guided many Copilot users through the first session and knows exactly where the friction points are. He anticipates them before the student hits them — and when she does hit one, he validates it rather than dismissing it.

**Student (female voice):** She's ready to try it. She has the mental model from Episodes 1 and 2 and wants to go from understanding to doing. Her questions this episode are practical: "what do I do first?", "what's going to feel strange coming from Copilot?", "what should I set up before I start on a real task?" Her energy is forward-moving — she is ready, not impatient.

**Narrative arc:** Install → authenticate (with the API key gotcha) → first session → CLAUDE.md setup → the ten gotchas (this is where the episode earns its value). End with the day-one checklist as the student's concrete action plan.

**Student question hooks — plant these throughout:**
- "Do I need to uninstall Copilot first, or can they run at the same time?"
- "I have ANTHROPIC_API_KEY set in my environment from another project — does that cause any issues?"
- "I opened it and I'm looking at a terminal prompt. Where do I start? There are no suggestions appearing."
- "It asked me for permission to edit a file. Copilot just edits automatically — is this normal behavior?"
- "How do I know if the context window is getting full? Does it warn me before performance drops?"

**The day-one checklist at the end should feel like the student's action plan** — the teacher walking her out the door with exactly what she needs to succeed in her first real session.

**Tone note:** This episode's energy is practical and forward-looking. When the gotchas come up, the teacher validates each one as real friction — he does not dismiss or minimize. The student's Copilot intuitions are often correct for Copilot; the teacher's job is to redirect them accurately for Claude Code, not to make her feel wrong for having them.

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

**4. GitHub workflows use standard git and gh CLI, not native Copilot integrations.** Copilot is deeply embedded in GitHub's web UI — PR summaries, reviewer suggestions, commit messages all happen inside GitHub. Claude Code does the same things through standard git commands and the `gh` CLI. If you already know git and gh, the translation is direct: "summarize these changes" becomes a prompt, "create a PR" becomes a `gh pr create` call that Claude Code can make on your behalf. The experience is terminal-first rather than web-native, but the underlying capability is equivalent for most workflows.

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
