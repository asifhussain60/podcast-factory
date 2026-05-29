<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.
-->
# Current work — status

**Last updated:** 2026-05-29

**Active priority: the intelligence + podcast pipeline (Wisdom Corpus Program).**
First step shipped — the corpus-population ENGINE, proven end-to-end on the on-disk
wisdom/teaching material: tradition stamped on every atom (fatimid-ismaili), a
source-agnostic tiered dedup engine (exact + near-duplicate → variants / human-review
queue, non-destructive, idempotent), and a runner. Verified: 122 chapters → 628 atoms,
tradition 628/628, idempotent re-run, 3 borderline review candidates, 0 false merges.
Run `python3 scripts/podcast/intelligence/populate_corpus.py --verify-idempotent` to rebuild.

**Waiting on you:** the other three source databases. The Quran + scholarly DBs aren't
on disk and the teaching-sessions app needs a dump — you said you'll provide them later.
Their per-source importers are deferred until they arrive; the engine already has the
slots (see `SOURCES` in populate_corpus.py).

**RD COMPLETE (awaiting consolidation into a plan):** multi-source intake & reconciliation
+ the chapter-reader redesign. All decisions recorded:
- `09-source-intake-decisions.md` — SI-1..SI-7: spine+layered alignment; hybrid engine-by-strength
  (Gemini bulk / Claude judge / Azure targeted) for the Anwaar two-transcript compare; cheap-signal
  source triage at an early human gate; authority-ranked reconciliation marked in the viewer;
  early-halt placement reusing the gate mechanism; per-book in-context Intake Review panel;
  deterministic spine selection + gate override.
- `10-reader-redesign-decisions.md` — R-1..R-10: two modes (Read audience-grade / Studio review
  cockpit); single contextual inspector; Read = canonical text + subtle verified markers + docked
  audio + Arabic; divergences = inline indicator + side-by-side inspector; persistent synced audio;
  explicit episode↔chapter mapping (Read=episode, Studio=chapter); Studio = the pipeline's single
  human-review cockpit on **TipTap/ProseMirror** (+ jsdiff, floating-ui); FULL capability package
  (minimap/heatmap, marking palette, diff, tracked edits + accept/reject AI, review-queue +
  reviewed-state + one-click stage approval); desktop-only for now.
- Full discussion: `08-source-intake-discussion.md`. Standing prefs: [[ui-max-surfacing]] (richest in-viewer; richer UI is the tiebreaker).

**Next steps:** (a) **consolidate 09+10 into ONE plan.yaml wave (sub-steps) + snapshot, for Asif's
approval before any code** — this is a real re-platforming of Studio onto TipTap + the intake/
reconciliation pipeline work; OR (b) add the three corpus importers once sources land; OR (c) the
blackbox annotation engine + corpus-verified reader popovers; OR (d) the in-pipeline knowledge phase.

**Parked (resume anytime):**
- *Site redesign* — 5 of 13 views built, 5 text-only and pending. Full audit + resume
  order: `_workspace/plan/site-view-audit.md`. Discuss each page before changing it.
- *Lint backlog* — `npm run lint:views` → 51 non-blocking warnings toward `--strict`
  (the gate already blocks new MUST violations). Burn-down order in the audit doc.

---
*The HTML-view rules (HOW views are built) live in `docs/standards/html-view-quality-digest.md`
(MUST card) + the full standard. WHAT each view shows is agreed per page.*
