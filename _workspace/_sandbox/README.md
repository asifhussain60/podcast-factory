# `_sandbox/` — content triage inbox

Universal drop zone for raw inputs the podcast agent will route into the
library. Nothing here is canonical; everything here is in-flight.

## Contract

1. **Human drops** anything into `_sandbox/`: MP3s, PDF scans, TurboScribe
   `.txt` exports, articles, transcripts, screenshots — by themselves or
   grouped in subfolders. Optionally include a `_notes.md` describing what
   the content is, the intended book/lecture, the source language, and any
   processing hints (e.g. "Urdu lecture, transcribe with `--locale ur-PK`").

2. **Human engages the podcast agent** with initial instructions:
   > "Triage the kunooz files in `_sandbox/`. Lectures by Sayyidna Mufaddal
   > Saifuddin TUS. Treat TurboScribe as source of truth, MP3 as reference."

3. **Agent picks up, classifies, and routes** each file into the canonical
   layout under `library/<category>/<book-slug>/_source/...`. Categories are
   `books`, `articles`, `documents`, `lectures`, `interviews`, `letters`.

4. **Agent decides keep-vs-delete** per file:
   - **Keep** (move into `_source/`): TurboScribe transcripts, refined text,
     anything the pipeline or future training runs may need to re-derive.
   - **Delete from sandbox**: large binaries already preserved elsewhere
     (e.g. MP3 backed up to cloud), duplicates, intermediate scratch.
   - **When in doubt**: keep, but make sure the path is git-ignored if it's
     a binary that would bloat the repo.

5. **Sandbox returns to empty.** This directory should rarely contain more
   than one in-flight batch at a time.

## Git policy

Everything inside `_sandbox/` is gitignored except this README. The agent
moves files *out* of the sandbox; nothing here should ever be committed.

## Why a sandbox at all?

Without it, raw inputs land in sibling category dirs (`library/audio/`,
`library/turboscribe/`) that get out of sync with the canonical book dirs
(`library/lectures/kunooz-al-hikmah/`). The sandbox forces a single
entrypoint: drop here, agent routes, layout stays clean.
