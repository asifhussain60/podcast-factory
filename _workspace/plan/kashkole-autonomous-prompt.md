# KAHSKOLE Autonomous Rollout Prompt

**Paste the body below (everything inside the `===` rulers) as the first message
in a fresh Claude Code session, working directory:
`/Users/ahmac/Code/podcast-factory`, branch: `feature/source-extractor`.**

The session will run autonomously for multiple hours, building a new tool,
bootstrapping a glossary, then extracting + reviewing 110 KAHSKOLE chapters.
It surfaces only when done.

================================================================================

# KAHSKOLE Autonomous Rollout — Operator Instructions

You are picking up multi-hour autonomous work in the **podcast-factory** repo
on branch **`feature/source-extractor`**. Before starting, READ in order:

1. [CLAUDE.md](CLAUDE.md) — repo conventions
2. [_workspace/plan/kashkole-rollout.md](_workspace/plan/kashkole-rollout.md) — full resume sheet, inventory, prior decisions
3. [tools/source_extractor/README.md](tools/source_extractor/README.md) — the extraction tool you'll use
4. [scripts/podcast/_branching.py](scripts/podcast/_branching.py) — branch-naming policy (don't need branches in this run, but useful context)

This prompt **overrides** the default cautious tool-use cadence. Work
continuously. Do not stop for confirmation between steps. Surface only when
finished, or on an unrecoverable error.

---

## Mission

Take KAHSKOLE binders 2 through 21 from "in the database" to "ready for
translation." Specifically:

1. Build a new `tools/content_reviewer/` tool (Phase 1 spec below).
2. Bootstrap `tools/content_reviewer/data/ismaili-glossary.json` from binder 1
   content (Phase 2 method below).
3. For each pending binder: extract every chapter → vision-classify every
   image → finalize → review (Phase 3 loop).
4. Apply the reviewer to binder 1 (id=1) too (Phase 4).
5. Surface ONLY when all done — or on unrecoverable error (Phase 5).

### Pending binders (in this order)

```
28  مسودے                          10 chapters
34  Quranic Studies                14
35  The Wise Reminder               2
36  ISLAM IMAN IHSAN                3
27  آداب و اخلاق حسنۃ                6
24  توحید مبدع تعالی                 7
23  منتخب علمی مضامین               11
32  غزالی - کیمیائی السعادۃ          2
 8  کلمات ربانی کی تاویلات           8
18  قرآنی قصص الانبیا کے حقائق       5
19  دعائم الاسلام : ولایت            7
25  دعائم الاسلام : طہارت            5
26  دعائم الاسلام : صلواۃ            8
29  دعائم الاسلام : الصوم            4
 6  علی ابن ابی طالب علیہ السلام     9
12  دعات اور مناصیب کی سیرت و واقعات 3
 5  منتخب اشعار                     3
16  منتخب دعاؤں کا مجموعۃ            3
```

(BinderID 30 and 31 are empty in the DB — skip them.)

Binder 1 (id=1) is already extracted; you only run the reviewer on it in
Phase 4.

---

## HARD GUARDRAILS — Read and internalize

These are non-negotiable. Violating any of them silently corrupts the
content corpus.

| Rule | Why |
|---|---|
| **Do not modify any `raw-extract.md`** | The bundle is the source of truth; corrections go in a sibling annotation layer. |
| **Do not use WebFetch / WebSearch** | The reviewer has zero live-web access. Knowledge = bundle text + HQAyats Quran corpus (in DB) + local glossary JSON + your own training. |
| **Do not auto-grow the glossary during the per-binder loop** | The glossary is curated in Phase 2 and FROZEN after. New unknown terms flag `needs_human_review`; you do not invent entries on the fly. |
| **Do not halt on chapter-level errors** | Log to `_workspace/plan/kashkole-rollout-failures.log`, mark chapter `needs_human_review` in its `bundle.yml`, continue. |
| **Do not skip the per-binder commit** | One commit per binder is the unit of resume. |
| **Do not modify `tools/source_extractor/`** | The content reviewer is a sibling tool. |
| **Do not push to remote** | Local commits only. Operator pushes manually after review. |
| **Do not amend, force-push, or use `--no-verify`** | Standard git hygiene. |

---

## Pre-flight (do this first)

```bash
# Verify branch
git branch --show-current   # must be feature/source-extractor
git status                  # must be clean

# Verify Docker SQL container is up
docker ps | grep kashkole-mssql   # must show "Up"

# Use the existing Phase 1 venv (has bs4, lxml, PyYAML)
VENV=_workspace/kashkole-ksessions/.venv/bin/python
$VENV --version   # should be 3.14
$VENV -c "from tools.source_extractor.db import query_json; print(len(query_json('KASHKOLE', 'SELECT 1 AS x FOR JSON PATH;')))"
# should print 1

# Create the failure log file if missing
touch _workspace/plan/kashkole-rollout-failures.log
```

If pre-flight fails, surface immediately with the failing command. Otherwise
proceed.

---

## Phase 1 — Build `tools/content_reviewer/`

Build a new sibling to `tools/source_extractor/`. The reviewer takes a
finalized bundle, walks it section by section, and emits an **annotation
layer** in the bundle's `_system/source/text/` directory. It does NOT modify
`raw-extract.md`. It marks `bundle.yml`'s `stage` field to `reviewed`.

### Directory layout

```
tools/content_reviewer/
├── __init__.py
├── __main__.py
├── README.md
├── cli.py
├── data/
│   └── ismaili-glossary.json     ← Phase 2 produces this
├── adapters/
│   ├── __init__.py
│   ├── base.py                    ← ReviewAdapter ABC
│   ├── urdu.py                    ← UrduReviewAdapter (full 4-type scope)
│   └── english.py                 ← EnglishReviewAdapter (typos only)
└── stages/
    ├── __init__.py
    ├── review.py                  ← walks bundle, emits annotations
    └── seal.py                    ← validates ready + stamps stage=reviewed
```

### Adapter interface (`adapters/base.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Annotation:
    section_id: int
    section_position: int
    type: str            # "typo" | "quran-uncited" | "glossary" | "sentence-completion" | "needs-human-review"
    confidence: str      # "high" | "medium" | "low"
    original_excerpt: str
    annotation: str
    rationale: str
    source: str          # "hqayats" | "glossary" | "training" | "self"

class ReviewAdapter(ABC):
    @property
    @abstractmethod
    def language(self) -> str: ...   # "ur" | "en"

    @abstractmethod
    def review_section(self, section_text: str, section_id: int, section_position: int,
                       label: str, glossary: dict, quran_corpus) -> list[Annotation]: ...
```

### UrduReviewAdapter scope (4 types)

In a single in-conversation pass over each section's text, look for and emit
annotations for:

1. **`type: "typo"`** — encoding junk, orphaned ZWNJ, half-formed ligatures,
   doubled punctuation, obvious OCR artifacts. High confidence only.
   `source: "self"`.
2. **`type: "quran-uncited"`** — if Urdu prose names a Quran verse (e.g.
   "سورۃ آل عمران میں اللہ فرماتے ہیں") but no `⟪quran X:Y⟫` citation marker
   is nearby in the same blockquote, look up the named verse in HQAyats via
   the adapter's `quran_corpus` and propose a citation.
   `confidence: "high"` only if the verse identification is unambiguous.
   `source: "hqayats"`.
3. **`type: "glossary"`** — proper-noun match against the local glossary
   JSON. Emit one annotation per first occurrence of a glossary term per
   section. `source: "glossary"`.
4. **`type: "sentence-completion"`** — only when:
   - A sentence is grammatically truncated (ends mid-clause, no terminal
     punctuation, followed by a heading or section marker), AND
   - The completion is obvious from immediate context (e.g. cut-off Quranic
     continuation matchable in HQAyats, or a well-known formula like "صلی
     اللہ علیہ وآلہ وسلم"), AND
   - `confidence: "high"` only.

   If completion is plausible but not high-confidence, emit
   `type: "needs-human-review"` instead.
   `source: "training" | "hqayats"`.

Everything else — unclear meaning, factual ambiguity, missing context —
emit `type: "needs-human-review"` with a short note. Do not attempt to fill.

### EnglishReviewAdapter scope (typos only)

Only `type: "typo"` annotations for KSESSIONS-style English content. Skip
glossary and sentence-completion. No-op on uncited Quran (English prose
doesn't have the same pattern).

### `stages/review.py` behavior

```
For a given (binder_id, chapter_id):
  1. Read bundle.yml. Verify stage == "finalized". If "reviewed", skip (idempotent).
  2. Read raw-extract.md. Split by section markers (the `<!-- section N (id=X, raw_sort=Y): label -->` comments).
  3. Load glossary from tools/content_reviewer/data/ismaili-glossary.json.
  4. For each section, instantiate KashkoleQuranCorpus from tools/source_extractor/adapters/kashkole.py, pass into adapter.
  5. Adapter returns list[Annotation] per section.
  6. Write:
     - _system/source/text/editorial-review.md — human-readable per-section grouping
     - _system/source/text/editorial-annotations.jsonl — one JSON line per annotation
  7. Append a `review:` block to bundle.yml with counts by type + confidence.
  8. DO NOT touch raw-extract.md.
```

### `stages/seal.py` behavior

```
For a given (binder_id, chapter_id):
  1. Verify editorial-review.md + editorial-annotations.jsonl exist.
  2. Verify review counts in bundle.yml.
  3. Switch bundle.yml stage from "finalized" to "reviewed".
  4. If any annotation has type="needs-human-review", also write a flag at
     bundle.yml under `needs_human_review: true` and append a line to the
     failure log noting the chapter + count.
```

### CLI (`cli.py`)

```bash
python -m tools.content_reviewer review kashkole --binder N --chapter M
python -m tools.content_reviewer review ksessions --binder N --chapter M
python -m tools.content_reviewer seal kashkole --binder N --chapter M
```

Smoke-test on binder 1 chapter 73 (`tashkeel-aalam-ruhani`, already
finalized in the prior session). Verify outputs exist and `bundle.yml` is
updated. Commit Phase 1:

```bash
git add tools/content_reviewer/
git commit -m "feat(content-reviewer): annotation-layer reviewer tool (autonomous Phase 1)"
```

---

## Phase 2 — Bootstrap the Ismaili glossary

Write a one-shot script `tools/content_reviewer/scripts/extract_candidates.py`
(or do it inline) that:

1. Reads every binder 1 raw-extract.md file.
2. Extracts the content of every `⟪ar:…⟫` marker.
3. Dedupes and counts frequency.
4. Sorts by frequency descending.
5. Writes top ~200 candidates to `tools/content_reviewer/data/glossary-candidates.txt`.

Then, **based on Claude's general training and the candidate frequencies**,
draft `tools/content_reviewer/data/ismaili-glossary.json` with entries in
this shape:

```json
{
  "version": 1,
  "generated_at": "<ISO timestamp>",
  "policy": "curated from binder 1; frozen during autonomous run",
  "terms": [
    {
      "term": "منبعثین",
      "transliteration": "Munbathin",
      "english": "Emanators / Those who emerge together",
      "classification": "concept",
      "definition_ur": "وہ دو وجود جو عقل اول کے بعد ایک ساتھ نکلے",
      "definition_en": "The two beings who emerged together after the First Intellect, denoting the second and third Intellects in the Ismaili emanationist scheme.",
      "source_authority": "Ismaili philosophical tradition; Kirmani's Rahat al-Aql",
      "confidence": "high"
    }
  ]
}
```

**Curation rules**:
- Only include terms you are highly confident about. Skip any term that's a
  Quranic verse fragment, a non-name common word, or anything ambiguous.
- Classification ∈ {"figure", "concept", "place", "technical", "title"}.
- `confidence: "high"` only when the definition would not change across
  any reasonable Ismaili authority.
- Aim for ~100–200 high-quality entries. Quality over quantity.

Commit Phase 2:

```bash
git add tools/content_reviewer/data/
git commit -m "feat(content-reviewer): bootstrap Ismaili glossary from binder 1 (autonomous Phase 2)"
```

---

## Phase 3 — Per-binder extraction + review loop

For each binder ID in the pending list above (in the listed order), do:

### Per-binder loop body

```bash
BINDER_ID=<id>
BINDER_NAME=<name from inventory>

# 3a. Survey chapters
$VENV -c "
from tools.source_extractor.db import query_json
ids = query_json('KASHKOLE', f'''
SELECT bc.ChapterID AS id, c.ChapterName AS name
FROM BinderChapters bc JOIN Chapters c ON c.ChapterID = bc.ChapterID
WHERE bc.BinderID = {BINDER_ID} ORDER BY bc.BinderChapterOrder FOR JSON PATH;''')
for r in ids: print(r['id'], r['name'])"

# 3b. For each chapter:
for CH in <chapter_ids>; do
  $VENV -m tools.source_extractor prepare kashkole --binder $BINDER_ID --chapter $CH || {
    echo "prepare failed binder=$BINDER_ID chapter=$CH" >> _workspace/plan/kashkole-rollout-failures.log
    continue
  }

  # 3c. Vision pass — Claude (you) reads each image in the bundle's
  # _system/source/images/ directory and writes a sibling NNN.json sidecar.
  # Follow the schema in vision-tasks.json. Use the same classifications
  # already established in binder 1.

  $VENV -m tools.source_extractor finalize kashkole --binder $BINDER_ID --chapter $CH || {
    echo "finalize failed binder=$BINDER_ID chapter=$CH" >> _workspace/plan/kashkole-rollout-failures.log
    continue
  }

  $VENV -m tools.content_reviewer review kashkole --binder $BINDER_ID --chapter $CH || {
    echo "review failed binder=$BINDER_ID chapter=$CH" >> _workspace/plan/kashkole-rollout-failures.log
    continue
  }

  $VENV -m tools.content_reviewer seal kashkole --binder $BINDER_ID --chapter $CH || {
    echo "seal failed binder=$BINDER_ID chapter=$CH" >> _workspace/plan/kashkole-rollout-failures.log
    continue
  }
done

# 3d. Commit the binder
git add _workspace/kashkole-ksessions/extracted/kashkole/
git commit -m "feat(kashkole): binder $BINDER_ID — $BINDER_NAME (autonomous run)"
```

### Vision-pass guidance

For each image you read, write a JSON sidecar with this schema (same as
binder 1 — match the style of those sidecars):

```json
{
  "classification": "teaching-diagram|quran-verse|hadith|poem-or-saying|mixed|other",
  "arabic_text": "all Arabic visible in the image, multiline",
  "urdu_text": "all Urdu visible if any",
  "english_text": "all English visible if any",
  "suggested_citation": { "surah": N, "ayat": M } | null,
  "alt_text": "1–3 sentence description of what the image shows",
  "confidence": 0.0–1.0,
  "notes": "anything pedagogically important"
}
```

For Quran-verse images, look up `(surah, ayat)` against HQAyats and use
that as the suggested_citation. For teaching-diagrams, focus on what
relationships/hierarchies the diagram conveys.

Move to the next binder after the commit. Do not pause.

---

## Phase 4 — Apply reviewer to binder 1

Binder 1 was extracted before the reviewer existed. Once Phases 2–3 are
complete, run the reviewer on binder 1's 12 chapters:

```bash
for CH in 73 74 125 75 76 78 80 84 81 82 20 21; do
  $VENV -m tools.content_reviewer review kashkole --binder 1 --chapter $CH
  $VENV -m tools.content_reviewer seal kashkole --binder 1 --chapter $CH
done

git add _workspace/kashkole-ksessions/extracted/kashkole/07-uloom-mabda-wa-maad/
git commit -m "feat(kashkole): binder 1 review pass (autonomous Phase 4)"
```

---

## Phase 5 — Surface

Write a summary to `_workspace/plan/kashkole-rollout-summary.md`:

```markdown
# KAHSKOLE Autonomous Rollout — Completion Summary

**Run completed:** <ISO timestamp>
**Branch:** feature/source-extractor

## Totals
- Binders shipped: <N>
- Chapters extracted: <M>
- Topics: <T>
- Inline images classified: <I>
- Annotations emitted: <A>
  - typo: <count>
  - quran-uncited: <count>
  - glossary: <count>
  - sentence-completion (high-confidence): <count>
  - needs-human-review: <count>
- Chapters flagged needs_human_review: <count>

## Failures (if any)
See `_workspace/plan/kashkole-rollout-failures.log`.

## Next steps (for operator)
1. Review chapters flagged `needs_human_review`.
2. Run `intake_book.py --from-bundle <bundle-path>` for each reviewed bundle.
3. Run `translate_bundle.py --slug <slug>` for translation to English.
4. Browse the reader at `/source-extractor/` to spot-check.
```

Then commit:

```bash
git add _workspace/plan/kashkole-rollout-summary.md _workspace/plan/kashkole-rollout-failures.log
git commit -m "docs(kashkole): autonomous rollout completion summary"
```

**Then and only then**, surface to the operator with a one-paragraph message
pointing to the summary file.

---

## Resume mechanics

This prompt is **idempotent**. If interrupted at any point:

- Re-running it from the start is safe. The pre-flight, tool-build, and
  glossary steps check existence and skip if already done.
- The per-binder loop checks `bundle.yml.stage` before each operation:
  - stage missing → run `prepare`
  - stage == "prepared" → run vision + `finalize`
  - stage == "finalized" → run `review` + `seal`
  - stage == "reviewed" → skip chapter entirely
- Resume granularity = chapter (within binder) → binder commit.

If `_workspace/plan/kashkole-rollout-failures.log` contains entries for the
current binder, do NOT retry them automatically. Skip them. Operator will
review failures after the run.

---

## Surface conditions

Surface to the operator (with a single short message) ONLY when:

1. **Pre-flight fails** — branch wrong, DB down, venv broken, etc.
2. **Phase 1 build fails** — tool can't be smoke-tested on binder 1 chapter 73.
3. **Glossary bootstrap fails** — can't extract candidates or produce a valid JSON.
4. **An unrecoverable error occurs** — disk full, git broken, irreversible state.
5. **All phases complete** — full summary as in Phase 5.

Do NOT surface for individual chapter failures. Those go to the log.

---

Begin.
