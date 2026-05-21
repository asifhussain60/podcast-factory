# Response conventions — Claude Code sessions on this repo

**Authoritative across all machines. Both Mac Air and Mac Studio sessions follow this.**
Updated 2026-05-21 by the Air session — At-a-glance-first template adopted (inverts Studio's prior Summary-at-end design) per Asif's directive: read summary, scroll for details if needed, act on a single clear next-step line.

If this file conflicts with a session-specific operator prompt, the operator prompt
wins for that session, and the operator-file owner updates this doc to capture
the divergence.

---

## 1. Response shape — the 4-part template for every substantive update

Every response to Asif that reports work, surfaces a decision, or hands off
follows this **4-part shape, in this exact order, with these exact headers**:

```
## At a glance — <severity emoji> <one-phrase status label>

1. <one-line punchy summary of body section 1 — non-technical, complete sentence>
2. <one-line punchy summary of body section 2>
3. <one-line punchy summary of body section 3>
4. <one-line punchy summary of body section 4>
5. <one-line punchy summary of body section 5>

---

### 1. <Plain English issue name> <severity emoji>
- *Plain English:* one sentence anyone can understand
- *Impact:* what this means for the next phase
- *Fix:* concrete resolution + cost (dollars + minutes if relevant)
- *Where:* [filename](path) and/or [commit](github-url) clickable refs

### 2. <Plain English issue name> <severity emoji>
- (same shape)

[…more body sections as needed; tables also OK when comparing options]

---

**Next:** *Asif* or *AI* — one explicit sentence naming the action and the actor.
```

### The four parts in detail

**Part 1 — `## At a glance — <status>`** — Visually distinct H2 header, severity emoji + one-phrase label embedded (so status is visible without scrolling). Followed by a numbered list of ~5 items (soft cap), each a complete sentence that stands alone. The reader should be able to act from the summary alone if they trust the recommendation. Then a horizontal rule (`---`) on its own line to set the summary apart from the details.

**Part 2 — Body sections** — Use `### N. <Plain English name>` headers with the canonical sub-bullets (*Plain English* / *Impact* / *Fix* / *Where*). OR tables when comparing options. OR short paragraphs for single-issue responses. **No custom section labels** like "Verification", "Coord doc", "Deviation from plan", "What changed" — they fragment the format across sessions and machines.

**Part 3 — Horizontal rule (`---`)** — Sets the Next line apart from body content. Always present, even for single-section responses.

**Part 4 — `**Next:**` line** — One italicized actor name (`*Asif*` or `*AI*`), then an em-dash, then one explicit sentence naming the action. **Exactly one word for the actor** — not "we", not "us", not "the user", not "the assistant". It's a delegation marker. No multi-step lists; pick one and name it.

### Severity emojis (used both in Part 1 header and per-section in Part 2)

- 🟢 ship-ready — work is done; nothing blocking
- 🟡 needs your decision — action required from Asif
- 🔴 blocked — cannot proceed; surface and halt
- ⚠ caution — proceed-with-care; surfaces a non-blocking risk

### When to include the At-a-glance summary

- Always, when the body has 2+ sections OR the response exceeds ~10 lines
- Skip for single-line acknowledgements ("yes, that's right") and ultra-short answers
- For one-section responses, the summary still helps — it's the first thing Asif reads; details are optional

### Worked example — clean response end-to-end

```
## At a glance — 🟢 ship-ready

1. Phase 0d regenerated all 14 chapter contracts against the new refined source — nothing failed.
2. The previously broken adams-law YAML self-resolved during the re-run.
3. Downstream Phase 0e is unblocked.

---

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

---

**Next:** *Asif* — authorize Phase 0e by running `python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad`.
```

### Rules and prohibitions

- **No `## Project Status` block.** Deprecated 2026-05-20; details in §2 below.
- **No `**TL;DR:**` opener.** Deprecated 2026-05-21; the At-a-glance numbered list IS the lead, and its first item carries the "what happened" message.
- **No trailing summary paragraphs** ("In summary…", "To recap…"). The At-a-glance list already did that job at the top.
- **No postscripts after the Next line.** The Next line ends the response.
- **No multi-step Next lines.** Pick one action, name one actor. If there are genuinely independent next steps for multiple actors, write one **Next** line per actor (no more than two total — usually one).
- **Markdown links always.** `[name](path)` for files, `[commit abc1234](https://github.com/asifhussain60/Journal/commit/abc1234)` for commits, `[file.py:42](scripts/file.py#L42)` for line refs. Never bare paths in prose.
- **Explain pipeline jargon parenthetically** the first time it appears in a response (Phase 0e, nāṭiq, P22, abjad, da'wa, etc.).
- **Synthesize, don't dump.** When external knowledge helps (style guides, conventions, prior art), use WebSearch and cite. Otherwise stick to what the codebase shows.
- **Recommend, don't enumerate.** Pick a recommended path and explain why. Asif redirects when needed — don't pre-emptively list all options as equal.

## 2. ~~Project Status block~~ — DEPRECATED 2026-05-20

The pre-BLUF `## Project Status` + `### Work Completed` / `### Work Pending`
block pattern is **deprecated**. It was noisy, rigid, and duplicated information
that the §1 structure already carries more cleanly.

The §1 **At-a-glance** numbered list at the top of every multi-section response
IS the long-running-work summary. The body's per-issue `### N.` blocks carry
"what's done / what's pending" at the per-item level (each block has
*Plain English* + *Impact* + *Fix* + *Where*). For cross-session continuity,
the [book-queue.md](operators/book-queue.md) In-flight / Queue / Completed
sections + the [index.md](operators/index.md) Machine Status dashboard cover
the cross-machine snapshot.

If you find a stale `## Project Status` reference in any operator file, agent spec,
or coord doc, replace it with a pointer to §1 (At-a-glance template). Tracked
stale refs as of 2026-05-21 are all reconciled across `_workspace/plan/operators/*`
and `.github/agents/*`; flag any new ones at file-edit time.

## 3. AskUserQuestion conventions

When using the AskUserQuestion tool:
- The **recommended option must be FIRST** and labeled "(Recommended)" in the
  label text
- Remaining options ordered by priority (highest → lowest)
- This applies to every question in every call — no exceptions
- **Push back if there's a better path** — if the question's framing has a flaw,
  surface that in the response BEFORE asking, then either reframe or skip the
  question entirely.

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
- **Non-technical by default.** Even when the topic is technical (regex,
  validator rules, orchestrator phases), translate to plain language in the
  At-a-glance list. The body's `### N.` sections can carry the precise terms.
- Don't narrate internal deliberation. User-facing text is communication, not
  commentary on your thought process.
- Updates between events: state results and decisions directly. "Win-007 clean"
  is better than "I checked win-007 and it appears to be clean as I had hoped."
- End-of-turn: one or two sentences for trivial replies. For substantive
  updates, the 4-part template is mandatory.
- No emoji except the severity set (🟢 / 🟡 / 🔴 / ⚠) and where the user has
  explicitly invited them.

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

## 9. Migration notes — 2026-05-21 inversion (Studio's Summary-at-end → Air's At-a-glance-at-top)

**Why the change**: Asif's reading pattern is scan-decide-then-scroll, not narrative-then-recap. Front-loading the summary saves the cognitive cost of scrolling-to-find-the-action-line. Studio's earlier Part 5 design (Summary at end) had the right intent but the wrong position; this revision relocates and renames it.

**What inverted**:
- "## Summary (scan-and-skip)" at END → "## At a glance — <status>" at TOP
- "**TL;DR:**" opener line → DEPRECATED (absorbed into At-a-glance item 1)
- "**Status:** 🟢/🟡/🔴" standalone line → folded into the At-a-glance H2 header
- "**Your next step:**" line at end → "**Next:** *<actor>* — …" line at end (same position, renamed for actor delegation)

**What was preserved**:
- Body section structure (`### N.` + *Plain English* / *Impact* / *Fix* / *Where*)
- All severity emojis (same meanings)
- No-custom-section-labels rule
- Cross-machine awareness rules
- File/commit reference conventions

**What both machines do now**: Use the §1 4-part template on every substantive response. Both Studio (asaas) and Air (kitab-al-riyad) sessions follow this; the Studio's next session merges develop and picks up this revision automatically.
