# Postprod-Vacuum brief — verification, filter, delta against existing ledger

**Branch:** `book/the-master-and-the-disciple`
**Companion to:** [`postprod-vacuum-tasks.md`](postprod-vacuum-tasks.md) (canonical 12-task ledger)
**Created:** 2026-05-26
**Status:** Advisory review — does NOT replace the 12-task plan; reconciles a fresh planning brief against it.

This document is the response to Asif's "Architecture Planning" brief that proposed adding (1) a post-production audio-file rename step and (2) a slide-deck-folder bug investigation. The brief was issued without awareness of the active postprod-review + vacuum agent build already on this branch; the bulk of its asks are already in flight as T3–T8 + T11 of the ledger. Below is the verification scan, filter table, deltas, and the small number of genuinely new items worth folding into the ledger.

---

## 1. Verification scan

Findings from the codebase on `book/the-master-and-the-disciple`.

| Brief claim | What the codebase actually shows | Verdict |
|---|---|---|
| Skill defines "Phases 1–4" of source-bundle prep | The pipeline runs orchestrator phases `0a` → `0b` → `0c` → `0d` → `0e` → `0f` → `per-chapter` → `per-chapter-slides` → `finalize` → `publish` (see `scripts/podcast/orchestrate_book.py` + `phases/`). The "Phase 1–4" framing comes from the generic `skills-staging/podcast/SKILL.md` for ad-hoc bundle prep; it is NOT the orchestrated per-book pipeline. Mixing the two will mislead any reader. | REVISE |
| Workspace registry is `_registry.md` | No `_registry.md` exists anywhere under `content/drafts/` or `content/published/`. The actual upload-time mapping lives in `chapter-contracts/*.yml` (canonical `ch<NN>-<slug>` naming) and the orchestrator's `_system/orchestrator-state.json`. Postprod-review's pairing artifact is `audits/postprod-<slug>-pairing.json`. | REJECT (registry doesn't exist; correct artifact already designed) |
| Phase 4 caches upload-time mapping in `_registry.md` | Not happening. The mapping NotebookLM destroys is reconstructible from the chapter-contract slug + the upload order the operator used. The vacuum agent spec already covers this via §1 "Inputs" and the postprod-review pairing JSON. | REJECT |
| Post-production agent should own rename | An agent pair is already designed with explicit Worker/Judge separation: `postprod-review` JUDGES (identify-only, never mutates); `vacuum` MUTATES (renames, moves, deletes, with dry-run-first + `--apply` gate). The brief's recommendation collapses the two responsibilities the existing design deliberately split. See [`infra/claude-agents/postprod-review.md`](../../../infra/claude-agents/postprod-review.md) and [`infra/claude-agents/vacuum.md`](../../../infra/claude-agents/vacuum.md). | REJECT (existing split is sounder) |
| Slide-deck module exists or is planned | EXISTS. `scripts/podcast/build_slide_deck.py` + `_slide_authoring.py` + `_slide_convergence.py` + tests at `scripts/podcast/tests/test_build_slide_deck.py`; agent at `infra/claude-agents/slide-deck-challenger.md`; output target `content/drafts/<slug>/_system/slide-decks/<chapter-slug>/`. The orchestrator phase is `per-chapter-slides`. | CONFIRM |
| "Most recent book run produced no slide-deck folder" | INCORRECT diagnosis. The folder `_system/slide-decks/` exists on M&D with one subfolder per chapter (all six). The bug is that `per-chapter-slides` reported `status: completed` with per-chapter `outcomes` of `SKIPPED` ×4 and `BLOCKED` ×2 — i.e. the phase fired and the per-chapter decision logic refused to author for every chapter. The visible symptom (empty/sparse slide-decks) is real; the root cause is in the SKIP/BLOCK decision path, not in module wiring or trigger eligibility. | REVISE the bug ticket |
| Azure handles audio transcription + scanned-PDF OCR | PARTIAL. `scripts/podcast/_azure.py` + `test_azure_connectivity.py` exist; OCR via Document Intelligence is wired (`ocr_image_pages.py`, `diff_ocr_vs_chapters.py`). However NotebookLM-output transcription is currently done by **Turboscribe** (human-driven, see ledger T5/T8), NOT Azure Speech-to-Text. The brief's "Azure handles audio transcription" claim is wrong for the postprod path. | REVISE |
| Google role exclusive to NotebookLM, browser-driven | Confirmed by `SKILL.md` and CLAUDE.md hard rule "never automate the browser for NotebookLM." | ACCEPT |
| Anthropic Claude owns all reasoning/orchestration/quality/rename | Mostly true, with the nuance that rename is owned by the `vacuum` *agent* (Claude-driven), invoked via `scripts/podcast/vacuum.py` (T3, not yet built). | ACCEPT (with the vacuum-agent caveat) |
| Total = 13 stages | Not a useful framing for this codebase. The orchestrator has 10+ phases plus a post-pipeline human review loop (NotebookLM → Turboscribe → vacuum → postprod-review). Counting "stages" obscures more than it reveals; the ADRs and phase list in `architecture.md` are the right reference. | REJECT (count is arbitrary; existing phase list supersedes) |

---

## 2. Filter results table

| Input from brief | Verdict | One-line reasoning |
|---|---|---|
| ITEM 1 — Post-production rename step | REVISE | Already designed; owner is `vacuum`, not "post-production agent". Brief collapses the Worker/Judge split. Fold the *intent* into T3–T6 (already there). |
| ITEM 1 sub — Mapping cached in `_registry.md` | REJECT | `_registry.md` doesn't exist; the right artifacts are `chapter-contracts/*.yml` + `audits/postprod-<slug>-pairing.json`. |
| ITEM 1 sub — Dry-run mode required | ACCEPT | Already the `vacuum` default (`default_mode: dry_run`, `apply_requires: user_approval`). |
| ITEM 1 sub — Every rename logged | ACCEPT | Already covered: `audits/vacuum-applied.md` per the vacuum spec. |
| ITEM 1 sub — Human approves before destructive | ACCEPT | Already T4, T5, T6 halt points. |
| ITEM 2 — Slide-deck folder bug | REVISE | The folder exists; phase fired; per-chapter outcomes were SKIPPED/BLOCKED. Investigate the SKIP/BLOCK decision logic, not module wiring or trigger eligibility. Ledger T11 should be updated to reflect this. |
| Inference — Azure pre-processes audio | REVISE | Azure does OCR; Turboscribe (not Azure) transcribes NotebookLM output. |
| Inference — Google = NotebookLM only | ACCEPT | Matches code + hard rule. |
| Inference — Anthropic owns everything else | ACCEPT (caveated) | The vacuum agent is the rename owner inside the Anthropic scope. |
| Inference — Slide-deck module exists | ACCEPT | Confirmed: `build_slide_deck.py` + tests + agent + state-machine integration. |
| Inference — 13 stages total | REJECT | Arbitrary count; pipeline is phase-based not stage-based. |
| NEW — SKIP/BLOCK decision logic for slides | 🆕 | Investigation should produce a decision-table + remediation, not a one-line "rerun and observe." |
| NEW — Pre-existing `m4a/v1/` legacy directory | 🆕 | M&D's `m4a/v1/` is a sibling to `m4a/transcripts/`; vacuum needs an explicit policy for "v1 legacy" before T5 runs. Cross-reference ledger T4. |
| NEW — `meta.yml` `archetype:` field needs schema-locking before T2 | 🆕 | T2 stamps `archetype:` into meta.yml but no validator enforces the field today. Add a tiny `_archetypes.py` schema check before T2 ships. |

---

## 3. The plan (deltas to fold into the existing ledger)

The 12-task ledger is mostly correct. Below are targeted edits and three new sub-tasks. Each is shown in the canonical plan-block format.

### 1. Re-scope T11 from "missing folder" to "SKIP/BLOCK decision-path bug"

> The slide-deck folder for M&D is NOT missing — it exists at [`_system/slide-decks/`](../../content/drafts/BOOKS/the-master-and-the-disciple/_system/slide-decks/) with one subfolder per chapter, and the `per-chapter-slides` phase ran to completion. The real bug is that all six chapters returned `SKIPPED` (×4) or `BLOCKED` (×2) — the per-chapter slide-decision logic refused authoring for every chapter. T11 should investigate `_slide_convergence.py` + `_slide_authoring.py` to surface (a) the SKIP/BLOCK predicate, (b) which input drove each verdict, and (c) whether SKIPPED is a true no-op-needed outcome or a silent regression.
>
> *Value gained:* The bug becomes actionable instead of a re-run-and-pray; root cause is identified before any retry burns LLM spend on the same wrong decision.

### 2. Add T13 — Schema-lock `meta.yml` `archetype:` field before T2 stamps it

> T2 writes `archetype: scholarly-deep-dive` (KaR) and `archetype: socratic-dialogue` (M&D) into each book's `meta.yml`, but no validator enforces the field's existence, allowed values, or shape. Add a small registered-archetype check inside the T1 `_archetypes.py` registry that fails loudly if a stamped value isn't in the registry. Without this, a typo in T2 ships silently and postprod-review picks the wrong rubric.
>
> *Value gained:* Eliminates the silent-mismatch class of bug at the seam between archetype declaration (T2) and archetype consumption (T7/T8); cheap to add when the registry is being built.

### 3. Add T14 — Explicit `m4a/v1/` legacy-directory policy in vacuum plan

> M&D's [`m4a/`](../../content/drafts/BOOKS/the-master-and-the-disciple/m4a/) contains a sibling `v1/` subfolder alongside `transcripts/`. The vacuum spec mentions removing "`m4a/v1/` legacy mp3s" but the actual policy (delete? archive? leave?) isn't pinned. Decide once, document in `content/_shared/conventions/audio-folder-name.txt` alongside the m4a-vs-audio decision, and write the vacuum plan to handle it deterministically.
>
> *Value gained:* T5 runs without halting on an undeclared edge case; KaR's T6 inherits the same policy without re-litigation.

### 4. Reject the brief's "_registry.md" addition; keep the existing artifact set

> The brief proposes extending a `_registry.md` schema to support rename mapping. That file does not exist in the pipeline today and there is no reason to introduce it — the canonical naming source is `chapter-contracts/*.yml` (per `_branching.py`), and the audio→chapter pairing artifact is `audits/postprod-<slug>-pairing.json` (per the postprod-review spec §1). Introducing `_registry.md` would create a third source of truth and a divergence risk against the chapter-contracts.
>
> *Value gained:* Avoids inventing a new artifact that overlaps two existing ones; keeps the chapter-contract as the single naming authority.

### 5. Reject the brief's "rename ownership = post-production agent"

> The brief recommends post-production agent owns rename, with vacuum reduced to "verifying the rename happened." The existing design is the opposite, and the existing design is correct: `postprod-review` is identify-only (Judge); `vacuum` is the only authorized mutator (Worker). Collapsing them re-merges the Worker/Judge boundary that was just deliberately split. Vacuum already consumes `delegate_to: vacuum` findings from postprod-review — the delegation chain matches the brief's intent without violating the separation.
>
> *Value gained:* Preserves Worker/Judge separation so an audit can never silently rewrite the thing it audited; matches the model already used by `podcast-challenger` + `podcast-trainer`.

### 6. Folded items (no change needed — already in ledger)

> Brief's "dry-run mode required," "every rename logged," "human approves before destructive rename," and "rename to canonical `ch<NN>-<slug>`" are all already in T3–T6 + the vacuum spec sections §2 (canonical layout) and §3 (m4a/audio reconciliation). The brief's intent is preserved; no new tasks needed.
>
> *Value gained:* Confirms the brief was directionally right on the safety properties even where it duplicated existing design.

---

### Integration into the active ledger

When Asif approves this review, the [`postprod-vacuum-tasks.md`](postprod-vacuum-tasks.md) ledger gets these mechanical edits in one turn:

- T11 row description rewritten to "Investigate SKIP/BLOCK decision-path in `_slide_convergence.py` for M&D's per-chapter-slides outcomes (4×SKIPPED + 2×BLOCKED). Slide-deck folder DOES exist; bug is in the decision predicate, not module wiring."
- Append T13 (archetype schema-lock).
- Append T14 (`m4a/v1/` policy).
- Change log line: "2026-05-26 — folded postprod-vacuum-review.md deltas; T11 re-scoped; T13/T14 added."

---

## 4. Open questions

Capped at 3; only those whose answer materially changes the plan.

1. **T11 escalation:** if the SKIP/BLOCK decision-path turns out to be intentional (i.e. the slide-deck module correctly identified these chapters as not slide-eligible), is that an acceptable outcome for M&D, or does it contradict the standing rule that "slide decks is not optional" ([`feedback_slide_decks_required.md`](~/.claude/projects/-Users-asifhussain-PROJECTS-podcast-factory/memory/feedback_slide_decks_required.md))? The remediation diverges: tighten the predicate vs. retire the rule.

2. **`m4a/v1/` policy:** delete after T5 runs, archive to `_system/legacy/m4a-v1/`, or leave untouched? Affects T14's acceptance criterion and whether T5/T6 are destructive Tier-2 actions.

3. **Brief's "13 stages" framing for any user-facing doc:** is there a downstream artifact (an architecture diagram, a Notion page) that Asif is trying to align the codebase against? If yes, the diagram should be updated to match the actual phase list; if no, the count can be dropped silently.

---

## 5. Out of scope

Deliberately excluded from this review and not folded into the ledger:

- **Rewriting the `skills-staging/podcast/SKILL.md` Phases 1–4 framing.** The skill's ad-hoc bundle-prep flow is a legitimate parallel surface to the orchestrator's per-book phases; trying to reconcile the two numbering schemes in this review would derail the postprod-vacuum work. Logged here as a future debt item if a confusion regression appears.
- **Replacing Turboscribe with Azure Speech-to-Text.** The brief implied Azure should own audio transcription; Turboscribe is the locked tool ([T5 in ledger](postprod-vacuum-tasks.md)). A switch is a separate Tier-2 decision with cost + accuracy implications; not in scope for postprod-review or vacuum.
- **Building a separate "rename module."** Brief floated "dedicated renamer" as an option; the vacuum agent is that dedicated renamer. No new module needed.
- **Adding a new orchestrator phase for post-production.** Per ledger T9, the existing `finalize` halt is enriched with post-production instructions; no new phase. The brief's framing of post-production as a stage-counted addition would violate that decision.
- **Touching the `develop` branch.** This review and all delta tasks stay on `book/the-master-and-the-disciple` until T12 (post-merge audit + categorized commit).
