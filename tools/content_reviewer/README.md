# content_reviewer

Annotation-layer reviewer for source-extractor bundles. Sibling to
`tools/source_extractor/`; never modifies `raw-extract.md`.

## What it does

Walks a finalized bundle section by section and emits a sibling annotation
layer:

```
<bundle>/_system/source/text/
  editorial-review.md          ← human-readable per-section grouping
  editorial-annotations.jsonl  ← one JSON object per annotation
```

It also appends a `review:` block to `bundle.yml` with counts by type +
confidence, and `seal` switches `bundle.yml.stage` from `finalized` →
`reviewed`. If any annotation type is `needs-human-review`, the bundle gets a
top-level `needs_human_review: true` flag and a line is appended to
`_workspace/plan/kashkole-rollout-failures.log`.

## Annotation types

| Type | Adapter | Confidence | Source |
|---|---|---|---|
| `typo` | urdu, english | high | self |
| `quran-uncited` | urdu | medium | hqayats |
| `glossary` | urdu | from glossary entry | glossary |
| `sentence-completion` | urdu | high only | training, hqayats |
| `needs-human-review` | urdu, english | low | self |

Hard rule: if a completion is plausible but not high-confidence, emit
`needs-human-review` instead of guessing.

## Usage

```bash
# Review a finalized bundle. Adds editorial-* files and review: block.
python -m tools.content_reviewer review kashkole --binder 1 --chapter 73

# Seal: validate outputs, flip stage to "reviewed", flag needs_human_review.
python -m tools.content_reviewer seal kashkole --binder 1 --chapter 73
```

Both commands are idempotent. `review` is a no-op when stage is already
`reviewed`; `seal` simply re-stamps the stage line and re-evaluates the
needs-human-review flag.

## Glossary

`data/ismaili-glossary.json` is curated from binder 1 and **frozen** during
the autonomous rollout. New unknown terms emit `needs-human-review`; the
reviewer never auto-grows the glossary.

To rebuild the candidate list (does not modify the curated glossary):

```bash
python tools/content_reviewer/scripts/extract_candidates.py
```

## Independence

- No imports from `scripts/podcast/`.
- No external network or LLM calls.
- Reuses `tools.source_extractor.adapters.kashkole.KashkoleQuranCorpus` for
  HQAyats lookups (read-only).
- `bundle.yml.stage` transitions: `finalized` → `reviewed` (one direction).
