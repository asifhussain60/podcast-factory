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

**APPROVED — co-development build on Ayyuhal Walad (plan.yaml WC8).** Walking-skeleton / vertical
slices: each pipeline step built WITH the editor halt that reviews it, run non-destructively on
ayyuhal-walad (own branch, new artifacts only, never re-ship), single-source first. Unification =
common-denominator CORE + attributed ADDITION layers (narrator/explainer/translator), then
noise-strip + enhance (SI-1 refinement). Cadence: **holistic review of ALL completed slices +
pipeline↔UI realignment between every slice** (mandatory gate). Slices: 0 readiness (reconcile
dual phase-naming, install TipTap+jsdiff, ayyuhal branch, editor↔halt write-back) → 1 intake+halt
→ 2 refine+halt → 3 reconcile+halt → 4 knowledge+halt → 5+ deepen.

**SOURCES LANDED (2026-05-29).** Multi-format Ayyuhal set received: 3 PDFs committed (Arabic original,
English superior, scholarly) at `content/drafts/books/ayyuhal-walad/_system/source/multi/` + SOURCES.md;
12 lecture videos (~13GB) + any extracted audio stay LOCAL (transient, deletable after build, restorable
from YouTube) — only pipeline-produced TEXT gets committed. Fixture now exercises the full common-denominator
+ attributed-additions design (Arabic core; English/scholarly/spoken = addition layers). Ready for Slice 0.

**First move when go:** Slice 0, starting with the TipTap proof-of-concept on one Ayyuhal chapter →
HALT for Asif's feel-check → finish the foundation. No LLM spend in Slice 0.

**Parked (resume anytime):**
- *Site redesign* — 5 of 13 views built, 5 text-only and pending. Full audit + resume
  order: `_workspace/plan/site-view-audit.md`. Discuss each page before changing it.
- *Lint backlog* — `npm run lint:views` → 51 non-blocking warnings toward `--strict`
  (the gate already blocks new MUST violations). Burn-down order in the audit doc.

---
*The HTML-view rules (HOW views are built) live in `docs/standards/html-view-quality-digest.md`
(MUST card) + the full standard. WHAT each view shows is agreed per page.*
