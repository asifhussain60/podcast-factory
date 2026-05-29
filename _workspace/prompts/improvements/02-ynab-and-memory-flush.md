# 02 — Remove YNAB MCP + flush stale memory + fix loop ledger (STRAIGHTFORWARD)

## A. Remove YNAB (your assumption #5)
`/.vscode/mcp.json` registers an unrelated `ynab` server with a **plaintext API key**:

```
"ynab": { "command": "uvx", "args": ["mcp-ynab"],
          "env": { "YNAB_API_KEY": "<REDACTED — rotate this token in YNAB; never commit secrets>" } }
```

Actions (after your OK):
1. Delete the `ynab` block from `.vscode/mcp.json` (and root `.mcp.json` if present — root currently only has `source-library`).
2. **Treat the leaked key as compromised** — revoke/rotate it in the YNAB account. (Even after deletion, it's in git history if the file was ever committed; `git log -p -- .vscode/mcp.json` to confirm. If committed, the key must be rotated regardless.)
3. Keep only `source-library` registered.

## B. Stale memory to flush
Global + project memory checked. Flush/fix these:

| Memory file | Problem | Fix |
|---|---|---|
| `project_podcast_reader.md` | Says reader is at `podcast-factory/podcast-reader/` — that dir doesn't exist; reader is in `plan-dashboard/` | Rewrite path, or fold into a single `project_site_reader.md` |
| `project_postprod_vacuum_ledger.md` | Points to `book/the-master-and-the-disciple` branch as ACTIVE; current branch is `develop`, that work appears landed | Verify against git; demote or delete |
| `MEMORY.md` index | References above | Update the one-line hooks |

Memory entries that are still ACCURATE and should stay: response-format, plan-format, plan-dashboard-snapshots-live, heartbeat rules, book-processing-pattern, extensibility-first, glossary-overlay, content-aware-format, slide-decks-required, llm-api-infra, repo-architecture, restructure-2026-05-23.

## C. Fix the corrupted loop ledger
`_workspace/prompts/loop-intelligence.md` lines ~42-131 are ~13 repetitions of the same `Chain W1–W2 / W1` block — the H3 autonomous chain driver looped and re-appended. Truncate the Iteration Log to the unique entries (keep one representative block + the distinct early entries). No information is lost; the repeats are noise.

> No deletions made yet — holding per your "no changes" instruction. All three are low-risk and ready to apply on your word.
