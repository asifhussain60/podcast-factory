# Extract capability — one chapter → one NotebookLM bundle

The `/podcast` skill exposes a single deterministic capability for the common case (one chapter, one episode). It coexists with the Series Mode (Phase 0 of `SKILL.md`) and shares the same output layout.

## When to use which mode

| Mode | When | Entry point |
|---|---|---|
| **Extract Mode** (this doc) | One chapter, already authored, ready to bundle | `scripts/podcast/extract_chapter.py` |
| **Series Mode** (`SKILL.md` §1.5) | Multi-chapter PDF or book that needs to be ingested, segmented, and enriched | `/podcast` skill conversation, Phase 0 |

Extract Mode does **not** ingest, distill, or enrich. It assumes the chapter file already exists in a published form. It is the right answer for re-extracting any single chapter from an already-enriched book.

## Command

```
python3 scripts/podcast/extract_chapter.py <chapter-ref>
python3 scripts/podcast/extract_chapter.py <chapter-ref> --contract <path>
python3 scripts/podcast/extract_chapter.py <chapter-ref> --force
```

## Chapter ref resolution

Resolution order (first definitive match wins; ambiguity is an error):

| Order | Resolution | Example |
|---|---|---|
| 1 | Literal path (absolute or repo-relative) | `content/podcast/library/<category>/<book-slug>/chapters/ch##-<slug>.txt` |
| 2 | `<book-slug>/<ref>` shorthand (forces resolution within one book) | `<book-slug>/ch01-<slug>` |
| 3 | Bare `<ref>` searched across `content/podcast/library/*/*/chapters/<ref>.txt`. If two books own the same slug, the script refuses with a disambiguation error rather than silently picking one. | `ch01-<slug>` |

A missing chapter is a hard error — the extractor refuses to invent one.

## Contract resolution

| Order | Resolution |
|---|---|
| 1 | `--contract <path>` (explicit) |
| 2 | `content/podcast/library/<category>/<book-slug>/chapter-contracts/<chapter-slug>.yml` |
| 3 | A stub is written to location (2) with `[TODO]` markers; re-run with `--force` after editing |

The full schema lives in `chapter-contract.template.yml`. The contract is the I/O surface — everything the extractor needs is in it. The extractor never invents fields.

## Output layout (per `source_type`)

```
content/podcast/library/<category>/<book-slug>/
├── chapters/ch##-<slug>.txt                       ← chapter copy (SOURCE upload; THE refinement target)
├── chapter-contracts/<slug>.yml                   ← the signed contract
├── _system/episode-drafts/EP##-<slug>/
│   ├── 00-framing.md         ← CUSTOMIZE PROMPT (downstream: build_episode_txt.py)
│   ├── 02-key-passages.md    ← scaffold; LLM-SELECT downstream
│   ├── 03-context-pack.md    ← scaffold; LLM-FILL downstream
│   ├── 04-discussion-spine.md ← N beats per length_target; LLM-FILL downstream
│   └── 99-show-notes.md      ← from contract.show_notes
```

No `01-source-primary.md`. Under v3.4's two-file deliverable model the chapter file IS the source — there is no second copy in the draft folder. See SKILL.md §0 Invariant 1.

`<book-slug>` is the directory name under `content/podcast/library/`.

Downstream, `build_episode_txt.py <bucket-root> EP##-<slug>` emits the final `episodes/EP##-<slug>.txt` (the customize-prompt-only file pasted into NotebookLM's Customize box).

## Determinism guarantee

Same chapter file + same contract → byte-identical bundle scaffolding. There are no timestamps, no random ordering, no environment-dependent paths in any emitted file. Slots that require downstream LLM authoring are marked with `[LLM-SELECT]`, `[LLM-FILL]`, or `[TODO]` — these are the only fields where content can drift between runs.

The extractor refuses to overwrite a file that has changed unless `--force` is passed.

## Boundary (SKILL.md §9)

Extract Mode reads only from `content/podcast/**`. Memoir paths are out of scope — the adapter inside `extract_chapter.py` enforces this via `PROHIBITED_PATH_PREFIXES`:

| Sanctioned | Prohibited |
|---|---|
| `content/podcast/**` | `content/babu-memoir/**` |

A read that resolves into a prohibited path exits with `BOUNDARY VIOLATION` and a non-zero code.

## Worked examples

Concrete CLI traces (idempotent re-render, first-run stub flow, ambiguous-ref disambiguation) live in [`worked-examples.md` §1](worked-examples.md#1--extract_chapterpy-cli-usage). Same shape applies to every book.

## Splitting policy (standing rule)

A source chapter that exceeds the NotebookLM word band must be split into derivative chapters in the podcast bucket. The original source chapter is never modified.

### Trigger

| Source word count | Action |
|---|---|
| ≤ 4,500 words | Single derivative; ship as-is |
| 4,500 – 5,500 words | Single derivative; set `length_target: longer` in the contract |
| > 5,500 words | **Split required** — `build_episode_txt.py` refuses anything over 5,500 (canon: `notebooklm-best-practices.md` §3) |

The extractor warns at extract time when any of these thresholds are crossed. Splitting decisions are authorized to be made autonomously by the skill — no per-chapter confirmation needed. The skill must:

- Place each derivative inside `content/podcast/library/<category>/<book-slug>/chapters/` as a plain `.txt` file.
- Title each derivative with a `kebab-case`, single-noun or short-noun-phrase, clean English title that reflects the content. No version suffixes, no date stamps, no Arabic phonetic transliterations. Examples: `inheritance`, `becoming`, `the-cane`, `eight-benefits` — not `part-1`, `ch01a`, `man-section-1`.
- Number derivatives monotonically with `ch##-<title>.txt`. Numbering is per-bucket, not per-source-chapter, so derivatives from one source span consecutive numbers.
- Make each derivative land inside the Default Deep Dive band (1,800–4,500 words). If a single seam would push one half outside the band, find a different seam.
- Record provenance in each derivative's contract via the `derived_from:` field — a repo-relative path to the original source chapter. This field is the canonical staleness signal.

### Lineage field

The contract schema includes a `derived_from:` field. When the field is set, the chapter is a derivative; the path identifies the original source. A future audit script can compare `derived_from` mtime to the derivative's mtime to detect staleness when the original is edited.

### Splitting is editorial, scaffolding stays deterministic

The skill chooses where to cut and what to title. That decision is editorial and may differ between runs. But once the split decision is made and committed as derivative `.txt` files, all downstream behavior — contract resolution, bundle scaffolding, episode build — remains fully deterministic.

## What this capability does NOT do

- It does not call the LLM. It does not author key passages, context, or beats.
- It does not ingest PDFs. Use Series Mode (Phase 0) for that.
- It does not modify the chapter file. The chapter at `chapters/ch##-<slug>.txt` is the source upload; nothing else mirrors it.
- It does not run `podcast-challenger`. Run that separately against the emitted bundle.
- It does not upload to NotebookLM. That step is always manual.
