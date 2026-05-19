# Orchestrator fix for large books (kitab-al-riyad and beyond)

**Status:** implemented · branch `book/kitab-al-riyad` · orchestrator v1.2
**Context:** Asif's prompt — "Fix the orchestrator. I want to process two large
PDFs end-to-end… You can break chapters into sections (episode per section). For
smaller books stick with the chapter. Do you have a better recommendation?"

## What was actually broken

Phase 0b on `kitab-al-riyad` (88k-word raw extract) ran 22:51 → 23:20 and died
at the 30-min `claude -p` timeout. Root cause: **one monolithic LLM call** for
the entire book. The 30-min ceiling is a property of the headless CLI, not the
input. So any book with more than ~30k words of OCR'd raw text would block here
regardless of how chapters are later carved.

The 88k-word extract was the symptom that surfaced two orthogonal problems:

1. **Phase 0b / 0c monolithic shellout** — pipeline-breaking. Bug.
2. **Per-chapter granularity for very long source chapters** — UX limitation,
   not a blocker. (Asif's question.)

These needed different fixes. The chunking fix (1) is the one that actually
unblocks large books. The section-mode fix (2) is the user's request, scoped
narrowly so it does not cascade through downstream code.

## Why I did not adopt the nested-folder proposal

Asif suggested: "create a new folder structure breaking down chapters into
sections (episode per section instead of per chapter)."

I went a different way and kept the **flat layout** because the invariant that
makes the whole pipeline tractable is:

> One episode  =  one chapter file  =  one contract  =  one NotebookLM upload.

Every downstream tool (`extract_chapter.py`, `build_episode_txt.py`,
`podcast-challenger`, `podcast-trainer`) assumes that invariant. Nesting
chapters into sub-folders would have rippled through every one of them and
broken the `chapters/ch##-*.txt` glob that drives the per-chapter loop. The
chunking is for the orchestrator's internal LLM throughput, not the
human-visible episode layout.

Sections are just named episodes with a suffix (`ch03a-foo.txt`,
`ch03b-bar.txt`) and a back-reference (`source_chapter_ref: ch03`,
`section_index: 1`) inside their contract. The series-plan surfaces a
source→episode map for human review. Nothing downstream needs to know whether
`ch03a-` came from a whole source chapter or half of one.

## The two-fold fix

### Fix 1 — Chunked Phase 0b / 0c (`scripts/podcast/_chunking.py`)

- Paragraph-aligned windows of ~3000 words (0b) / ~8000 words (0c), with a
  120-word context-overlap block prepended to every continuation.
- Per-window `claude -p` calls (10-min timeout each, well under the 30-min
  ceiling).
- **Checkpointed:** every window writes `_chunks/0b/win-NNN.in.md` (input
  provenance) and the model writes `win-NNN.out.md` (its output). On `--resume`,
  windows whose `out.md` already exists+non-empty are skipped. Crash-safe.
- Stitching strips common LLM preambles ("Here is the refined text:") and stray
  markdown fences before assembling the final `refined-english.md` /
  `_phonetics.md`.
- `_phonetics.md` merge dedupes by first column (term, case-folded), preserving
  first-occurrence order across windows.

Validated on the real `kitab-al-riyad/raw-extract.md`: 32 windows, mean 2873
words, with `<!-- context-overlap from prior window -->` blocks on windows
2-32. Total throughput ~92k words.

### Fix 2 — Phase 0d `unit_mode` (`chapter | section | auto`)

- New state config `state.config.unit_mode`, written at initial-run time from
  `--unit-mode` (default `auto`).
- The Phase 0d prompt branches:
  - `chapter`: one episode per source chapter, never split. Small books / short
    chapters.
  - `section`: split every source chapter into sections sized to the tier band.
  - `auto`: per-chapter decision — split only when source word count exceeds
    1.5× the tier upper bound. Recommended default.
- Section episodes are named `ch03a-`, `ch03b-`, `ch03c-`. Each contract gets
  `source_chapter_ref` + `section_index`.
- When `unit_mode != chapter`, Phase 0d also writes
  `_system/source/text/source-chapter-map.md` (pipe table of source-chapter →
  episodes) that Phase 0f embeds in the series-plan for human review.

### Operator ergonomics — `--retry-phase`

Resetting a `failed` phase used to require hand-editing
`orchestrator-state.json`. New flag:

```bash
python3 scripts/podcast/orchestrate_book.py --resume <slug> --retry-phase 0b
```

Sets the named phase to `pending`, clears any downstream `completed` markers in
the authoring band (0b → 0e), and resumes. The chunking checkpoint means a
retried 0b/0c reuses any already-completed windows.

## How to drive `kitab-al-riyad` from here

State is clean (0a complete, 0b pending). No `--retry-phase` needed:

```bash
git checkout book/kitab-al-riyad
python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad
```

That will window-process 0b (~32 windows, ~5 min each on a stable connection)
into `refined-english.md`, then chunk 0c into `_phonetics.md`, then 0d (with
`unit_mode=auto`) into the contracts + chapter txts, then 0e, then halt at 0f
for series-plan review.

## Files

- NEW: `scripts/podcast/_chunking.py`
- CHANGED: `scripts/podcast/_authoring.py` (phases 0b, 0c, 0d rewritten)
- CHANGED: `scripts/podcast/orchestrate_book.py` (CLI flags, state config,
  series-plan template, `--retry-phase` runtime)
- CHANGED: `scripts/podcast/_progress.py` (version bump to 1.2)
