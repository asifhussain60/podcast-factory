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
