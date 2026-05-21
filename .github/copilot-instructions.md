# Copilot instructions for the Journal repo

GitHub Copilot auto-loads this file as project-wide guidance. When Asif asks
you (in Copilot Chat in VSCode) about this repo, follow this orientation.

## What this repo is

- A podcast-authoring pipeline driving scholarly Arabic books through Claude + Azure → NotebookLM Audio Overview episodes (under `scripts/podcast/`, `content/podcast/library/books/`)
- A memoir authoring engine for Asif's life story (under `content/babu-memoir/` — Asif IS Babu, the memoir's protagonist)
- A travel-planning skill set (under `skills-staging/trips/`)
- A static site renderer in `site/`

## Cross-machine model

Two physical machines (Mac Studio + Mac Air) coordinate via:
- **ONE shared git repo, ONE working directory per machine**
- Books processed on `book/<slug>` branches; integration via `develop`
- Each machine carries `~/.machine-id` (`mac-studio-primary` or `macbook-air-secondary`)
- Per-machine operator files at `_workspace/plan/operators/<machine-id>.md`

The full discipline lives in `_workspace/plan/operators/coordination-protocol.md`.

## When Asif asks you for help

**For pipeline / orchestration / coord questions:** point him at running the session-starter, OR if he's already running it, work from its output:

```bash
bash _workspace/plan/operators/start-session.sh
```

That script tells you the current book, branch, phase, and next_action.

**For code suggestions in `scripts/podcast/**`:** this is shared framework. Changes here affect both machines; coordinate via `develop` merges. Reference `_workspace/plan/operators/coordination-protocol.md` §6 (shared-infra zones).

**For book content** (`content/podcast/library/books/<slug>/`): one book is owned by one machine at a time (see `_workspace/plan/book-queue.md` In-flight section). Don't touch a book that's not on your machine's branch.

## Response format

Asif uses a **4-part At-a-glance-first template** across both machines and all tools (Copilot, Claude Code). Body sections are PROSE paragraphs that naturally cover what happened / impact / fix / where — NOT labeled sub-bullets. Updated 2026-05-21:

```
## At a glance — <severity emoji> <one-phrase status label>

1. <one-line punchy summary of body section 1 — non-technical, complete sentence, clickable links preserved>
2. <one-line punchy summary of body section 2>
3. <one-line punchy summary of body section 3>
4. <…up to ~5 items>

---

### 1. <Plain English issue name> <severity emoji>
<Short PROSE paragraph (2–4 sentences) covering what happened, the impact, the fix if any, where to look — clickable file/commit links woven inline. NO literal `*Plain English:*`/`*Impact:*`/`*Fix:*`/`*Where:*` sub-bullets — those four words are instructions to the writer, not visible markup.>

### 2. <Plain English issue name> <severity emoji>
<Same shape — short prose paragraph.>

### 3. <Section with genuinely enumerable content> <emoji>
<Lead sentence, then bullets/tables ONLY when content has structure to enumerate. When bullets appear, content-meaningful labels ("Option A (recommended)", "Step 1"), NEVER meta-labels.>

[…tables also OK when comparing options]

---

## Next: 👤 Asif    [or 🤖 AI, depending on who owns the next move]
<One explicit sentence naming the action.>
```

Severity emojis: 🟢 ship-ready / 🟡 needs your decision / 🔴 blocked / ⚠ caution. Used in the At-a-glance header AND per body section. The `## Next:` header uses 👤 for Asif-owned action and 🤖 for AI-owned action.

**Default response posture (added 2026-05-21):** reflect the directive, push back ONLY when warranted (regression risk, scope ambiguity, naming conflict, missing context, better path exists), recommend a best path, ask interactively via AskUserQuestion (one question per call, recommended option FIRST) ONLY when a genuine decision is needed. **Do NOT over-ask** — if the directive is clear/low-risk/pattern-matched, JUST EXECUTE.

**Deprecated** (do NOT use): `**TL;DR:**` opener, standalone `**Status:**` line, trailing `## Summary (scan-and-skip)` block, `## Project Status` block, literal `*Plain English:*` / `*Impact:*` / `*Fix:*` / `*Where:*` sub-bullets, inline `**Next:**` line — all replaced 2026-05-21.

Full spec at `_workspace/plan/response-conventions.md` §1 (template) + §10 (default posture). The non-negotiables: **no custom section labels** like "Deviation from plan", "Verification", "Coord doc", "What changed", "Summary". The fixed 4-part structure with prose bodies is what makes cross-machine responses scannable.

## Authoritative state

When in doubt about phase / status / what's done, read:

```bash
jq '{phase, phase_status, last_completed_phase, last_error}' \
    content/podcast/library/books/<book>/_system/orchestrator-state.json
```

Operator-file frontmatter is a snapshot; `state.json` is truth.

## Don't

- Suggest cross-writing a peer's operator file (see WRITE EXCEPTION protocol in coord-protocol §15 for the rare legitimate case)
- Suggest pushing to the peer's book branch
- Suggest force-push to `main` or `develop`
- Recommend bypassing `git status` cleanliness checks before merges
- Use emojis in code or commits unless Asif invites them (status emojis 🟢/🟡/🔴/⚠ in chat responses are explicitly OK)
