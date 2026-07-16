# Book Pipeline v2 — knob-matrix validation: cross-machine continuation

**Written 2026-07-16 on the desktop; read this on the MacBook Air to continue.**
Everything needed is in the repo (this directory is tracked) — a `git pull` on
the laptop gives you this doc, the portable cell runner, and the auto-layout
helper. Session-local context (the working plan file, cell logs, result
snapshots) stays on the desktop; the durable state below is authoritative.

## What this is

Phase 4 of the PDF-route consolidation (see `_workspace/plan/book-pipeline-cutover.md`):
validate the v2 unified book pipeline across the knob matrix
`{book_augmentation: none|source_only} × {book_voice: faithful|author_companion}`
before flipping the default ON and deleting the legacy compose paths.

## State at handoff (2026-07-16)

| Cell | Book | aug | voice | Status |
|---|---|---|---|---|
| c5 | the-master-and-the-disciple | none | faithful | **DONE — rendered (114pp A4, 15 visuals); challenger verdicts recorded in the cell commit message / matrix below** |
| c6 | the-master-and-the-disciple | source_only | faithful | **NEXT — run on the laptop** |
| c7 | the-master-and-the-disciple | none | author_companion | queued |
| c8 | the-master-and-the-disciple | source_only | author_companion | queued |
| c1–c4 | mukhtasar-ul-asar-2 | (all) | (all) | **ON HOLD per Asif ("focus only on M&D for now")** — do not run without his say-so |

- Branch `Islamic/the-master-and-the-disciple` (pushed): fast-forwarded to
  `develop`@`bc2b2cac`, then carries the per-phase pipeline commits + the c5
  cell commit. `book/_chunks/translation/` (the per-chapter compose checkpoint,
  normally gitignored) is force-added in a convenience commit so the laptop
  reuses it — **cells c6–c8 skip the expensive base recompose**. Remove that
  commit's files from tracking after the matrix (they're build cache).
- Branch `Islamic/mukhtasar-ul-asar-2` (pushed): c1 pause state (knobs stamped,
  `slide-decks/book.SKIP` authorized by Asif, partial compose). Its chunk cache
  was NOT pushed (killed mid-run; 15 chunks, desktop-only) — a resume there
  recomposes what's missing.
- Maintenance branch `chore/pdf-route-consolidation-and-site-validation`
  (pushed): Phases 1–3, site fixes, DR-013 wording restored (Asif authorized
  the PDF re-runs but declined a DR-013 doc exemption — this file is the record
  of that one-time authorization).

## Laptop bootstrap (once)

```bash
git clone git@github.com:asifhussain60/podcast-factory.git && cd podcast-factory   # or git pull
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pip install Pillow google-genai        # matrix extras (not in requirements.txt)
az login                                          # Key Vault: podcast-factory-vault
claude -p "pong"                                  # verify Max OAuth; else: claude login
git worktree add ../podcast-factory-worktrees/the-master-and-the-disciple Islamic/the-master-and-the-disciple
```

## Run the remaining cells (sequential, ~1–3h each; $0 — flat-rate `claude -p`)

```bash
BOOK_DIR=../podcast-factory-worktrees/the-master-and-the-disciple/content/Islamic/the-master-and-the-disciple
bash _workspace/plan/v2-matrix/run_cell.sh "$BOOK_DIR" source_only faithful          mad-c6-sourceonly-faithful  full
bash _workspace/plan/v2-matrix/run_cell.sh "$BOOK_DIR" none        author_companion mad-c7-none-companion       full
bash _workspace/plan/v2-matrix/run_cell.sh "$BOOK_DIR" source_only author_companion mad-c8-sourceonly-companion full
```

Each run: stamps the knobs into `_system/series-config.yaml`, cleans stage
outputs (keeps the chunk cache), drives design→compose(v2)→illustrate→
slide-import→awaiting-layout, then auto-layout (`auto_layout.py` — Composer
stand-in, alternates standalone/wrap so both render flows get exercised) →
`build_book_pdf.py --json` → commits + pushes the cell on the content branch.
Logs: `_workspace/experiments/v2-matrix/logs/<cell>.log` (machine-local).
Watch for `RENDER-DONE` / `PAUSED` / `FAILED` at the end of the log.
Liveness: the log and `book/_chunks/` should grow; a silent >30min alive
process is a stall — kill and re-run (chunk cache makes re-entry cheap).

## Gate each cell (after RENDER-DONE)

Invoke both agents (Claude Code session in the repo):
1. `book-challenger` — "challenge book the-master-and-the-disciple", pointing it
   at the WORKTREE BOOK_DIR explicitly. Validation mode: findings only, no
   re-compose. The cutover criterion is the **BK-P4** (faithfulness) probe.
2. `book-render-challenger` — same BOOK_DIR; criterion **RENDER-CLEAN**.
   `_system/book-render-checks.json` may be absent (CLI render path) — it runs
   the deterministic probes itself.

Record each cell's two verdicts here (and push):

| Cell | BK-P4 | RENDER |
|---|---|---|
| c5 | 🔴 BLOCKED overall (1 P0: planned preface never rendered; BK-P4 itself: BK5 P1 + BK10 P2, both chunk-seam narrator stitching). Core faithfulness clean: 0 doctrinal invention, 0 outside augmentation, BK-P3 all-canonical Arabic. | pass 1 RENDER-BROKEN (layout anchors dropped silently — fixed, scripts `9c598d9e`); pass 2 🟡 RENDER-CAUTION: 0 P0s, 6 P1s — renderer CSS: p5 table spill, p72 widow page, p9 float bleeds into chapter heading (chapter-open needs `clear:both` in book-print.css); fixture: same-anchor wrap pairs p8/p25, dense raster at 40% p85. Details in working-plan.md + `_system/book-render-checks.json` |
| c6 | | |
| c7 | | |
| c8 | | |

**✅ SYSTEMIC FIX LANDED (2026-07-16, laptop `/Users/asifhussain`).** The c5
challenger found a `compose_book_v2` chunking defect: content duplicates across
`book/_chunks/translation` chunk boundaries (4 of the 6 BK-P6 findings, incl.
one meaning inversion), the composer papers over seams with un-sourced narrator
bridges (both BK-P4 findings), and the planned preface is dropped entirely at
assembly (the P0). Per the systemic-fixes standing rule
(`feedback_systemic_fixes_from_chapter_archetype`), the root fix is now on the
maintenance branch in `scripts/podcast/_translation_edition.py`:

1. **Preface emission (fixes the P0).** `author_translation_edition_compose` now
   composes `book-toc.json`'s declared `preface` (its own source range) and emits
   it as a `## <title>` block before chapter 1. Previously the compose loop only
   iterated `chapters`, so the planned preface was silently dropped.
2. **Sequential window continuity (fixes the BK-P6 seam-duplication root).** Long
   chapters were split into windows composed IN PARALLEL, every window handed the
   same *previous-chapter* tail — so windows couldn't see each other and the model
   re-rendered boundary passages at each seam. Windows now compose SEQUENTIALLY,
   each handed the real tail of the window before it, so the compose prompt's
   "do not repeat this" continuity note actually holds at the seam. (Trade-off:
   loses intra-chapter parallelism on >4500-word chapters; the per-window chunk
   cache still makes re-entry cheap. `TRANSLATION_EDITION_MAX_WORKERS` is retired.)
3. **Deterministic seam-overlap trimmer (safety net).** `_trim_seam_overlap`
   conservatively drops a leading paragraph of any window/chapter that verbatim-
   echoes (SequenceMatcher ratio ≥ 0.80, or a ≥12-token verbatim run covering
   ≥60% of the paragraph) the tail of the previous one — catching BK2/BK3/BK4
   (intra-chapter) and BK6 (cross-chapter ch2→3 ¶27) residual echoes. Whole-
   paragraph drops only; never edits surviving text; can't false-positive on a
   genuinely distinct opening.

Unit tests in `scripts/podcast/tests/test_translation_edition.py` (7 new) cover
the trimmer boundary + preface emission/skip; full book suite 242 passed / 1
skipped. **The narrator bridges (BK5/BK10) were added to smooth the dups — with
the dups gone they should not reappear; the c5 re-run confirms.**

**⚠ NEXT — re-run c5 to validate the fix, THEN c6–c8.** Because the fix changes
window seams (not chunk BOUNDARIES — the window split points are unchanged), a
c5 re-run can REUSE the chunk cache; but to exercise the new sequential-tail
compose end-to-end, run c5 with `full` (not `resume`). If validating only the
deterministic assembly (preface + trim) without paying for re-compose, the
cached parts are re-assembled with the new preface/trim logic on any re-run.
Re-run c5 → both challengers → expect BK-P1 P0 cleared (preface present) and the
BK-P6 seam cluster gone; get it green — THEN run c6–c8. Full original findings:
the worktree's `book/book-challenger-report.md` + `_learning/findings.jsonl`.

## After all 4 M&D cells

**STOP. Do not execute Phase 5.** The cutover doc's gate requires BOTH fixture
books; mua2 is on hold. Ask Asif: M&D-only sufficient, or resume mua2 c1–c4
first? Then, per his answer:
- Phase 5 (Tier 2): `_workspace/plan/book-pipeline-cutover.md` §Cutover steps,
  exactly — flip default, delete legacy paths (`generate_translation_edition.py`,
  `_inject_figures` in `_book_illustrate.py`, `inject_slides` write in
  `_slide_import.py`, legacy `book_driver.py` dispatch), remove flag scaffolding,
  docs-sweep if `_rules.py`/state fields changed, regen dashboard snapshots,
  sync TS↔Python mirrors, `repo-surgeon --scope podcast`. Any red cell → STOP.
- Phase 6b: `cd plan-dashboard && npm run smoke` (32/32 baseline),
  `site-health-sentinel`, `html-view-challenger` on touched views,
  `npm run lint:views` + `npm run check`.
- Phase 7: ask Asif explicitly before merging the maintenance branch to `develop`.
- Commit + push after every phase (standing order, 2026-07-16).
