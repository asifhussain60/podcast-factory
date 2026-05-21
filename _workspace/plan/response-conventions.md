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
follows this **5-part shape, in this exact order, with these exact section labels**:

```
**TL;DR:** one sentence in plain English — what happened + what to do next.
Anyone (technical or not) should understand it.

**Status:** 🟢 ship-ready / 🟡 needs your decision / 🔴 blocked

[Body — per-issue or per-step blocks when there are multiple items.
 ALWAYS use this canonical block shape — do not invent custom section labels:

   ### N. <Plain English issue name> <severity emoji>
   - *Plain English:* one sentence anyone can understand
   - *Impact:* what this means for the next phase
   - *Fix:* concrete resolution + cost (dollars + minutes if relevant)
   - *Where:* [filename](path) and/or [commit](github-url) clickable refs

 OR tables when comparing options / surfacing per-item state.
 OR (for short single-issue updates) one or two short paragraphs.

 DO NOT use custom section labels like "Deviation from plan", "Verification",
 "Coord doc", "Next per machine roadmap", "What changed", etc. The fixed
 structure (TL;DR / Status / Body blocks or table / Your next step / Summary)
 is what makes responses scannable across sessions and machines. Custom labels
 fragment the format.]

**Your next step:** one explicit sentence naming the file or command Asif acts on.

---

## Summary (scan-and-skip)

1. <one-line restate of body section 1>
2. <one-line restate of body section 2>
…
N. **Next step:** <one-line restate of "Your next step">
```

The **Summary** is an ordered list at the very end, **visually separated** from the rest of the response by:
- A horizontal rule (`---`) on its own line, with a blank line on each side
- An H2 header (`## Summary (scan-and-skip)`) — one level larger than the `###` body section headers, so it stands out as a distinct concluding zone (not just another body section)
- A blank line between the header and the first list item

Each item is ONE LINE summarizing one body section (numbered sections). The final item restates the next step, prefixed `**Next step:**` for visual anchor. Purpose: Asif can scroll to the bottom, scan 5–10 lines in a clearly-set-apart zone, and decide whether to scroll up for detail — never has to read the full response top-to-bottom to know what changed and what to do.

**When to include the Summary:** any time the body has 2+ sections, or whenever the total response exceeds ~10 lines. Skip the Summary for single-issue or single-paragraph updates where it would just duplicate the TL;DR.

### Worked example — what a clean BLUF response looks like end-to-end

```
**TL;DR:** Phase 0d re-run shipped clean; 14 chapter contracts now reference the
new refined-english.md verbatim, and the broken adams-law YAML self-resolved.

**Status:** 🟢 ship-ready

### 1. Phase 0d completed cleanly 🟢
- *Plain English:* All 14 chapter contracts regenerated against the new refined source.
- *Impact:* Downstream Phase 0e enrichment can proceed safely.
- *Fix:* (none needed; ran clean)
- *Where:* [commit 8a34564](https://github.com/asifhussain60/Journal/commit/8a34564), [chapter-contracts/](content/podcast/library/books/kitab-al-riyad/chapter-contracts/)

### 2. YAML parse error self-resolved 🟢
- *Plain English:* The bad contract from the prior run was overwritten by the fresh 0d output.
- *Impact:* Phase 0f no longer halts on YAML parse failure.
- *Fix:* (none needed; structural fix from re-run)
- *Where:* [adams-law-and-the-prophetic-cycle.yml](content/podcast/library/books/kitab-al-riyad/chapter-contracts/adams-law-and-the-prophetic-cycle.yml)

**Your next step:** authorize advancing to Phase 0e — `python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad`.

---

## Summary (scan-and-skip)

1. 14 chapter contracts regenerated cleanly against the new refined-english.md ([commit 8a34564](https://github.com/asifhussain60/Journal/commit/8a34564))
2. Previously-broken adams-law YAML self-resolved during the re-run
3. **Next step:** authorize Phase 0e — `python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad`
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
- **No custom section labels.** Body content lives inside the structured blocks
  above, inside tables, or in short paragraphs. Never invent your own headings
  ("Coord doc:", "Verification:", "Deviation from plan:") — they fragment the
  shared format and make responses harder to scan when toggling between
  machine sessions.
- **Summary items keep clickable links** for files and commits, even though they're
  one-liners. Asif should be able to act from the Summary without scrolling.

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
