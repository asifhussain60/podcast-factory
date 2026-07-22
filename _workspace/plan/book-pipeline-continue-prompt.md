# Continuation prompt — Book Pipeline v2

Paste the block below into a fresh Claude Code session (in the `podcast-factory` repo) on the MacBook Air to resume implementation.

---

You are resuming an approved, multi-phase implementation in the `podcast-factory` repo. Do NOT re-plan — the plan is already approved and committed.

**Read first:** `_workspace/plan/book-pipeline-plan.md` (the full approved plan — context, the two architectural moves, the cross-cutting contracts, Phases 0–8, the UI visual-QA loop, standard-adoption table, key files, and verification). Treat it as the source of truth for this work.

**Branch:** work on `book-pipeline-v2` (already created and pushed). Run `git fetch --all --prune && git checkout book-pipeline-v2 && git pull --rebase` before starting.

**Execution mode — autonomous:** Implement Phases 0 → 8 in order. Commit after each phase with a descriptive message and proceed to the next WITHOUT asking permission. Stop only for a genuine blocker, a Tier-2 destructive action, or the final end-of-chain report. Do NOT push `develop`→`main`.

**The non-negotiable invariants (from the plan):**
- Feature flag `book_pipeline_v2` (default OFF) is the cohesion backbone: with the flag OFF the pipeline must reproduce today's output byte-for-byte; with it ON, exercise the new path on the two fixture books. Commit a phase only when green with the flag OFF.
- The two fixture books are `content/Islamic/the-master-and-the-disciple/` (augmented companion) and `content/Islamic/mukhtasar-ul-asar-2/` (translation edition). Their current PDFs are the regression baseline.
- Accuracy veto: every content-touching change is gated by `book-challenger` BK-P4 faithfulness + `_doctrinal.py` T1–T5. A teaching/citation/Arabic-term drift blocks the phase.
- Two independent knobs in `series-config.yaml`: `book_augmentation: none|source_only` and `book_voice: faithful|author_companion`. Config-default map must reproduce current output (`deliverable_mode: translation_edition` → `{none, faithful}`; legacy companion → `{source_only, author_companion}`).
- Visuals are decoupled: `book.md` stays diagram-free; candidates go to `book/visuals/` + `index.json`; the human curates via the Astro "Book Composer" which writes `book/visual-layout.json` (schema `book.visual-layout/v1`); the renderer consumes that contract. Placement supports `align: left|center|right`, `flow: wrap|standalone` (wrap requires `width_pct ≤ 50`), explicit `width_pct`, movable `anchor`, and `page_fit`. No figure may span a page break; no `NotebookLM` watermark; no duplicated caption; no blank/half-empty interior pages (professional page-fill).
- Any change under `plan-dashboard/` (the Podcast Factory Astro Site) must run the UI visual-QA loop defined in the plan AND pass `npm run lint:views` + the `html-view-challenger` agent, external CSS/tokens only.
- Keep TS↔Python mirror files in sync in the same commit; regenerate dashboard snapshots when touching the tracked plan docs; update `plan.yaml`/`plan.md` when a phase ships.

**Start now with Phase 0 (Spike + scaffold):** confirm the Astro write-back/API path (the reader is read-only today), stand up the `book_pipeline_v2` flag scaffold, and commit. Then continue through Phase 8, which ends by enhancing `repo-surgeon` to verify the new architecture, running `repo-surgeon --scope podcast`, fixing findings, and merging `book-pipeline-v2` → `develop` with `--no-ff`. Leave the tree clean and production-ready with the Astro site building and functional.

Before writing code each phase, restate the phase's goal and its flag-OFF invariant in one line, then implement.
