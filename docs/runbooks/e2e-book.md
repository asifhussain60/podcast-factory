# End-to-end book runbook

Intake → publish for a new book. Assumes a clean clone with Azure + Claude Max creds configured per [infra/azure/](../../infra/azure/) and [infra/llm-apis/](../../infra/llm-apis/).

## 0. Pre-flight

```bash
bash scripts/start-session.sh   # fetches, fast-forwards develop, lists in-flight books
python3 scripts/podcast/cross_book_dashboard.py   # fleet view of all books
```

Confirm no in-flight book is in `phase=running` from a crashed prior session. If one is, run `python3 scripts/podcast/orchestrate_book.py --retry-phase <phase> <slug>` per [_workspace/runbooks/watchdog.md](watchdog.md) recovery section.

## 1. Intake

Drop the source PDF / DOCX / MP3 at `_workspace/_sandbox/<your-file>` then run intake:

```bash
python3 scripts/podcast/intake_book.py \
    --category books --slug my-book-slug \
    --source-path _workspace/_sandbox/my-book.pdf
```

This creates `book/my-book-slug` branch off develop, copies the source to `content/drafts/my-book-slug/_system/source/`, and writes the initial `orchestrator-state.json`. Series-config.yaml is scaffolded — fill in `audience`, `source_tradition` (default `islam`; ismaili/shia/sunni/twelver/sufi alias to it), `host_dynamic`, `per_chapter_cost_cap_usd` (default 5.0 — raise per book if needed), `enable_slide_decks` (default true).

## 2. Orchestrator launch (Tier 2 — REQUIRES Asif authorization)

First launch is multi-hour LLM spend:

```bash
python3 scripts/podcast/orchestrate_book.py \
    content/drafts/my-book-slug/_system/source/raw.pdf
```

This drives Phase 0a (ingest via Doc Intelligence) → 0b (refinement, parallel windows per F34-second) → 0c (phonetic extraction, parallel windows) → 0d (chapter design with thesis_relevance per F23 + editorial-frontmatter exclusion per F4) → 0e (enrichment) → 0f (halt for human review of series-plan.md). The watchdog auto-spawns on every `--resume` (see [watchdog.md](watchdog.md)). Re-arm the in-session heartbeat per CLAUDE.md Tier 0 rule.

## 3. Phase 0f review (human gate)

Read `content/drafts/my-book-slug/_system/series-plan.md`. Confirm chapter list, length tier, episode_format per chapter (deep_dive / debate / walkthrough / monologue / interview / recap / narrative — see [_rules.py:EPISODE_FORMAT_ALLOWED](../../scripts/podcast/_rules.py)). Edit series-plan.md if needed.

```bash
python3 scripts/podcast/orchestrate_book.py --resume my-book-slug
```

Drives per-chapter loop: extract → frame (with F1 word-cap compression retry) → build → converge (5 challenger iters max with F11 SHIP-preservation on later timeouts) → next chapter. Failed chapters (P0 unresolved or COST-CAPPED per F35-second) are skipped per F33-second graceful-degrade; whole-book proceeds; failures surfaced at end. Per-chapter timing in `phases.per-chapter.chapter_timings`.

## 4. Phase 0g audit + per-chapter-slides

After per-chapter loop, Phase 0g runs `phase_0g_register` + `phase_0g_audit_bundles` (F30 dual-auditor: Claude + Gemini in parallel per chapter; reports at `BOOK_DIR/audits/`). Then per-chapter-slides cohort authors slide decks. Then phase=finalize, status=halted.

## 5. Finalize review

```bash
jq '{phase, phase_status, completed_slugs: .phases."per-chapter".completed_slugs,
     failed_slugs: .phases."per-chapter".failed_slugs,
     audit_outcomes: .phases."0g".audit_outcomes}' \
   content/drafts/my-book-slug/_system/orchestrator-state.json
```

Review audit reports in `BOOK_DIR/audits/`. Spot-check episode txt files in `BOOK_DIR/episodes/`. Listen to a sample render in the reader section of the Podcast Factory Astro Site if desired.

## 6. Publish (Tier 2 — REQUIRES Asif authorization)

When satisfied, per [publish.md](publish.md):

```bash
python3 scripts/podcast/publish_to_library.py my-book-slug
```

G1-G7 gates validate; on PASS, moves `content/drafts/my-book-slug/` → `content/published/books/my-book-slug/`. The orchestrator then merges `book/my-book-slug` → `develop` with --no-ff, pushes, and the book branch becomes deletable per the "ONE branch per active book" rule.

## 7. Post-publish

Run the cross-book dashboard one more time to confirm the book moved to the `shipped` row. Optionally run `python3 scripts/podcast/learn_aggregate.py --by-check-id --since 7d` to see which rules fired most during the run — useful for next book's planning.
