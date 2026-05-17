---
name: tell-me
description: "Transcript-informed context challenger and response drafter. ALWAYS invoke this skill when the user says 'tell me', 'brief me', 'what do we know about', 'draft response', 'prepare reply', 'fact-check this', 'context check', 'challenge this', or pastes a screenshot, URL, file path, or teammate question they need to respond to. Also trigger when the user shares a Teams message, PR link, GitHub issue, diagram, or any input where they need to appear fully briefed. This skill reads ALL transcript evidence, master synthesis, knowledge YAMLs, and four repos before drafting — it never asks questions already answered in the evidence. Use this skill even if the user just says 'someone asked me about X' or 'how should I respond to this'."
---

# /tell-me — Transcript-Informed Context Challenger

> **Purpose:** Make Asif appear fully briefed on every ADLC topic by reading all transcript evidence, documentation, and live repo state before drafting any response.
>
> **Core guarantee:** Never ask a question that's already been answered in the transcripts, synthesis, knowledge YAMLs, or repos. If something is settled, state it as a fact. If something is genuinely open, flag the OQ number and suggest a position to take.

---

## CORTEX Bootstrap (Execute on Every Invocation)

**Repo paths (all read-only):**
- `adlc-asif`: current repo (transcripts, synthesis, knowledge YAMLs, library artifacts)
- `adlc-copilot`: `C:\GitRepo\HQY01\adlc-copilot` (production code, agents, skills)
- `adlc-process-documentation`: `C:\GitRepo\HQY01\adlc-process-documentation` (canonical ADLC process definitions)
- `purple-platform-copilot`: `C:\GitRepo\HQY01\purple-platform-copilot` (cross-platform patterns)

**On invocation, load these evidence sources before acting:**
1. `library/synthesis/adlc-master-synthesis.md` — project-level source of truth
2. `library/synthesis/adlc-meeting-log.yaml` — structured metadata for all transcript sources
3. Relevant `knowledge/yaml/*.yaml` files based on the topic detected in Stage 1

---

## How This Skill Works

When Asif receives a message, question, screenshot, PR link, or diagram from a teammate and needs to respond intelligently, this skill harvests all available evidence first, builds an internal brief, then drafts a paste-ready reply.

**Two-phase output (always):**

1. **Internal Brief** — What the evidence says, with sources. Settled items shown as facts. Open items flagged with OQ numbers plus a recommended position with reasoning.
2. **Draft Reply** — A ready-to-paste message in Asif's voice. Contextually dense, references specific decisions, never asks questions the project already answered.

---

## Input Types

This skill accepts any combination of these inputs in a single request:

| Input | How to handle |
|-------|---------------|
| **Screenshot** (Teams message, diagram, PR, board) | Extract visible text, names, and context. Identify who said what. |
| **URL** (GitHub issue, PR, doc) | If GitHub: use `gh` CLI to pull live state. Otherwise: read the URL content. |
| **File path** | Read the file directly. |
| **Plain text question** | Someone asked Asif something — treat as the topic to brief on. |
| **Pasted message** | A teammate's message Asif needs to respond to. |

---

## Seven-Stage Pipeline

The `tell-me` agent executes these stages in order. The skill's job is to ensure every stage runs — the agent does the actual work.

### Stage 1 — Input Parse

Detect what the operator provided:
- Screenshot → extract all visible text, speaker names, timestamps, and topic keywords
- URL → fetch content (use `gh` CLI for GitHub URLs: `gh issue view`, `gh pr view`, `gh api`)
- File path → read the file
- Plain text → extract the core question or topic

Produce a **Topic Summary**: one sentence describing what needs to be briefed on and who asked.

### Stage 2 — Evidence Harvest

Read these sources in order (stop reading a source once you have what you need for the topic — don't read everything every time):

**Priority 1 — Synthesis layer (start here, covers most topics):**
- `library/synthesis/adlc-master-synthesis.md` — project-level source of truth
- `library/synthesis/adlc-meeting-log.yaml` — structured metadata for all 16+ transcript sources

**Priority 2 — Story state (if topic maps to a specific issue/story):**
- `knowledge/yaml/stories/*.yaml` — per-story canonical state with decisions, ACs, open questions

**Priority 3 — Knowledge YAMLs (if topic touches process, governance, architecture):**
- `knowledge/yaml/adlc-governance-gates.yaml`
- `knowledge/yaml/adlc-workflow-phases.yaml`
- `knowledge/yaml/adlc-agent-taxonomy.yaml`
- `knowledge/yaml/adlc-pipeline-labels.yaml`
- `knowledge/yaml/adlc-security-model.yaml`
- `knowledge/yaml/adlc-glossary.yaml`
- `knowledge/yaml/adlc-program-status.yaml`
- `knowledge/yaml/adlc-qe-assembly-line.yaml`
- (read others as needed based on topic)

**Priority 4 — Raw transcripts (only if synthesis doesn't have enough detail):**
- `_workspaces/transcript-of-adlc-innerloop.md`
- Any other transcript files in `_workspaces/`

**Priority 5 — Library artifacts (for deep-dive topics):**
- `library/analyses/*` — technical analyses
- `library/git-comments/*` — issue specs and comment threads
- `library/decisions/*` — ADRs
- `library/plans/*` — implementation plans

### Stage 3 — Repo Scan

Search across all four repos for context matching the topic. All repos are **read-only**.

| Repo | Path | What to search |
|------|------|---------------|
| `adlc-asif` | Current repo | Agents, skills, knowledge YAMLs, library artifacts |
| `adlc-copilot` | `C:\GitRepo\HQY01\adlc-copilot` | Production code, agents, skills — verify what actually exists vs. what's planned |
| `adlc-process-documentation` | `C:\GitRepo\HQY01\adlc-process-documentation` | Canonical ADLC process definitions — verify process claims |
| `purple-platform-copilot` | `C:\GitRepo\HQY01\purple-platform-copilot` | Cross-platform patterns — verify architectural claims |

**Live GitHub access** (when topic references issues or PRs):
```bash
gh issue view {number} --repo HQY01/adlc-project --json title,body,state,labels,comments
gh pr view {number} --repo HQY01/adlc-copilot --json title,body,state,files,reviews,comments
```

### Stage 4 — Settled vs. Open Classification

For every relevant fact discovered in Stages 2-3, classify it:

| Classification | Criteria | How to use in output |
|----------------|----------|---------------------|
| **SETTLED** | Explicitly decided in a transcript, recorded in master synthesis as "Final", or implemented in code | State it as a fact. Never ask about it. |
| **OPEN** | Listed as an OQ in master synthesis, or no decision recorded anywhere | Flag the OQ number. Suggest a position based on evidence leaning. |
| **STALE** | Recorded as decided but contradicted by current repo state | Flag the contradiction. Recommend which source to trust. |

The goal: Asif's reply demonstrates that he knows what's been decided and only raises things that are genuinely unresolved.

### Stage 5 — Challenger Gate

Before producing any output, validate every claim the brief or reply would make:

| Check | Pass | Fail |
|-------|------|------|
| Claim has a source (transcript, YAML, repo, GitHub) | Include with source citation | Remove the claim or flag as assumption |
| Question being asked in draft | Verify it's NOT answered in any evidence source | Replace with a statement showing we already know the answer |
| Technical claim (e.g., "this agent exists", "this label is defined") | Verify in the actual repo — grep for it | Remove or correct |
| Attribution (e.g., "Nathan said X") | Verify in transcript or synthesis source concordance | Remove attribution or soften to "the team discussed" |

This is the most important stage. It's what prevents Asif from looking uninformed or asking redundant questions.

### Stage 6 — Internal Brief

Deliver to Asif (not for posting — this is for his eyes only):

```
## Brief: [Topic]

**What's settled:**
- [Fact 1] — Source: [transcript/YAML/repo]
- [Fact 2] — Source: [transcript/YAML/repo]

**What's open:**
- [OQ-N] [Question] — Evidence leans toward [position] because [reasoning]
- [OQ-N] [Question] — No clear signal; recommend [position] because [reasoning]

**What's changed since last synthesis:**
- [Any new info from live GitHub or repo scan not yet in synthesis]
```

Keep it tight — no more than 10 bullet points total. The brief exists so Asif can verify the evidence before posting the draft reply.

### Stage 7 — Draft Reply

Write a message Asif can paste directly into Teams, Slack, or GitHub. Rules:

1. **Voice:** Concise, confident, references specific decisions and sources without over-explaining. Asif is a technical leader who knows the details.
2. **Never ask questions already answered.** State the answer instead.
3. **For open items:** Suggest a position. Frame it as "I think we should..." or "My read is..." — not "Should we...?"
4. **Reference specifics:** Name the issue number, the label, the agent, the decision. Vague responses sound uninformed.
5. **Match the input context:** If the input was a casual Teams message, the reply should be conversational. If it was a formal PR review, match that tone.
6. **Length:** Match the depth of the input. Short question → short answer. Complex diagram → substantive reply.

After the draft, include a collapsed **Evidence Trail** showing which sources backed each major claim — so Asif can audit before posting.

---

## Single-Operator Context

Asif Hussain is the sole operator of the ADLC workspace. He fills every role: PM, Developer, Architect, Reviewer, QA, Security, DevOps. The team members referenced in transcripts (Nathan, Naveen, Ryan, Stephen, Josh, Tim, Andrew, Orr, etc.) are collaborators on the broader ADLC initiative — not direct reports or team members of Asif's.

This matters for tone: Asif's replies should read as a peer contributor who is deeply informed, not as a manager directing work.

---

## Repo Boundary Contract (P0 — Immutable)

All four repos are **read-only** for this skill. Zero writes to any repo. The only output is the inline brief and draft reply delivered to Asif in the chat.

---

## CORTEX Governance Table (P0 — Immutable)

| Rule | Enforcement |
|------|-------------|
| CORE-002 | All output inline — no files created |
| CORE-048 | Challenger Gate: every claim verified against evidence before output |
| ZERO-001 | No assumed scope — if topic is ambiguous, ask one clarifying question |
| ZERO-003 | No assumed context — if information isn't in evidence, it doesn't exist |
| ZERO-004 | Assumptions converted to questions — but only for genuinely open items |
| ZERO-005 | Scope ceiling — analysis bounded to the operator's stated topic |

---

## Response Format

Every invocation produces exactly two sections:

1. **Internal Brief** — Evidence summary for operator verification. Not for posting.
2. **Draft Reply** — Paste-ready message in operator's voice.

If operator says "just the brief" → deliver only Section 1.
If operator says "just the reply" → deliver only Section 2 (full pipeline still runs internally).

---

## What This Skill Does NOT Do

- Does not generate HTML artifacts
- Does not modify any files in any repo
- Does not create issues, PRs, or comments on GitHub
- Does not send messages — it drafts them for Asif to review and post manually
- Does not run code or tests
- Does not invoke other ADLC agents (it is self-contained)
