# KAHSKOLE rollout — pending work resume sheet

**Last updated:** 2026-05-24
**Branch:** `feature/source-extractor`
**Status:** binder 1 (of 21) fully shipped; binders 2–21 pending.

This is the resume sheet for continuing the KAHSKOLE → podcast-pipeline pipeline
across the remaining binders. The infrastructure (tool + bundle contract +
intake + translation + reader review view) is all built. What's left is purely
**vision work** (in-conversation classification of inline images) and the
mechanical prepare/finalize/intake/translate per chapter.

---

## What's done

Five-phase build, all shipped on `feature/source-extractor`:

| Commit | Phase | What |
|---|---|---|
| [32cf566](https://github.com/asifhussain60/podcast-factory/commit/32cf566) | A | `tools/source_extractor/` + adapter seam |
| [73655b0](https://github.com/asifhussain60/podcast-factory/commit/73655b0) | B | BOOK_DIR bundle shape |
| [09ca9ba](https://github.com/asifhussain60/podcast-factory/commit/09ca9ba) | D | `intake_book.py --from-bundle` |
| [9aa1852](https://github.com/asifhussain60/podcast-factory/commit/9aa1852) | E | `translate_bundle.py` (Phase 0a-translate bridge) |
| [f67e6b1](https://github.com/asifhussain60/podcast-factory/commit/f67e6b1) | C | Binder 1 — 12 BOOK_DIR bundles + URDU_STEM_MAP fix |
| [49b68c8](https://github.com/asifhussain60/podcast-factory/commit/49b68c8) | — | podcast-reader `/source-extractor/` review view |

**Binder 1 (id=1, علوم مبدا و معاد) is the only fully-shipped binder.** 12 chapters,
162 topics, 73 inline images classified, 109 curated citations validated.

---

## Inventory — full KAHSKOLE binder set

|  # | BinderID | Binder name                            | Chapters | Topics |
|----|----------|----------------------------------------|----------|--------|
|    |       28 | مسودے                                  |       10 |     75 |
|    |       34 | Quranic Studies                        |       14 |     84 |
|    |       35 | The Wise Reminder                      |        2 |     18 |
|    |       36 | ISLAM IMAN IHSAN                       |        3 |     24 |
|    |       27 | آداب و اخلاق حسنۃ                      |        6 |     40 |
|    |       24 | توحید مبدع تعالی                       |        7 |     79 |
|  ✓ |        1 | علوم مبدا و معاد                       |       12 |    162 |
|    |       23 | منتخب علمی مضامین                      |       11 |    214 |
|    |       32 | غزالی - کیمیائی السعادۃ                |        2 |     15 |
|    |        8 | کلمات ربانی کی تاویلات                 |        8 |    138 |
|    |       18 | قرآنی قصص الانبیا کے حقائق             |        5 |     26 |
|    |       19 | دعائم الاسلام : ولایت                  |        7 |     87 |
|    |       25 | دعائم الاسلام : طہارت                  |        5 |     42 |
|    |       26 | دعائم الاسلام : صلواۃ                  |        8 |     75 |
|  — |       31 | دعائم الاسلام : زکواۃ                  |        0 |      0 |
|    |       29 | دعائم الاسلام : الصوم                  |        4 |     43 |
|  — |       30 | دعائم الاسلام : الحج                   |        0 |      0 |
|    |        6 | علی ابن ابی طالب علیہ السلام           |        9 |    170 |
|    |       12 | دعات اور مناصیب کی سیرت و واقعات       |        3 |      7 |
|    |        5 | منتخب اشعار                            |        3 |     24 |
|    |       16 | منتخب دعاؤں کا مجموعۃ                  |        3 |     14 |

Key: ✓ done, — empty (skip), blank = pending.

**Totals across pending binders**: 110 chapters, ~1175 topics, ~**500–600 inline
images** (estimate — binder 1 had 0.45 images/topic; bigger binders may differ).

---

## Hours estimate

Roughly: **6–12 hours of focused image-reading time**, plus a few hours of
script time for prepare/finalize/intake/translate runs.

Best done in **binder-sized sessions** — process one full binder per session,
commit at the end, sleep, repeat. The reader view at `/source-extractor/`
makes progress visible.

---

## Resume procedure

When ready to continue, follow this exact sequence per binder. (Adjust
`BINDER_ID` and `CHAPTERS` for the binder you're tackling.)

### 0. Pre-flight

```bash
# Confirm we're on the branch
git checkout feature/source-extractor
git pull  # if remote is ahead

# Confirm Docker SQL container is up
docker ps | grep kashkole-mssql  # should show "Up"

# Use the Phase 1 venv (has bs4, lxml, PyYAML)
VENV=_workspace/kashkole-ksessions/.venv/bin/python
```

### 1. Survey the binder

```bash
$VENV -c "
from tools.source_extractor.db import query_json
binder_id = <BINDER_ID>
chaps = query_json('KASHKOLE', f'''
SELECT bc.BinderChapterOrder AS ord, c.ChapterID AS id, c.ChapterName AS name
FROM BinderChapters bc JOIN Chapters c ON c.ChapterID = bc.ChapterID
WHERE bc.BinderID = {binder_id} ORDER BY bc.BinderChapterOrder FOR JSON PATH;''')
for c in chaps:
    print(f'  #{c[\"ord\"]:02d}  id={c[\"id\"]:>4}  {c[\"name\"]}')"
```

### 2. Bulk-prepare every chapter

```bash
$VENV -m tools.source_extractor prepare kashkole --binder <BINDER_ID> --chapter <CHAPTER_ID>
# Repeat per chapter; or scripted:
for ch in <CH1> <CH2> ...; do
  $VENV -m tools.source_extractor prepare kashkole --binder <BINDER_ID> --chapter $ch
done
```

### 3. Vision pass (in-conversation Claude)

Open Claude Code, ask: **"Process the vision tasks for binder N. Read each
image, write the sidecar JSONs."**

Claude will Read each PNG under `_workspace/kashkole-ksessions/extracted/kashkole/<NN-shelf>/<NN-book>/_system/source/images/NNN.png`
and Write a sibling `NNN.json` with `{classification, arabic_text, urdu_text,
english_text, suggested_citation, alt_text, confidence, notes}`.

### 4. Finalize each chapter

```bash
for ch in <CH1> <CH2> ...; do
  $VENV -m tools.source_extractor finalize kashkole --binder <BINDER_ID> --chapter $ch
done
```

### 5. (Optional) End-to-end into the pipeline

```bash
# For each finalized bundle:
BUNDLE=_workspace/kashkole-ksessions/extracted/kashkole/<NN-shelf>/<NN-book>
python3 scripts/podcast/intake_book.py --from-bundle "$BUNDLE" --no-branch
python3 scripts/podcast/translate_bundle.py --slug <suggested-slug-from-bundle.yml>
```

Each translate run costs **~$0.20–2** in Azure depending on chapter size.

### 6. Commit + push

```bash
git add _workspace/kashkole-ksessions/extracted/kashkole/<NN-shelf>/
git commit -m "feat(kashkole): binder N bundles (<binder-name>)"
git push origin feature/source-extractor
```

### 7. Review in the reader

```bash
cd podcast-reader
PODCAST_FACTORY_ROOT=/Users/ahmac/Code/podcast-factory npm run dev
# → http://localhost:4321/source-extractor/
```

---

## Decisions locked

These are baked into the tool / branch — do not re-litigate without cause:

- **Architecture**: Independent tool at `tools/source_extractor/` with
  `SourceAdapter` seam. KAHSKOLE adapter is full; KSESSIONS is a stub.
- **Output**: BOOK_DIR bundle (`<extract>/<source>/<NN-shelf>/<NN-book>/`)
  with `bundle.yml`, `_system/source/` per the schema in
  [tools/source_extractor/bundle.py](../../tools/source_extractor/bundle.py).
- **Translation**: Lives in the pipeline as `Phase 0a-translate`, bridged by
  [scripts/podcast/translate_bundle.py](../../scripts/podcast/translate_bundle.py)
  until the orchestrator integrates it natively.
- **Vision**: In-conversation Claude reads PNGs via the Read tool and writes
  sidecar JSONs. NO external Anthropic API calls (matches repo invariant).
- **Provenance**: `_provenance.json` uses `podcast.ingest-source/v1` schema
  with `source.kind: "sql"` discriminator.
- **Scope unit**: Each KAHSKOLE *chapter* = one podcast-pipeline *book*.
  Binders are the *shelf* level (not books). Topics within a chapter become
  the source's section list.

---

## Known edge cases (handled, just FYI)

1. **Quran-verse images** — some chapters paste Quran widgets as inline PNGs
   instead of HTML widget tables. Classify as `"quran-verse"` with
   `suggested_citation: {surah, ayat}`.
2. **Duplicate images** — chapter 12 of binder 1 had the same diagram embedded
   twice and the same Quran widget three times. Faithfully extract all; dedup
   is a Phase 0b refine task.
3. **Decorative-only images** — e.g. binder 1 chapter 07 image 002 (Helix
   Nebula photo, no text). Classify as `"other"` with no Arabic/Urdu fields.
4. **Slugify fingerprints** — if a chapter slug contains `x####` placeholders,
   add the missing Urdu stem to `URDU_STEM_MAP` in
   [tools/source_extractor/slugify.py](../../tools/source_extractor/slugify.py)
   and regenerate the affected chapters. Common particles already added in
   the Phase C commit: `کی`, `کا`, `ان`, `اس`, `وہ`, `یہ`, `ہے`, `ہیں`, `سے`,
   `تک`, `نے`, `پر`, `کو`, `میں`.

---

## What was cleaned up to save state

- Two partial bundle directories left over from a cancelled bulk-prepare loop:
  - `extracted/kashkole/18-ali-ibn-abi-talib-alayhi-as-salam/`
  - `extracted/kashkole/20-muntakhab-ashaar/`

  Both had `stage: prepared` only (no vision sidecars, no finalize). Deleted to
  avoid confusing future sessions — re-running prepare for those binders is
  cheap (a few seconds) and idempotent. Their content is reproducible from the
  SQL DB at any time.

---

## Open questions for resume

- **PR strategy** — keep stacking on `feature/source-extractor` until all
  binders ship, or open a draft PR now and merge incrementally? Default
  recommendation: open draft PR after binder 2 ships (validates the workflow
  on a second binder before going wider).
- **KSESSIONS** — the other SQL dump (mostly English content). Adapter is a
  stub. Tackle after KAHSKOLE binders ship.
- **Phase 1 flat-layout proof retirement** — the old
  `extracted/kashkole/07-uloom-mabda-wa-maad/03-munbathin.md` and
  `03-munbathin-images/` are still tracked alongside the new BOOK_DIR. Safe
  to delete in a follow-up cleanup commit.
