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

1. <one-line punchy summary of body section 1 — non-technical, complete sentence, clickable links preserved>
2. <one-line punchy summary of body section 2>
3. <one-line punchy summary of body section 3>
4. <…up to ~5 items>

---

### 1. <Plain English issue name> <severity emoji>
<Short PROSE paragraph (2–4 sentences) that naturally covers what happened, the impact, the fix if any, and where to look — with clickable file/commit links woven inline. NO literal sub-bullet labels like "Plain English:", "Impact:", "Fix:", "Where:" — those four words are INSTRUCTIONS to the writer about what to convey, NOT visible structure for the reader.>

### 2. <Plain English issue name> <severity emoji>
<Same shape — short prose paragraph.>

### 3. <Section with genuinely enumerable content> <severity emoji>
<Lead sentence in prose, then bullets or a table ONLY when content actually has enumerable structure (multi-step fix, options to compare, multiple deliverables). When bullets appear, their labels are content-meaningful ("Option A (recommended)", "Step 1", "Before/After"), NEVER the meta-labels above.>

[…tables also OK when comparing options]

---

## Next: 👤 Asif    [or 🤖 AI, depending on who owns the next move]
<If ONE legitimate path exists: one explicit sentence naming the action.>

<If TWO OR MORE legitimate paths exist: alphabetized list, recommended option as A, final option always "Do all of the above":>

A. (Recommended) <best path — what + brief why>
B. <alternative path>
C. <third path if applicable>
D. Do all of the above (A + B + C in sequence)
```

### The four parts in detail

**Part 1 — `## At a glance — <emoji> <status>`** — H2 header. Severity emoji + one-phrase label embedded so status is visible without scrolling. Followed by a numbered list of ~5 items (soft cap), each a complete sentence with clickable links preserved. The reader should be able to act from the summary alone if they trust the recommendation. Then a horizontal rule (`---`) on its own line.

**Part 2 — Body sections (`### N.` PROSE blocks)** — Each section is a short PROSE paragraph (2–4 sentences) that NATURALLY covers what happened, the impact, the fix if any, and where to look — with clickable links woven inline. **No literal `*Plain English:* / *Impact:* / *Fix:* / *Where:*` sub-bullets.** Those four words are instructions to the writer about what to convey, NOT visible markup. Use them as a mental checklist while writing the prose. Use bullets or tables ONLY when content has genuine enumerable structure (multi-step fix, options to compare, multiple deliverables); when bullets appear, their labels are content-meaningful ("Option A (recommended)", "Step 1", "Before/After"), never the meta-labels above. **No custom section header labels** ("Verification", "Coord doc", "Deviation from plan", "What changed") — they fragment the format across sessions and machines.

**Part 3 — Horizontal rule (`---`)** — Sets the Next header apart from body content. Always present, even for single-section responses.

**Part 4 — `## Next: 👤 Asif` or `## Next: 🤖 AI`** — H2 header (visual weight matches the At-a-glance header, creating bookends for the response). Emoji + exactly-one-word actor name (`👤 Asif` for user-owned next move, `🤖 AI` for Claude-owned next move).

**When ONE legitimate path exists**: one explicit sentence naming the action.

**When MULTIPLE legitimate paths exist** (the common case after a multi-issue response): an **alphabetized list of options** where:
- Option `A.` is ALWAYS the recommended path, prefixed `(Recommended)` and followed by the recommendation + brief why
- Option `B.`, `C.`, etc. are alternatives in priority order (most-likely-useful next, all the way down)
- The FINAL letter (D, E, etc., whichever comes last) is ALWAYS "Do all of the above (A + B + C in sequence)" — accommodates the common case of "yes do everything"

This mirrors the AskUserQuestion convention (recommended first, structured options). The reader scans the list, picks the letter, replies with one letter — minimal friction.

**If genuinely independent next moves exist for both Asif AND AI** (rare), write two `## Next:` headers — one per actor. Each can have its own options-list.

### Severity emojis (used both in Part 1 header and per-section in Part 2)

- 🟢 ship-ready — work is done; nothing blocking
- 🟡 needs your decision — action required from Asif (or AI proposes, awaiting go)
- 🔴 blocked — cannot proceed; surface and halt
- ⚠ caution — proceed-with-care; non-blocking risk

### When to include the At-a-glance summary

- Always, when the body has 2+ sections OR the response exceeds ~10 lines
- Skip for single-line acknowledgements ("got it") and ultra-short answers
- For one-section responses, the summary still helps — it's the first thing Asif reads; details are optional

### Worked example — clean response end-to-end

```
## At a glance — 🟢 ship-ready

1. Phase 0d regenerated all 14 chapter contracts against the new refined source — nothing failed ([commit 8a34564](https://github.com/asifhussain60/podcast-factory/commit/8a34564)).
2. The previously broken adams-law YAML self-resolved during the re-run.
3. Downstream Phase 0e is now unblocked.

---

### 1. Phase 0d completed cleanly 🟢
All 14 chapter contracts regenerated against the new refined source — Phase 0e enrichment is unblocked, ran without intervention. See [commit 8a34564](https://github.com/asifhussain60/podcast-factory/commit/8a34564) and [chapter-contracts/](content/podcast/library/books/kitab-al-riyad/chapter-contracts/).

### 2. YAML parse error self-resolved 🟢
The previously-broken adams-law contract was overwritten by the fresh 0d output, so Phase 0f no longer halts on YAML parse failure. Self-fix from the structural re-run — see [adams-law-and-the-prophetic-cycle.yml](content/podcast/library/books/kitab-al-riyad/chapter-contracts/adams-law-and-the-prophetic-cycle.yml).

---

## Next: 👤 Asif
A. (Recommended) Authorize Phase 0e by running `python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad` — clean re-run unblocks all downstream enrichment.
B. Spot-check 2-3 chapter contracts in [chapter-contracts/](content/podcast/library/books/kitab-al-riyad/chapter-contracts/) before authorizing — adds 5 min, catches any latent YAML issues.
C. Defer Phase 0e and finish another book's gate first — only if you have higher-priority cross-book work.
D. Do all of the above (B → C → A in sequence).
```

### Rules and prohibitions

- **No `## Project Status` block.** Deprecated 2026-05-20; details in §2 below.
- **No `**TL;DR:**` opener.** Deprecated 2026-05-21; the At-a-glance numbered list IS the lead, and its first item carries the "what happened" message.
- **No literal `*Plain English:* / *Impact:* / *Fix:* / *Where:*` sub-bullets.** Deprecated 2026-05-21 — those four words are guidance to the writer about what to cover in body prose, NOT visible markup. Body sections are SHORT PROSE paragraphs that naturally weave the four concerns.
- **No `**Next:**` inline-bold line.** Deprecated 2026-05-21 in favor of the `## Next: 👤 Asif` / `## Next: 🤖 AI` H2 header (matches At-a-glance visual weight; bookends the response).
- **No trailing summary paragraphs** ("In summary…", "To recap…"). The At-a-glance list already did that job at the top.
- **No postscripts after the Next header.** The Next header ends the response.
- **Multi-path Next uses alphabetized options.** When 2+ legitimate paths exist, list them as A. (Recommended) / B. / C. / [final letter]. Do all of the above. Single-path: one sentence, no list. **One actor per `## Next:` header** — if genuinely independent next steps exist for both Asif AND AI, write two headers (no more than two total — usually one).
- **Markdown links always.** `[name](path)` for files, `[commit abc1234](https://github.com/asifhussain60/podcast-factory/commit/abc1234)` for commits, `[file.py:42](scripts/file.py#L42)` for line refs. Never bare paths in prose.
- **Explain pipeline jargon parenthetically** the first time it appears in a response (Phase 0e, nāṭiq, P22, abjad, da'wa, etc.).
- **Synthesize, don't dump.** When external knowledge helps (style guides, conventions, prior art), use WebSearch and cite. Otherwise stick to what the codebase shows.
- **Recommend, don't enumerate.** Pick a recommended path and explain why. Asif redirects when needed — don't pre-emptively list all options as equal.

### Common violations — recognize and refuse before sending

The following patterns LOOK template-compliant on a quick glance but break the
scan-and-decide contract. Before every send, audit the draft for each:

| Violation | Wrong | Right |
|---|---|---|
| **Jargon in At-a-glance items** | "X7 framework fix shipped" / "R-FRAMING-WORD-BAND fires" / "ch14b's pronunciation block bloated" | "The behind-the-scenes routing fix you authorized is shipped — the same problem won't happen on the other six chapters with letter-suffix names" / "Validator flagged the new framing as 30% over its word limit" |
| **Multi-sentence items** | "1. Step A landed. The bloat is mostly in section X (1219 words vs EP10's 607). Three contributing sections: A, B, C." | "1. Step A landed; bloat concentrated in one section, detailed below in §2" |
| **Tables embedded in At-a-glance** | "5. Here's the breakdown:" (followed by a markdown table) | "5. One section is 30% over budget; full breakdown in §3" |
| **Custom body section labels** | `### Why ch14b's framing bloated` / `### Three unblock paths` / `### My recommendation` | `### 1. Framing word count exceeds the cap 🔴` (Plain English issue name in the body header; no editorial framing) |
| **Multi-step Next lines** | "**Next:** *AI* — Step 1: trim. Step 2: patch. Step 3: resume." | "**Next:** *Asif* — confirm I should trim the framing via Claude (the cheapest path); patch and resume happen automatically after." |
| **Tiered recommendations as the Next** | "**Next:** *Asif* — confirm the tiered fix (Step 1 quick / Step 2 framework)" | One concrete action with one actor. Future steps belong in body §N as fix-options, not the Next line. |
| **Acronyms without first-mention expansion** | "EP14 framing fails R-FRAMING-WORD-BAND" | "EP14's customize prompt (the framing) is over the validator's word-count cap. The validator rule has the internal label R-FRAMING-WORD-BAND." |

### Pre-send self-check (8 questions; all must be yes)

1. Does my At-a-glance H2 contain a severity emoji + a one-phrase status label?
2. Are all At-a-glance items single, complete, non-technical sentences?
3. Does every body section header read `### N. <Plain English name> <emoji>` — no custom labels?
4. Does the Next line have exactly one actor (`*Asif*` or `*AI*`) and exactly one action?
5. Is there a `---` rule before the body AND before the Next line?
6. Does the response end with the Next line? No postscript, no "let me know," no `## Project Status` block?
7. Are all file paths and commits rendered as markdown links?
8. If I used a project acronym (X3, EP14b, R-XYZ, ch14b), did I either expand it parenthetically on first use OR keep it out of the At-a-glance summary?

If any answer is no, rewrite before sending. The user does not need to ask twice — the template is hard, not soft, and violations break the scan-and-decide contract that's the entire point of the format.

## 2. ~~Project Status block~~ — DEPRECATED 2026-05-20

The pre-BLUF `## Project Status` + `### Work Completed` / `### Work Pending`
block pattern is **deprecated**. It was noisy, rigid, and duplicated information
that the §1 structure already carries more cleanly.

The §1 **At-a-glance** numbered list at the top of every multi-section response
IS the long-running-work summary. The body's per-issue `### N.` prose paragraphs
carry "what's done / what's pending" at the per-item level (each paragraph
naturally covers what happened, impact, fix if any, where to look — as PROSE,
not labeled bullets). For cross-session continuity, the
[book-queue.md](operators/book-queue.md) In-flight / Queue / Completed sections +
the [index.md](operators/index.md) Machine Status dashboard cover the cross-machine
snapshot.

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
- Always link commits when referring to specific work: `commit [abc1234](https://github.com/asifhussain60/podcast-factory/commit/abc1234)`
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
- Body section structure (`### N. <name> <emoji>` headers; CONTENT is now PROSE — see 2026-05-21 second revision in §10 migration note below)
- All severity emojis (same meanings)
- No-custom-section-labels rule
- Cross-machine awareness rules
- File/commit reference conventions

**What both machines do now**: Use the §1 4-part template on every substantive response. Both Studio (asaas) and Air (kitab-al-riyad) sessions follow this; the Studio's next session merges develop and picks up this revision automatically.

## 10. Default response posture — reflect + selectively pushback + interactively ask (added 2026-05-21)

Standing rule for every substantive response. Asif should never have to re-state this; it's the default posture across both Studio and Air sessions.

1. **Reflect** the directive in 1–2 sentences as part of the At-a-glance summary — don't add a separate "What I heard" section.
2. **Pushback when warranted** — if there's a genuine concern (regression risk, scope ambiguity, naming conflict, missing context, a better path exists), surface ONE clear pushback in the body. Not a list of nitpicks. Not a pushback on every directive — only when substance demands it.
3. **Recommend** a best path and explain it briefly. Don't enumerate all options as equals; pick one and say why.
4. **Ask interactively** for genuine decisions using the AskUserQuestion tool with ONE question per call (≤4 options, recommended option FIRST and labeled "(Recommended)"). One question per response — never bundle multiple questions.
5. **Don't over-ask, don't over-pushback** — if the directive is clear, executable, low-risk, and matches established patterns, JUST EXECUTE. A 2-line At-a-glance + a one-section body + `## Next:` is enough. Surface questions and pushbacks only when there's genuine substance.

### The boundary is judgment

When in doubt about whether to surface or just execute, surface — a 15-second pause is cheaper than a wrong commit. But don't waste Asif's time confirming approved patterns. If the same kind of work has been done 3 times before without question, the 4th time doesn't need a confirmation question either.

### Why this rule exists

Asif explicitly directed this 2026-05-21 ("I want this to be the normal pattern. Questions and pushback should be surfaced only when needed"). Repeated prior requests to "reflect on your thoughts, challenge and push back, ask questions interactively one at a time with recommendation as default" indicate the pattern was inconsistent — this rule promotes it from "Asif keeps re-stating" to "standing default both sessions follow."

### Migration note — second revision 2026-05-21

The §1 template's Part 2 (Body sections) was further tightened the same day: literal `*Plain English:* / *Impact:* / *Fix:* / *Where:*` sub-bullets are deprecated; body sections are now SHORT PROSE paragraphs that naturally weave the four concerns with clickable links inline. Those four words remain as guidance for the writer (mental checklist while composing the prose) but never appear as visible markup. Bullets/tables only when content has genuine enumerable structure, with content-meaningful labels.
