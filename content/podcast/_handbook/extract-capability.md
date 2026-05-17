# Extract capability — one chapter → one NotebookLM bundle

The `/podcast` skill exposes a single deterministic capability for the common case (one chapter, one episode). It coexists with the Series Mode (Phase 0 of `SKILL.md`) and shares the same output layout.

## When to use which mode

| Mode | When | Entry point |
|---|---|---|
| **Extract Mode** (this doc) | One chapter, already authored, ready to bundle | `scripts/podcast/extract_chapter.py` |
| **Series Mode** (`SKILL.md` §1.5) | Multi-chapter PDF or book that needs to be ingested, segmented, and enriched | `/podcast` skill conversation, Phase 0 |

Extract Mode does **not** ingest, distill, or enrich. It assumes the chapter file already exists in a published form. It is the right answer for memoir chapters and for re-extracting any single chapter from an already-enriched book.

## Command

```
python3 scripts/podcast/extract_chapter.py <chapter-ref>
python3 scripts/podcast/extract_chapter.py <chapter-ref> --contract <path>
python3 scripts/podcast/extract_chapter.py <chapter-ref> --force
```

## Chapter ref resolution

The first match wins:

| Order | Resolution | Example |
|---|---|---|
| 1 | Literal path (absolute or repo-relative) | `content/babu-memoir/chapters/ch01-man.txt` |
| 2 | `content/babu-memoir/chapters/<ref>.txt` | `ch01-man` |
| 3 | `content/podcast/*/chapters/<ref>.txt` | `ch02-hatim-eight-benefits` |

A missing chapter is a hard error — the extractor refuses to invent one.

## Contract resolution

| Order | Resolution |
|---|---|
| 1 | `--contract <path>` (explicit) |
| 2 | `content/podcast/<source-bucket>/chapter-contracts/<chapter-slug>.yml` |
| 3 | A stub is written to location (2) with `[TODO]` markers; re-run with `--force` after editing |

The full schema lives in `chapter-contract.template.yml`. The contract is the I/O surface — everything the extractor needs is in it. The extractor never invents fields.

## Output layout (per `source_type`)

```
content/podcast/<bucket>/
├── chapters/ch##-<slug>.txt                       ← chapter copy (SOURCE upload)
├── chapter-contracts/<slug>.yml                   ← the signed contract
├── _system/episode-drafts/EP##-<slug>/
│   ├── 00-framing.md         ← CUSTOMIZE PROMPT (downstream: build_episode_txt.py)
│   ├── 01-source-primary.md  ← mirror of chapter (the refinement target)
│   ├── 02-key-passages.md    ← scaffold; LLM-SELECT downstream
│   ├── 03-context-pack.md    ← scaffold; LLM-FILL downstream
│   ├── 04-discussion-spine.md ← N beats per length_target; LLM-FILL downstream
│   └── 99-show-notes.md      ← from contract.show_notes
```

`<bucket>` is `babu-memoir` for memoir chapters, or `<book_slug>` for book chapters.

Downstream, `build_episode_txt.py <bucket-root> EP##-<slug>` emits the final `episodes/EP##-<slug>.txt` (the customize-prompt-only file pasted into NotebookLM's Customize box).

## Determinism guarantee

Same chapter file + same contract → byte-identical bundle scaffolding. There are no timestamps, no random ordering, no environment-dependent paths in any emitted file. Slots that require downstream LLM authoring are marked with `[LLM-SELECT]`, `[LLM-FILL]`, or `[TODO]` — these are the only fields where content can drift between runs.

The extractor refuses to overwrite a file that has changed unless `--force` is passed.

## Boundary (SKILL.md §9 v2)

Extract Mode is the **only** part of the podcast skill that may read memoir paths. The adapter inside `extract_chapter.py` enforces this via `PROHIBITED_PATH_PREFIXES`:

| Sanctioned | Prohibited |
|---|---|
| `content/babu-memoir/chapters/*.txt` | `content/babu-memoir/reference/**` |
| `content/podcast/**` | `content/babu-memoir/_system/**` |
| | `content/babu-memoir/scratchpad/**` |
| | Any path matching `voice-fingerprint*` or `master-context*` |

A read that resolves into a prohibited path exits with `BOUNDARY VIOLATION` and a non-zero code. This is the contract that lets the podcast skill touch memoir without inheriting memoir authoring responsibilities.

## Worked example — memoir chapter

```
$ python3 scripts/podcast/extract_chapter.py ch01-man
NOTE: no contract found — wrote stub at content/podcast/babu-memoir/chapter-contracts/man.yml. Edit it and re-run with --force.

# Edit the stub: fill audience, key_tensions, tone_constraints, title.

$ python3 scripts/podcast/extract_chapter.py ch01-man --force
Extracted EP01-man from ch01-man.txt
  Source bucket: babu-memoir
  Episode draft: content/podcast/babu-memoir/_system/episode-drafts/EP01-man
  Files written: 7
  Files unchanged: 0

Next: build the customize-prompt episode txt:
  python3 scripts/podcast/build_episode_txt.py content/podcast/babu-memoir EP01-man
```

## Worked example — re-extract a book chapter

```
$ python3 scripts/podcast/extract_chapter.py ch02-hatim-eight-benefits
# (contract already exists from prior run; bundle re-rendered deterministically)
Extracted EP02-hatim-eight-benefits from ch02-hatim-eight-benefits.txt
  Source bucket: ayyuhal-walad
  Files unchanged: 7
```

Re-running with no contract change is a no-op. This is the idempotency promise.

## Splitting policy (standing rule)

A source chapter that exceeds the NotebookLM word band must be split into derivative chapters in the podcast bucket. The original source chapter is never modified.

### Trigger

| Source word count | Action |
|---|---|
| ≤ 4,500 words | Single derivative; ship as-is |
| 4,500 – 5,500 words | Single derivative; set `length_target: longer` in the contract |
| > 5,500 words | **Split required** — `build_episode_txt.py` refuses anything over 5,500 (canon: `notebooklm-best-practices.md` §3) |

The extractor warns at extract time when any of these thresholds are crossed. Splitting decisions are authorized to be made autonomously by the skill — no per-chapter confirmation needed. The skill must:

- Place each derivative inside `content/podcast/<bucket>/chapters/` as a plain `.txt` file.
- Title each derivative with a `kebab-case`, single-noun or short-noun-phrase, clean English title that reflects the content. No version suffixes, no date stamps, no Arabic phonetic transliterations. Examples: `inheritance`, `becoming`, `the-cane`, `eight-benefits` — not `part-1`, `ch01a`, `man-section-1`.
- Number derivatives monotonically with `ch##-<title>.txt`. Numbering is per-bucket, not per-source-chapter, so derivatives from one source span consecutive numbers.
- Make each derivative land inside the Default Deep Dive band (1,800–4,500 words). If a single seam would push one half outside the band, find a different seam.
- Record provenance in each derivative's contract via the `derived_from:` field — a repo-relative path to the original source chapter. This field is the canonical staleness signal.

### Lineage field

The contract schema includes a `derived_from:` field. When the field is set, the chapter is a derivative; the path identifies the original source. A future audit script can compare `derived_from` mtime to the derivative's mtime to detect staleness when the original is edited.

### Splitting is editorial, scaffolding stays deterministic

The skill chooses where to cut and what to title. That decision is editorial and may differ between runs. But once the split decision is made and committed as derivative `.txt` files, all downstream behavior — contract resolution, bundle scaffolding, episode build — remains fully deterministic.

### Worked example — over-length memoir chapter

Source: `content/babu-memoir/chapters/ch01-man.txt` (6,576 words — over 5,500, split required).

Derivatives in `content/podcast/babu-memoir/chapters/`:

| Derivative | Word count | Content arc |
|---|---|---|
| `ch01-inheritance.txt` | ~3,500 | The parents, the brother, what was given — through "still figuring it out the hard way" |
| `ch02-becoming.txt` | ~3,100 | Nadeem, Ishrat, Erum, the imagined letter, the inward gap — closing on "now I know where to look" |

Each derivative has its own contract (`inheritance.yml`, `becoming.yml`) with `derived_from: content/babu-memoir/chapters/ch01-man.txt`.

## What this capability does NOT do

- It does not call the LLM. It does not author key passages, context, or beats.
- It does not ingest PDFs. Use Series Mode (Phase 0) for that.
- It does not modify the chapter file. The chapter is verbatim in `01-source-primary.md` and verbatim in `chapters/ch##-<slug>.txt`.
- It does not run `podcast-challenger`. Run that separately against the emitted bundle.
- It does not upload to NotebookLM. That step is always manual.
