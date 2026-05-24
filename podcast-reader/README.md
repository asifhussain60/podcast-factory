# podcast-reader

Local-first reading-and-review companion for podcast-factory worktree content.

**See [SPEC.md](SPEC.md) for the full design.**

## Status

Design locked 2026-05-23. Implementation pending (Phase 0 bootstrap not yet started).

## Quick orientation

- **Purpose:** review chapter-contracts (`*.yml`) across worktrees with Quran/Hadith/Arabic auto-highlighted, jump-key navigation, and inline comments that flow back to Claude Code.
- **Stack:** Astro + Tailwind + React islands + Pagefind.
- **Content source:** live glob from `~/PROJECTS/podcast-factory/content/drafts/`.
- **Prefs:** on-disk JSON at `~/.config/podcast-reader/prefs.json`.
- **Comments:** sidecar JSON next to each contract (`<contract>.yml.review.json`).

## Folder structure

See [SPEC.md §Folder structure](SPEC.md#folder-structure).

## Phases

See [SPEC.md §Implementation phases](SPEC.md#implementation-phases).
