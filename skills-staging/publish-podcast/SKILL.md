---
name: publish-podcast
description: "On-demand publisher of completed podcast assets from `content/drafts/<slug>/` to the filesystem-only `content/published/books/<slug>/`. Minimal output: `chapters/` + `episodes/` + `README.md`. The chapter file is what gets uploaded to Google NotebookLM as the SOURCE; the episode file is what gets pasted into NotebookLM's Customize prompt box. ALWAYS invoke when user says 'publish <book-slug>', 'publish kar', '/publish-podcast', '@publish-podcast', 'ship to library', 'publish to library'. Six readiness gates run before any file copies: (G1) chapters/+episodes/ structure, (G2) chapter↔episode pair completeness, (G3) purely-sequential 01..N numbering with no letter suffixes or .5 decimals, (G4) build_episode_txt.py P0=0 on every episode (P1 warn-only by default, blocking under --strict), (G5) orchestrator-state.json shows phase=done OR ship-with-caution|ship-ready|halted_by_operator, (G6) target either doesn't exist OR is safe to wipe (inside library/, not a symlink). Defaults to wipe-and-recreate; --no-wipe coexists; --dry-run prints the plan without writing. The Python script `scripts/podcast/publish_to_library.py` does the deterministic work; this skill is its trigger surface."
locked_decisions:
  - "content/published/books/<slug>/ contains ONLY chapters/ + episodes/ + README.md (no index.md, no podcasts/, no transcripts/, no _meta.json)"
  - "library/ is filesystem-only at <repo-parent>/library/; NOT git-tracked"
  - "wipe-and-recreate is the default; --no-wipe is the escape hatch for coexistence"
  - "ship_to_library.py is deprecated; publish-podcast is the canonical writer of library/"
  - "all 6 gates block by default; --strict elevates P1 to blocking, --force bypasses G5 state checkpoint"
  - "README.md includes publish timestamp, source git SHA, EP→chapter pair table, NotebookLM upload instructions"
---

# publish-podcast — Skill Overview

This skill takes a completed book's workspace and publishes the minimal NotebookLM-ready assets to the filesystem library. It is the **on-demand** counterpart to the in-progress authoring tools (`orchestrate_book.py`, `build_and_ship_chapter.sh`, etc.) — nothing publishes automatically; you invoke this skill when the book is ready for NotebookLM consumption.

## What this skill DOES

1. **Validates** the workspace against 6 readiness gates (see SKILL frontmatter `description` for the full gate list).
2. **Copies** `content/drafts/<slug>/chapters/*.txt` → `content/published/books/<slug>/chapters/`.
3. **Copies** `content/drafts/<slug>/episodes/*.txt` → `content/published/books/<slug>/episodes/`.
4. **Writes** `content/published/books/<slug>/README.md` — human-readable manifest with publish timestamp, source git SHA, EP→chapter pair table, NotebookLM upload instructions.
5. **Updates** `library/_meta/catalog.md` — one row per published book (`<slug>` | episode count | publish date | git SHA).

## What this skill does NOT do

- Does NOT write to `library/` automatically. Always operator-triggered.
- Does NOT write inside the git worktree. Library is filesystem-only at `<podcast-factory>/library/`.
- Does NOT include `_system/`, `chapter-contracts/`, `operator-review.md`, transcripts, audio files, or any authoring-process artifact. NotebookLM doesn't need them and listeners don't either.
- Does NOT regenerate per-episode index pages or per-series metadata. The README.md at the book root is the entire reader surface.
- Does NOT call out to LLMs or external APIs. Deterministic local file operations only.
- Does NOT push to a remote. Library is a local artifact-store; if you want it elsewhere, sync it separately.

## Invocation

```
scripts/podcast/publish_to_library.py <book-slug>
```

Options:

| Flag | Behavior |
|---|---|
| `--strict` | Elevate P1 advisories to blocking. Default: P1 warn-only. |
| `--no-wipe` | Skip the wipe step. Coexist with prior content at `content/published/books/<slug>/`. |
| `--dry-run` | Run all 6 gates + print the would-copy file list. Do not write. |
| `--force` | Skip the G5 state-checkpoint gate (e.g., when state.json is mid-flight from a halt). |

## Gate failure semantics

Default mode (no flags) blocks on ANY of G1–G6 failing. Exit code 1, no files written.

The `--strict` flag tightens G4 only — P1 advisories that would normally warn now block. The other gates are already blocking; `--strict` doesn't make them stricter.

The `--force` flag bypasses G5 only. G5 exists because some pipeline halts leave `state.json` in an ambiguous intermediate state; `--force` is the manual override for "I know the state is fine, just publish."

`--dry-run` runs all 6 gates and reports their outcomes but writes nothing. Useful before a real publish to surface any gate failures up-front.

## Example session

```
$ scripts/podcast/publish_to_library.py kitab-al-riyad --dry-run
==> publish_to_library: kitab-al-riyad
    workspace: content/drafts/kitab-al-riyad
    target:    /Users/.../content/published/books/kitab-al-riyad
    mode:      dry-run

=== Gates ===
OK    [G1] 15 chapters + 15 episodes present
OK    [G2] 15 chapter/episode pairs match
OK    [G3] chapters 1..15 + episodes 1..15 purely sequential
OK    [G4] P0=0 across 15 episodes (P1=23, warn-only)
OK    [G5] state.json phase=done
OK    [G6] target /Users/.../content/published/books/kitab-al-riyad exists; wipe-and-recreate authorized

=== Plan ===
    would copy 15 chapter(s) → .../chapters/
    would copy 15 episode(s) → .../episodes/
    would write .../README.md
    would update catalog row for kitab-al-riyad

==> DRY RUN: no files written. All gates passed.
```

If a gate fails:

```
$ scripts/podcast/publish_to_library.py kitab-al-riyad
…
FAIL  [G3] chapter numbers not purely sequential 1..N: [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
```

The user sees the failing gate, fixes the workspace (renames, rebuilds), re-runs.

## Relation to other tools

- `intake_book.py` — creates the workspace skeleton (preflight).
- `orchestrate_book.py` — drives the in-progress authoring loop.
- `build_episode_txt.py` — validates one episode's customize prompt (called internally by G4).
- `build_and_ship_chapter.sh` — per-chapter author+validate+commit loop on the book branch.
- `ship_to_library.py` — DEPRECATED predecessor; rich-output convention. Do not invoke.
- **`publish_to_library.py`** ← this skill. The on-demand final-mile to NotebookLM-ready library.

## When NOT to use this skill

- The book isn't done yet. Publishing mid-authoring overwrites prior published state with incomplete content. Use the workspace until ship.
- You want to ship a single episode update. The current design is whole-book publishing. If you only updated EP07, `--no-wipe` re-copies all 15 and the rest are byte-identical — still safe, just wasteful. A future `--episode EP07` flag could optimize this.
- The book uses non-NotebookLM downstream (a third-party podcast platform, a custom audio pipeline). Library is NotebookLM-shaped. Different downstream needs a different publisher.
