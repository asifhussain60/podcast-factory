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

**Active discussion (RD):** multi-source intake & reconciliation — Asif's two questions
(unify multiple sources of one work early without losing concepts; compare the two Anwaar
transcripts + engine routing). FOUR decisions converged + recorded in
`_workspace/prompts/improvements/09-source-intake-decisions.md` (SI-1 spine+layered align;
SI-2 hybrid engine-by-strength; SI-3 cheap-signal triage at the gate; SI-4 authority-ranked
+ preserved + marked in the astro viewer). Full discussion restored at `08-source-intake-discussion.md`.
THREE open items remain before RD is complete: phase-placement of unify+triage vs the existing
halts; where the "source budget" renders in the astro viewer; spine-selection rule when >1
source could claim authority. Resume by closing those, then write the plan entry.

**Next steps (pipeline):** (a) close the 3 open RD items, then write the plan entry for the
intake/reconciliation work; OR (b) add the three corpus importers once sources land; OR
(c) the blackbox annotation engine + corpus-verified reader popovers; OR (d) the in-pipeline
knowledge phase (one chapter read → podcast framing + reader markers).

**Parked (resume anytime):**
- *Site redesign* — 5 of 13 views built, 5 text-only and pending. Full audit + resume
  order: `_workspace/plan/site-view-audit.md`. Discuss each page before changing it.
- *Lint backlog* — `npm run lint:views` → 51 non-blocking warnings toward `--strict`
  (the gate already blocks new MUST violations). Burn-down order in the audit doc.

---
*The HTML-view rules (HOW views are built) live in `docs/standards/html-view-quality-digest.md`
(MUST card) + the full standard. WHAT each view shows is agreed per page.*
