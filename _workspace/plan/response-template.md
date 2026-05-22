# Response template — canonical reference (all machines, all branches)

**This file is the canonical, focused reference for the 4-part response template.** Both Mac Studio and Mac Air sessions follow it.

For the full conventions doc with migration notes, deprecations, and rationale, see [response-conventions.md](response-conventions.md). This file is the **bare template + rules + worked example** — what you'd paste into a system prompt or copy when bootstrapping a new session.

Last updated 2026-05-22 — extracted from [response-conventions.md §1](response-conventions.md) so any pulling machine (Air or Studio) picks up the same template via `develop`.

---

## The 4-part response template

Every response to Asif that reports work, surfaces a decision, or hands off follows this **4-part shape, in this exact order, with these exact headers**:

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

---

## Next: 👤 Asif    [or 🤖 AI, depending on who owns the next move]
<If ONE legitimate path exists: one explicit sentence naming the action.>

<If TWO OR MORE legitimate paths exist: alphabetized list, recommended option as A, final option always "Do all of the above":>

A. (Recommended) <best path — what + brief why>
B. <alternative path>
C. <third path if applicable>
D. Do all of the above (A + B + C in sequence)
```

---

## The four parts in detail

**Part 1 — `## At a glance — <emoji> <status>`** — H2 header. Severity emoji + one-phrase label embedded so status is visible without scrolling. Followed by a numbered list of ~5 items (soft cap), each a complete sentence with clickable links preserved. The reader should be able to act from the summary alone if they trust the recommendation. Then a horizontal rule (`---`) on its own line.

**Part 2 — Body sections (`### N.` PROSE blocks)** — Each section is a short PROSE paragraph (2–4 sentences) that NATURALLY covers what happened, the impact, the fix if any, and where to look — with clickable links woven inline. **No literal `*Plain English:* / *Impact:* / *Fix:* / *Where:*` sub-bullets.** Those four words are instructions to the writer about what to convey, NOT visible markup. Use them as a mental checklist while writing the prose. Use bullets or tables ONLY when content has genuine enumerable structure (multi-step fix, options to compare, multiple deliverables); when bullets appear, their labels are content-meaningful ("Option A (recommended)", "Step 1", "Before/After"), never the meta-labels above. **No custom section header labels** ("Verification", "Coord doc", "Deviation from plan", "What changed") — they fragment the format across sessions and machines.

**Part 3 — Horizontal rule (`---`)** — Sets the Next header apart from body content. Always present, even for single-section responses.

**Part 4 — `## Next: 👤 Asif` or `## Next: 🤖 AI`** — H2 header (visual weight matches the At-a-glance header, creating bookends for the response). Emoji + exactly-one-word actor name (`👤 Asif` for user-owned next move, `🤖 AI` for Claude-owned next move).

- **One legitimate path exists**: one explicit sentence naming the action.
- **Multiple legitimate paths exist**: alphabetized list where `A.` is ALWAYS `(Recommended)`, `B./C./…` are alternatives in priority order, and the **final letter** is ALWAYS `Do all of the above (A + B + C in sequence)`.
- **Genuinely independent next moves for both Asif AND AI** (rare): two `## Next:` headers, one per actor.

---

## Severity emojis (used both in Part 1 header and per-section in Part 2)

- 🟢 ship-ready — work is done; nothing blocking
- 🟡 needs your decision — action required from Asif (or AI proposes, awaiting go)
- 🔴 blocked — cannot proceed; surface and halt
- ⚠ caution — proceed-with-care; non-blocking risk

---

## When to include the At-a-glance summary

- **Always**, when the body has 2+ sections OR the response exceeds ~10 lines.
- **Skip** for single-line acknowledgements ("got it") and ultra-short answers.
- For one-section responses, the summary still helps — it's the first thing Asif reads; details are optional.

---

## Worked example — clean response end-to-end

```
## At a glance — 🟢 ship-ready

1. Phase 0d regenerated all 14 chapter contracts against the new refined source — nothing failed ([commit 8a34564](https://github.com/asifhussain60/Journal/commit/8a34564)).
2. The previously broken adams-law YAML self-resolved during the re-run.
3. Downstream Phase 0e is now unblocked.

---

### 1. Phase 0d completed cleanly 🟢
All 14 chapter contracts regenerated against the new refined source — Phase 0e enrichment is unblocked, ran without intervention. See [commit 8a34564](https://github.com/asifhussain60/Journal/commit/8a34564) and [chapter-contracts/](content/podcast/library/books/kitab-al-riyad/chapter-contracts/).

### 2. YAML parse error self-resolved 🟢
The previously-broken adams-law contract was overwritten by the fresh 0d output, so Phase 0f no longer halts on YAML parse failure. Self-fix from the structural re-run — see [adams-law-and-the-prophetic-cycle.yml](content/podcast/library/books/kitab-al-riyad/chapter-contracts/adams-law-and-the-prophetic-cycle.yml).

---

## Next: 👤 Asif
A. (Recommended) Authorize Phase 0e by running `python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad` — clean re-run unblocks all downstream enrichment.
B. Spot-check 2-3 chapter contracts in [chapter-contracts/](content/podcast/library/books/kitab-al-riyad/chapter-contracts/) before authorizing — adds 5 min, catches any latent YAML issues.
C. Defer Phase 0e and finish another book's gate first — only if you have higher-priority cross-book work.
D. Do all of the above (B → C → A in sequence).
```

---

## Rules and prohibitions

- **No `## Project Status` block.** Deprecated 2026-05-20.
- **No `**TL;DR:**` opener.** Deprecated 2026-05-21; At-a-glance item 1 IS the lead.
- **No literal `*Plain English:* / *Impact:* / *Fix:* / *Where:*` sub-bullets.** Deprecated 2026-05-21 — those are guidance to the writer, not visible markup. Body sections are SHORT PROSE paragraphs.
- **No `**Next:**` inline-bold line.** Deprecated 2026-05-21 in favor of `## Next: 👤 Asif` / `## Next: 🤖 AI` H2.
- **No trailing summary paragraphs** ("In summary…", "To recap…"). At-a-glance already did that job.
- **No postscripts after the Next header.** The Next header ends the response.
- **Multi-path Next uses alphabetized options.** `A. (Recommended) / B. / C. / [final letter]. Do all of the above`. Single-path: one sentence, no list. One actor per `## Next:` header; max two total.
- **Markdown links always.** `[name](path)` for files, `[commit abc1234](https://github.com/asifhussain60/Journal/commit/abc1234)` for commits, `[file.py:42](scripts/file.py#L42)` for line refs. Never bare paths in prose.
- **Explain pipeline jargon parenthetically** the first time it appears (Phase 0e, nāṭiq, P22, abjad, da'wa, etc.).
- **Synthesize, don't dump.** When external knowledge helps, cite. Otherwise stick to what the codebase shows.
- **Recommend, don't enumerate.** Pick a path and explain why; Asif redirects when needed.

---

## Default response posture — reflect + selective pushback + interactive ask

Standing rule (Asif set 2026-05-21):

1. **Reflect** the directive in 1–2 sentences inside the At-a-glance summary — no separate "What I heard" section.
2. **Pushback only when warranted** — regression risk, scope ambiguity, naming conflict, better path. Not every directive.
3. **Recommend** a best path and explain it briefly. Don't enumerate options as equals.
4. **Ask interactively** via AskUserQuestion: ONE question per call, ≤4 options, recommended FIRST and labeled `(Recommended)`. Never bundle.
5. **Don't over-ask, don't over-pushback** — clear, executable, low-risk, pattern-matched directives: JUST EXECUTE. 2-line At-a-glance + one-section body + `## Next:` is enough.

**The boundary is judgment**: when in doubt, surface. But don't waste Asif's time confirming approved patterns.

---

## File and commit references

- Always link files: `[refined-english.md](content/podcast/library/books/.../refined-english.md)`
- Always link commits: `commit [abc1234](https://github.com/asifhussain60/Journal/commit/abc1234)`
- Use `file:line` form when referencing code: `[orchestrate_book.py:917](scripts/podcast/orchestrate_book.py#L917)`
- Backticks for inline code only — file paths in markdown links should not also be backticked.
