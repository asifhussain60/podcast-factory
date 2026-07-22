# Capability Manifest — Reconciliation (2026-07-13)

**Base twin:** [`capability-manifest-2026-06-20.md`](capability-manifest-2026-06-20.md) (`develop @ af7f6a5`)
· **Structured manifest:** [`_workspace/plan/capabilities-manifest.yml`](../../_workspace/plan/capabilities-manifest.yml) (was `2026-06-14`, bumped to `2026-07-13`)
· **Reconciled to:** `develop @ d4cfbc92` · **Delta:** +82 commits
**Validation depth:** STATIC (import health, dependency resolution, full test suite, CI status). Runtime / integration / E2E remain spend-gated and out of scope, unchanged from the base twin.

> This is a point-in-time reconciliation, not a rewrite. It records what drifted since the 2026-06-20 snapshot and updates the risk register. The base twin remains valid for everything not called out here.

---

## 1. What changed since the base snapshot

82 commits landed on `develop` between `af7f6a5` (2026-06-20) and `d4cfbc92` (2026-07-13). The material code surface:

- **New:** `_translation_edition.py` (812L), `generate_translation_edition.py` (182L), `inject_chapter_arabic.py` (178L), `strip_reference_attribution_noise.py` (58L).
- **Materially grown:** `validate_book_ready.py` (+233L), `_rules.py` (+187L), `build_glossary.py` (+140L), `_book_illustrate.py` (+93L), `full_book_denoise.py` (+88L), `_authoring/_enrichment.py` (+81L).
- **New tests:** `test_translation_edition.py`, `test_validate_book_ready.py` (+308L), `test_book_illustrate_mindmap.py`, `test_reference_attribution_noise.py`, `test_denoise_contract.py`.

Neither base artifact covered the **translation-edition deliverable path** — a whole capability surface. It is now recorded as `surfaces.translation_edition` in the structured manifest.

## 2. Capability manifest — new/changed entries

| Capability | Entry point | Key files | Static status |
|---|---|---|---|
| Translation-edition orchestration | `generate_translation_edition` | `generate_translation_edition.py` | **Verified Working** (imports clean; 36 tests pass) |
| Translation compose (source-aligned, no augmentation) | `author_translation_edition_compose` | `_translation_edition.py` | Statically Sound |
| Translation config-contract gate | `assert_translation_contract` | `_translation_edition.py` | Statically Sound |
| Book-ready readiness gate | `validate_book` | `validate_book_ready.py` | Statically Sound |
| Source crosswalk | `build_source_crosswalk` | `_translation_edition.py`, `book/source-crosswalk.json` | Statically Sound |
| Reference-attribution denoise | `strip_reference_attribution_noise` | `strip_reference_attribution_noise.py` | Statically Sound (2 test modules) |
| Chapter Arabic injection | `inject_chapter_arabic` | `inject_chapter_arabic.py` | Statically Sound |
| Book-illustrate mindmap normalization | `_normalize_mindmap_dsl` | `_book_illustrate.py` | **Working With Risks** (R15) |

**Correction to any prior "digital twin" narrative:** a `2026-06-29` repo-surgeon-style report described an `evaluate_book_gate` / `gate_and_emit` / `_measure_prose_ratio` / `_ALLOWED_ARTIFACTS` "disk-read gate" with a first-emission P0. **Those symbols do not exist in the codebase.** The actual gating is the deterministic config contract plus a final `validate_book()`. That finding set was not reproducible and is void.

## 3. Verification report (2026-07-13)

- **Local full suite** (repo `.venv`, pytest 9.0.3): `1476 passed, 1 skipped, 1 failed` in ~13s.
- **CI** (`podcast-e2e`, ubuntu / py3.13 / requirements.txt only): `1475 passed, 10 skipped, 1 failed`.
- **The single failure — `test_book_illustrate_mindmap::test_normalized_mindmap_renders_single_root`:** the render script `render-mermaid.mjs` throws `ERR_MODULE_NOT_FOUND: playwright` and exits `1` when `plan-dashboard/node_modules` is absent; the test's skip guard only catches exit `3` (chromium binary missing), so it asserts instead of skipping. Not a product regression — a test-robustness defect.

## 4. Risk register — reconciled

| ID | Risk | Status @ 2026-07-13 | Evidence |
|---|---|---|---|
| **R15** *(new)* | Mindmap live-render test asserted (not skipped) when playwright pkg absent → **was the sole cause of red `develop` CI since 2026-06-24** (last green 2026-06-23) | **FIXED 2026-07-13** — class gated on playwright package; runtime skip on chromium/module-missing signals; suite now `1476 passed, 2 skipped, 0 failed` | test added `281aa5de` 2026-06-24; fix in `test_book_illustrate_mindmap.py` |
| **R16** *(new)* | Twin artifacts stale (`.yml` 2026-06-14, `.md` 2026-06-20); translation-edition surface uncovered | **CLOSED by this reconciliation** | `.yml` bumped to 2026-07-13 + new surface; this doc |
| R4 | `deliver_book._find_pdf` (titled-preferred) vs `export_distribution._find_pdf` (`book.pdf` only) diverged | **FIXED 2026-07-13** — `export_distribution` now imports the one shared `_find_pdf` from `deliver_book` (single source) | `export_distribution.py` import; verified `is` identity |
| R9 | `R_SERMON_VERBATIM` "defined, no enforcer" | **STALE — effectively CLOSED.** Enforcer exists and is wired: `check_chapter_set.py::check_sermon_integrity` (P9, called at line 687) flags a sermon dropped (P0), fragmented across >1 chapter (P0), or stubbed <150 words (P1). Residual is cosmetic only: findings use `check="P9"`, not the `R_SERMON_VERBATIM` constant (consistent with all other checks, which cite no rule constant). **No `assert_sermon_verbatim()` written — that would duplicate a working check.** | `check_chapter_set.py:557,687` |
| R13 | Web app + API routes: zero automated tests | **OPEN** | 0 test files under `plan-dashboard/` |
| R1–R3, R5–R8, R10–R12, R14 | (carried from base twin) | **Not re-verified this pass** — presumed open | see base twin §4 |

## 5. Gap analysis (delta)

- **Validation:** translation-edition surface is well unit-tested; the mindmap live-render path (R15) is the newest untrusted surface and is actively breaking CI.
- **Documentation:** closed for the translation-edition surface (this reconciliation). Base-twin risks R1–R14 remain the standing backlog.
- **Operational:** R15 (red CI) is the highest-priority operational finding — it masks any *new* regression because the signal is already red.

## 6. Honest scope (unchanged from base twin)

No runtime execution of spend-gated phases; no integration/E2E; no web-app build/render; numpy/PIL/chromium-dependent paths not exercised. See base twin §7.
