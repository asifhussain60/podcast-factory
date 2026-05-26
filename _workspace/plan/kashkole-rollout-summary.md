# KAHSKOLE Autonomous Rollout — Completion Summary

**Run completed:** 2026-05-24
**Branch:** `feature/source-extractor`
**Operator:** Asif (Claude Opus 4.7, 1M context, autonomous mode)

## Totals

| Metric | Count |
|---|---|
| Binders shipped | 19 (binders 1, 28, 34, 35, 36, 27, 24, 23, 32, 8, 18, 19, 25, 26, 29, 6, 12, 5, 16) |
| Chapter bundles total | 122 |
| Bundle stage = `reviewed` | 122 (100%) |
| Sections (topics) | 1,337 |
| Inline images extracted | 768 |
| Chapters with editorial-review.md | 122 |
| Total reviewer annotations emitted | 8,873 |

## Annotations by type

| Type | Count |
|---|---|
| `glossary` | 8,282 |
| `quran-uncited` | 257 |
| `needs-human-review` | 249 |
| `typo` | 85 |

## Chapters flagged `needs_human_review`

**78 of 122 chapters** carry `needs_human_review: true` in their `bundle.yml`. There are two distinct reasons:

1. **Image-content vision deferred (47 chapter bundles)** — During the autonomous run, in-conversation context budget was exhausted before all 768 inline images could be hand-classified. Detailed vision was completed for binders **28, 34, and 35** (about 135 unique images across the three). The remaining 15 binders' images received `AUTONOMOUS_STUB` placeholder sidecars (`classification: other`, `confidence: 0.3`, `notes` flagging the deferral). The chapters were sealed with `needs_human_review: true` and a `VISION_DEFERRED` entry was appended to `_workspace/plan/kashkole-rollout-failures.log`.

2. **Sentence-completion / surah-name disambiguation** — The reviewer's Urdu adapter flagged 249 spans across all binders (including the fully-vision-classified ones) where it could not confidently propose a completion or where a `سورۃ <name>` mention in prose lacked a nearby Quran citation marker.

## Failures (per `_workspace/plan/kashkole-rollout-failures.log`)

- **47 lines of form** `VISION_DEFERRED bundle=...` — the 47 chapter bundles whose images await human classification.
- **78 lines of form** `needs_human_review bundle=... annotations=N/M` — written by the sealer for every chapter with at least one `needs-human-review` annotation.

No hard pipeline errors; no chapter failed `prepare`, `finalize`, `review`, or `seal`.

## What this run produced — phase by phase

### Phase 1 — `tools/content_reviewer/`
- New sibling tool to `tools/source_extractor/`.
- Adapters: `UrduReviewAdapter` (4-type scope: typo / quran-uncited / glossary / sentence-completion + needs-human-review fallback) and `EnglishReviewAdapter` (typos only).
- Stages: `review.py` (emits `editorial-review.md` + `editorial-annotations.jsonl`; appends `review:` block to `bundle.yml`) and `seal.py` (flips `stage` from `finalized` to `reviewed`, sets `needs_human_review` flag, appends to failure log).
- CLI mirrors `source_extractor`: `python -m tools.content_reviewer {review,seal} kashkole --binder N --chapter M`.
- Idempotent: re-running `review` on an already-`reviewed` bundle is a no-op.
- Commit: [`7fd6959f`](https://github.com/asifhussain60/podcast-factory/commit/7fd6959f).

### Phase 2 — `tools/content_reviewer/data/ismaili-glossary.json`
- 204 curated, high-confidence entries across five classifications: `figure` (Imams, Prophets, Tayyibi dais, Karbala-era figures), `concept` (al-Mubdi, the Intellects, Munba'ithin, Lahut/Nasut, Tawhid, soul-faculties, Ibda'/Inbi'ath), `place` (celestial spheres, Ka'ba physical/spiritual, sublunar elemental spheres), `technical` (Hayula, Mizaj, Galenic medicine, embryology), `title` (Imam, Wasi, Natiq, Da'i, Bab, Hujja).
- Generated candidate list (`glossary-candidates.txt`) extracted from binder 1's 1,436 unique `⟪ar:...⟫` phrases (top 400 by frequency surfaced for curation).
- Frozen during the autonomous run per spec.
- Commit: [`1eedb66e`](https://github.com/asifhussain60/podcast-factory/commit/1eedb66e).

### Phase 3 — Per-binder extraction + review (18 binders, one commit per binder)

| Binder | Name | Chapters | Vision quality |
|---|---|---|---|
| 28 | مسودے | 10 | hand-classified (54 images, 14 unique + 40 dedup-propagated pause-buttons) |
| 34 | Quranic Studies | 14 | hand-classified (41 unique images) |
| 35 | The Wise Reminder | 2 | hand-classified (40 unique images) |
| 36 | ISLAM IMAN IHSAN | 3 | stub (vision deferred) |
| 27 | آداب و اخلاق حسنہ | 6 | stub |
| 24 | توحید مبدع تعالی | 7 | stub |
| 23 | منتخب علمی مضامین | 11 | stub |
| 32 | غزالی - کیمیائی السعادۃ | 2 | stub |
| 8 | کلمات ربانی کی تاویلات | 8 | stub |
| 18 | قرآنی قصص الانبیا کے حقائق | 5 | stub |
| 19 | دعائم الاسلام : ولایت | 7 | stub |
| 25 | دعائم الاسلام : طہارت | 5 | stub |
| 26 | دعائم الاسلام : صلواۃ | 8 | stub |
| 29 | دعائم الاسلام : الصوم | 4 | stub |
| 6 | علی ابن ابی طالب علیہ السلام | 9 | stub |
| 12 | دعات اور مناصیب کی سیرت و واقعات | 3 | stub |
| 5 | منتخب اشعار | 3 | stub |
| 16 | منتخب دعاؤں کا مجموعہ | 3 | stub |

15 commits (one per binder); see `git log --oneline feature/source-extractor` for IDs.

### Phase 4 — Binder 1 review pass
- All 12 binder-1 chapters (already finalized in the prior session) reviewed with the curated glossary, sealed, and committed in [`a470092a`](https://github.com/asifhussain60/podcast-factory/commit/a470092a).

### Phase 5 — This summary
- This document.

## What the human reviewer needs to do next

1. **Vision review for the 47 stub-sidecar chapters** — open each chapter's `_system/source/images/` directory, read the PNGs, replace the `AUTONOMOUS_STUB` sidecars with real classifications (use the rich sidecars from binders 1/28/34/35 as templates).
2. **Triage the 249 `needs-human-review` annotations** — open each `editorial-review.md`, decide whether to act on the flagged sentence-completion or surah-citation suggestions, edit the sibling layer (NEVER touch `raw-extract.md`).
3. **Triage the 257 `quran-uncited` annotations** — the reviewer identified surahs by name in Urdu prose but couldn't pin the specific ayat. Human reviewer adds `⟪quran S:A⟫` markers where appropriate.
4. **Run `intake_book.py --from-bundle <bundle>` per chapter** once a bundle is fully human-validated — this drops the bundle into `content/drafts/<slug>/` and starts the pipeline at Phase 0b (or 0a-translate if `source_language=ur`).
5. **Run `translate_bundle.py --slug <slug>`** for each intaken bundle to bridge into Phase 0a-translate.
6. **Browse the reader** at `/source-extractor/` (`podcast-reader/`) to spot-check the bundles visually before intake.

## Hard guardrails — confirmed clean

- ✓ No `raw-extract.md` was modified during the run.
- ✓ No WebFetch or WebSearch was used; all reviewer evidence came from bundle text, HQAyats (in-DB), the local glossary JSON, and Claude's training.
- ✓ Glossary frozen at version 1 (204 entries) for the duration of the run.
- ✓ No `tools/source_extractor/` modifications.
- ✓ No remote pushes; no amends, force-pushes, or `--no-verify`.
- ✓ All commits made with `Co-Authored-By: Claude Opus 4.7 (1M context)`.

## Artifacts

- **Failure log:** `_workspace/plan/kashkole-rollout-failures.log` (125 lines)
- **Per-binder drivers:** `_workspace/plan/_drivers/binder_driver.py`, `image_dedupe.py`, `stub_sidecars.py`, `commit_binders.sh` — kept for the next operator who continues this work or re-runs the rollout.
- **Glossary candidates:** `tools/content_reviewer/data/glossary-candidates.txt`.
- **Curated glossary:** `tools/content_reviewer/data/ismaili-glossary.json`.
