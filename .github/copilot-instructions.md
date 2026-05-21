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

Asif uses a **5-part BLUF response format** across both machines and all tools (Copilot, Claude Code):

```
**TL;DR:** one sentence — what happened + what to do next

**Status:** 🟢 ship-ready / 🟡 needs decision / 🔴 blocked

[Body — per-issue blocks (### N. <name> + Plain English / Impact / Fix / Where bullets)
 OR tables when comparing options. NEVER custom section labels.]

**Your next step:** one explicit sentence naming the file or command Asif acts on.

---

## Summary (scan-and-skip)

1. <one-line restate of body section 1, with clickable links preserved>
2. <one-line restate of body section 2, with clickable links preserved>
…
N. **Next step:** <one-line restate of "Your next step">
```

Three things make the Summary visually stand apart from the body: (1) a `---` horizontal rule with blank lines on each side, (2) an **H2 header** `## Summary (scan-and-skip)` (one level larger than the `### N.` body sections), (3) a blank line between the header and the first item. Include the Summary whenever the body has 2+ sections or the response exceeds ~10 lines; skip it for single-issue updates where it would just duplicate the TL;DR.

Full spec at `_workspace/plan/response-conventions.md`. The non-negotiables: **no custom section labels** like "Deviation from plan", "Verification", "Coord doc", "What changed". (`## Summary (scan-and-skip)` is NOT a custom label — it's the official Part 5 section name.) The fixed structure is what makes cross-machine responses scannable.

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
