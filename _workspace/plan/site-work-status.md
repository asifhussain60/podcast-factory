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

**Last updated:** 2026-06-17 (session 31 — Arabic-review panel redesign + smart defaults)

**Session 31 (commits 0e7658e, 697f5e6, d4d34c7, branch Islamic/kunooz-al-hikmah):**
Five-part Arabic-review-panel overhaul (governance plan A approved). (1) Taa-marbuta
fix: 8 Kunooz terms whose Arabic ends in ة now end -h not -t (ri-yaah etc.) +
`_normalize_taa_marbuta()` added to fill_glossary_arabic.py so every future book is
normalized (idempotent). (2) NEW classify_term_defaults.py: per-term smart default
language — transparent terms (naturalised loanwords Allah/Quran, names+places,
calques like "First Intellect") -> speak English; technical/doctrinal (taʾwil,
nasut, riyat) -> recite Arabic. Flat-rate Claude Max, batched, NO API spend. Writes
ONLY existing fields (english_override for all + decision=replace_english/decided_by=auto
for transparent) => ZERO audio-pipeline change (replace_english already drops Arabic).
Idempotent + non-destructive: skips human ('reader') decisions. Ran on Kunooz: 113
English, 193 Arabic, 11 human preserved. (3) Panel redesign: dropped "Keep" (untouched
= already recited by default, per resolve_curation `decision or 'keep'`); 4 buttons ->
one Arabic|English segmented toggle; english_override shown inline (one-click flip, no
typing); phonetic + Arabic became inline pencil chips; "auto" tag on classifier
defaults, drops to decided_by=reader on any human flip; header reframed to
"N recited · M English — flip exceptions". Verified: astro check 0 err, lint:views
clean, toggle save round-trip live (auto->reader on flip) + page 200, glossary restored
after test. Earlier same session: english-term endpoint, panel one-click-accept/4-in-row/
wider-read (169246c). KNOWN debatable auto-defaults (e.g. tawaf->"circumambulation") are
flippable in the panel — classifier is a starting point. NOTE: ch01a still carries the
user's uncommitted content edits (Night-Journey Arabic + 2 deletions) from session 30.

**Last updated prior:** 2026-06-16 (session 30 — Studio draft-retention model shipped)

**Session 30 (commit b400dee, branch Islamic/kunooz-al-hikmah):** Fixed the
reported "edit, save, refresh -> reverts to original" bug at the root by adding a
DRAFT-RETENTION layer (governance-protocol plan, approved option A). Diagnosed:
the save round-trip itself worked (the user's deletion was on disk, original in
.bak) — the real gap was that the ONLY persistence was the explicit irreversible
"Save & Approve" (writes straight to canonical chapters/<id>.txt), so any
unapproved edits were lost on reload, and save==approve. New two-phase model:
edits autosave (debounced 1.2s + flush on tab-hide/unload) to a per-stage draft
at content/<bucket>/<slug>/_system/drafts/<chapter>/<stage>.md (NEW
lib/reader/stage-draft.ts; git-ignored); book-workspace.loadStageText prefers the
draft over canonical for the live editable stage (archives unaffected) + exposes a
per-chapter `drafted` map; NEW api/studio/draft.ts (POST autosave / DELETE
discard); save-stage approval now PROMOTES the draft -> chapters/<id>.txt AND
deletes it; StudioPoc: Discard deletes draft + reloads canonical (preserving
?ch=), "Save & Approve" cancels pending autosave then commits, "Draft saved · not
yet approved" indicator, approved badge reverts while a draft is open. SCOPE
SAFETY (verified): book-workspace is Studio-only; the public reader
(lib/reader/chapters) + publish/NotebookLM path read chapters/<id>.txt directly,
so an unapproved draft NEVER reaches the published book, audio upload, or
orchestrator. VERIFIED LIVE (API+SSR round-trip on ch13, cleaned up): draft
written -> served on full reload (survives refresh) -> discard reverts -> approve
clears draft; canonical never mutated until approval. astro check 0 errors;
lint:views clean. NOTE: the user has a live ch01a draft (their editor autosaving
through the new endpoint = feature working); if it predates the session-29 صورة/
gardens-gloss commits it could be stale — Discard resets to committed canonical.

**Session 29 (commit 39a5dae, branch Islamic/kunooz-al-hikmah):** Resumed an

**Session 29 (commit 39a5dae, branch Islamic/kunooz-al-hikmah):** Resumed an
in-flight, uncommitted feature — the Studio editor "Explain" immediate AI action
(begun after the session-28 commit; commits d7c49d6/67b3acc/a6d2c5f for the Arabic
replace + palette work also landed since the session-28 note). Highlight a passage
-> "Explain" sends the excerpt + FULL CHAPTER as context to Gemini Flash (new
api/ai/explain.ts, mirrors arabic-term.ts: generate + rateLimitCheck, thinkingBudget=0
so the 1024-tok budget feeds the answer, strips wrapping quotes) -> Flash rewrites
ONLY the excerpt into a clearer/fuller version staying inside the chapter's meaning,
voice, tradition (no new doctrine/names/citations) -> proposed text lands in an
editable textarea, confirm-then-replace, same shape as the Arabic action. Apply guards
the selection range is unchanged before replacing. Bundled footer fix: "approved"
reverts to "Save & Approve" on any fresh edit (approvedClean = approved && changedCount===0).
Verified: astro check 0 errors; endpoint exercised live (200, ~0.7s) — a real clause
expands into a faithful fuller rewrite; a two-word excerpt echoes the surrounding
sentence (expected — nothing to expand). Committed + pushed. NOTE left uncommitted:
content/Islamic/kunooz-al-hikmah/_system/review/ch01a-family-of-light.json — editor
approval-state record written live by stage-review.ts (this confirms the session-28
save-stage 404 worry is RESOLVED: save-stage now handles bucket-layout books with no
_stages/ and writes review/ records under _system/). No _system/review/* is tracked
for any book and there's no gitignore rule — left for Asif to decide track-vs-ignore.

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

Also shipped (commit d8eba51): Studio GLOBAL FIND-AND-REPLACE. Highlight a phrase
-> "Replace" term action opens a popup (multiple find->replace pairs + scope
checkbox: current chapter vs whole book). New api/studio/replace.ts rewrites the
canonical chapters/<id>.txt files (resolved via findContentDirSync) — literal
case-sensitive, pairs in order, preview-before-apply, per-file .txt.bak (gitignored)
+ git as deeper undo. StudioPoc mirrors confirmed pairs into the live editor doc.
Verified end-to-end (preview chapter=2/book=7-across-3 matches grep; apply book-
wide writes+restores clean). NOTE discovered: save-stage.ts still targets the
legacy content/drafts/books/_stages path + requires _stages, so for bucket-layout
books with no _stages (e.g. Kunooz) the editor's own Save & Approve likely 404s —
pre-existing latent bug, NOT fixed here (replace writes chapters/<id>.txt directly).

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
