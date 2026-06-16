<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.

  HISTORY: prior session logs (sessions 9-26) were trimmed 2026-06-15 to keep this
  file small — a 23KB backlog had pushed the hook's old whitespace-strip into a
  ~10min CPU spin. Recover any earlier entry from git history of this file.
-->
# Current work — status

**Last updated:** 2026-06-16 (session 28 — Studio action-item queue stabilized + committed)

**Session 28 (commit 80e612e, branch Islamic/kunooz-al-hikmah):** Resumed an
in-flight, uncommitted feature — the Studio editor "deferred AI action-item"
system. PRODUCER half is now complete, verified, and committed: stamp actions
(etymology/rewrite/rephrase/improve/expand/condense/simplify/remove/define/xref/
addcorpus) on a paragraph or selected term -> persist to new action_items table
(schema/031) -> knowledge.ts CRUD -> api/studio/action-items GET/POST/DELETE ->
StudioPoc palettes + queue list + inline badges. One immediate action "arabic"
(api/ai/arabic-term) renders EN->Arabic via Gemini Flash, confirm-then-replace.
Two defects found + fixed: (1) arabic-term called undefined extractJson (build
break) -> added, mirrors define-term fence-strip parse; (2) intermittent empty
output -> thinkingBudget=0 (Flash thinking ate the 300-tok budget). astro check
0 errors; POST/GET/DELETE + Arabic endpoint exercised end-to-end on live server.
CONSUMER half NOT built: no CLI drain pass exists to read pending rows, run AI
per action_kind, and write results back into `result`. That is the next phase
(needs a per-kind handler design pass before building — it is spend-bearing).

**Session 27 (audit + fixes, commit 9c5ff4a):** Full pipeline + site audit; every

**Session 27 (audit + fixes, commit 9c5ff4a):** Full pipeline + site audit; every
finding independently verified before fixing (pipeline auditor fabricated most of
its claims — only merge-abort hardening in phases/merge.py + a __main__ guard on
_fix_chapter_commas.py were real). Site MUST fixes, all challenger-gated PASS:
archive form onclick -> data-confirm + submit listener (library/[slug]); Sparkline
useId a11y ids; ChapterEditor + PipelineOverviewRail inline styles externalised
(k-<kind> classes set --por-k; zoom/width via --por-zoom/--por-w; popovers via
--pop-top/--pop-left ref callbacks); svg width/height attrs dropped; REQ-052
.table-container promoted to theme.css + wrapped pron/intelligence tables;
sequence-diagram Mermaid theme vars added (actors were default grey); REQ-050
reduced-motion guards (intelligence/narrative/chapter-viewer css + SMIL particles
skipped via matchMedia); lint hardened with blocking INLINE-HANDLER check; lint
allow-list now empty (rail entry removed), stale NarrativeBase note corrected.

**Deferred design-decision queue (discuss one page at a time, NOT bugs):**
(a) NarrativeScroll homepage — 11 JSX <style> keyframe blocks, off-token cinematic
palette/fonts, unguarded GSAP — needs documented-exception-or-retheme call;
(b) REQ-010 typography sweep (.small/.card-sub used for multi-sentence prose);
(c) section ids/number markers on overview/architecture/infrastructure/quality;
(d) figure+figcaption wrappers for architecture diagram mounts; (e) SHOULD tier:
scroll-behavior smooth, print block, ld+json, footer conformance stamp,
system-map density split, SpendChart dead code removal (Tier-2 rm — ask).
