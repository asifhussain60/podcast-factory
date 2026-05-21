# Response conventions — Claude Code sessions on this repo

**Authoritative across all machines. Both Mac Air and Mac Studio sessions follow this.**
Updated 2026-05-21 by the Air session — extracted from the Air's per-machine
memory (`feedback_response_closing_status.md`, `feedback_askuserquestion_ordering.md`)
and the Air's operator-prompt for the kitab-al-riyad run, so that both machines
respond to Asif in exactly the same shape.

If this file conflicts with a session-specific operator prompt, the operator prompt
wins for that session, and the operator-file owner updates this doc to capture
the divergence.

---

## 1. BLUF response format (the primary structure for every substantive update)

Every response to Asif that reports work, surfaces a decision, or hands off
follows this 4-part shape:

```
**TL;DR:** one sentence in plain English — what happened + what to do next.
Anyone (technical or not) should understand it.

**Status:** 🟢 ship-ready / 🟡 needs your decision / 🔴 blocked

[Body — per-issue or per-step blocks when there are multiple items, each shaped as:
   **N. <Plain English issue name>** <severity emoji>
   - *Plain English:* one sentence anyone can understand
   - *Impact:* what this means for the next phase
   - *Fix:* concrete resolution + cost (dollars + minutes if relevant)
   - *Where:* [filename](path) and/or [commit](github-url) clickable refs
]

**Your next step:** one explicit sentence naming the file or command Asif acts on.
```

Rules:
- Explain pipeline jargon (Phase 0e, nāṭiq, P22, abjad, da'wa) in a parenthetical
  the first time it appears in a response.
- No mega-paragraphs. No raw `~` before text or numbers in prose (VSCode preview
  interprets as strikethrough — use "about" instead).
- Markdown links for files and commits: `[name](path)` and
  `[commit](https://github.com/asifhussain60/Journal/commit/<sha>)`.
- Severity emojis: 🟢 ship-ready / 🟡 needs decision / 🔴 blocked / ⚠ caution.
- Tables are encouraged when comparing options or surfacing per-item state.

## 2. The Project Status block (long-running work summary)

For tasks spanning many turns, the BLUF can be followed by a `## Project Status`
block when surfacing where we are overall. Mandatory sub-sections:

```
## Project Status

### Work Completed
- bullet list of done items, with commit refs

### Work Pending
- bullet list of remaining items, in priority order
```

Optional sub-sections (use only when relevant):
- `### Blockers` — what's stopping progress
- `### Next Action` — single sentence naming the file/command
- `### Decisions Needed` — questions for Asif
- `### Risks` — what could go wrong
- `### Verdict` — ship-ready / needs-fix / blocked

Skip the block entirely on small interactive turns (single question, single
acknowledgement). Use it when a VP needs a coffee-break update and would want
to see the whole picture.

## 3. AskUserQuestion conventions

When using the AskUserQuestion tool:
- The **recommended option must be FIRST** and labeled "(Recommended)" in the
  label text
- Remaining options ordered by priority (highest → lowest)
- This applies to every question in every call — no exceptions

## 4. Halt-and-surface pattern

When the user gives you autonomous-mode authorization, halt and surface to
the user (rather than continuing) at these moments:

- Hard regression detected (e.g., a fix that doesn't fix)
- Any hallucinated artifact (made-up filename, fabricated quote, invented commit)
- Cost cap exceeded (>$8 single-task, >$20 multi-task default; user can override)
- Wall-clock cap exceeded (>2 hours for a "should be 1 hour" task)
- Decision boundary the user reserved for themselves (often called out as
  "halt at X gate" in the operator prompt)
- Any destructive operation (force-push, rm -rf, drop table, dropping uncommitted
  work, cherry-pick with conflicts the user hasn't seen)

Auto-fix without halting:
- Transient LLM/network failures (retry)
- Stale `phase_status=running` locks (flip to failed + resume)
- Missing intermediate files that re-resume produces (just re-resume)

## 5. Tone and brevity

- Match response length to task complexity. Simple question = direct answer,
  no headers and sections.
- Don't narrate internal deliberation. User-facing text is communication, not
  commentary on your thought process.
- Updates between events: state results and decisions directly. "Win-007 clean"
  is better than "I checked win-007 and it appears to be clean as I had hoped."
- End-of-turn: one or two sentences. What changed + what's next. Nothing else
  unless the BLUF format applies.
- No emoji except the status set above and where the user has explicitly invited
  them (e.g., commit messages he's reviewing).

## 6. File and commit references

- Always link files: `[refined-english.md](content/podcast/library/books/.../refined-english.md)`
- Always link commits when referring to specific work: `commit [abc1234](https://github.com/asifhussain60/Journal/commit/abc1234)`
- Use `file:line` form when referencing code: `[orchestrate_book.py:917](scripts/podcast/orchestrate_book.py#L917)`
- Use backticks for inline code only — file paths in markdown links should
  not also be backticked.

## 7. Cross-machine awareness (critical for multi-Claude operation)

When acting:
- Check what other machines are doing (read peer operator files; `git log
  origin/<other-branch>`) before any destructive or shared-state action.
- For shared state changes (develop branch, framework code in `scripts/podcast/`,
  shared infra in `content/podcast/.skill/`), surface a plan + ask before
  executing.
- Always know which branch you're on, and never accidentally check out a
  peer's branch.
- Operator-file ownership: each machine ONLY writes its own operator file.
  Reading peer operator files is encouraged; writing them is forbidden except
  by explicit one-time exception from Asif (record the exception inline in
  the file).

## 8. Memory awareness

The Air session has a machine-local memory store at
`~/.claude/projects/-Users-asifhussain-PROJECTS-journal/memory/`. The Studio
session has its own at the equivalent path on the Studio machine. Memory
files do NOT cross machines — that's why conventions like these live in this
tracked file.

If a session learns something cross-cutting (a convention the other machine
should also follow), it commits the learning to this file (or to
`_workspace/plan/coordination-protocol.md` if it's about coordination
specifically) rather than just to local memory.
