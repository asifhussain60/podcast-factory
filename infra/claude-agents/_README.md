# infra/claude-agents/

Canonical agent specifications for the podcast-factory repo.

**One canonical spec per agent. This directory is the single source of truth.**

## The mirrors are GENERATED — never hand-edit one

Each spec has two derived copies: `.github/agents/<name>.agent.md` (byte-identical
full text, for Claude Code / Copilot discovery) and `.codex/agents/<name>.toml` (for
Codex). **Both are written by
[`scripts/podcast/sync-agent-wrappers.sh`](../../scripts/podcast/sync-agent-wrappers.sh).**
Edit the spec here, run the script, stage what it writes:

```bash
bash scripts/podcast/sync-agent-wrappers.sh          # regenerate
bash scripts/podcast/sync-agent-wrappers.sh --check  # fail on drift (what pre-commit runs)
```

The pre-commit hook runs `--check`, so a hand-edited mirror or a forgotten regenerate
blocks the commit rather than drifting silently. The Codex tree is a **subset** by
design — 16 of the 22 agents — so a missing `.toml` is not itself drift.

> This supersedes the earlier "edit both files in the same commit and verify with
> `cmp`" instruction. Hand-mirroring is how `.codex/agents/book-challenger.toml` fell
> a whole generation behind while claiming to be a mirror (caught 2026-07-20).

---

## Agent registry (22 agents)

Alphabetical. Each row has one canonical spec in this directory and a generated
`.github/agents/<name>.agent.md` mirror.

| Agent | Purpose |
|---|---|
| `book-challenger` | Semantic-fidelity challenger for the reading-edition PDF (augmented companion + articulated translation editions) |
| `book-publication-reviewer` | Reader-facing review of the rendered PDF — is it understandable, consistent, taught in a sensible order; fixes are orienting BRIDGES only, never a reorder |
| `book-publisher` | Physical delivery — copies a book's audio (m4a) + reading-edition PDF to a target folder (default: Google Drive) |
| `book-rearticulator` | On-demand articulation of one stiff or literal chapter against the Book Articulation Standard; convergence action on failure is REVERT |
| `book-render-challenger` | Print-render challenger for the rendered reading-edition PDF (blank pages, split figures, watermark, page fill) |
| `html-view-challenger` | Conformance validator for HTML views against the Cortex quality standard (STATIC, source-level) |
| `noise-auditor` | Cross-surface detector for authorial-apparatus noise (circulation/provenance/colophon) the denoise step never strips; identify-only |
| `podcast-challenger` | Semantic quality validator for chapters and framings; convergence loop |
| `podcast-extract` | Single-chapter → NotebookLM bundle path orchestrator |
| `podcast-librarian` | Knowledge-extraction agent (Quran + hadith atoms → canonical library) |
| `podcast-orchestrator` | Autonomous book-to-NotebookLM pipeline driver |
| `podcast-planner` | Guardian + Builder for plan audits and roadmap step execution |
| `podcast-publisher` | Publish-gate enforcer — flips status draft→published in place after gates pass |
| `podcast-trainer` | Cross-book pattern learner; proposes regression-gated spec refinements |
| `postprod-review` | Post-production audio audit from downloaded m4a transcripts |
| `project-steward` | Strategic health advisor; composes other agents; corpus-cited recommendations |
| `pronunciation-probe-analyst` | Closes the Arabic pronunciation loop — judges the NotebookLM probe episode and writes durable ok/respell/unfixable verdicts into the cross-book library |
| `refine-prompt` | Refines raw requests into compact instruction paragraphs for Claude |
| `repo-surgeon` | Holistic repo auditor — 5-pass sweep (structure, code, architecture, brittleness, plan conformance) |
| `site-health-sentinel` | Runtime + visual-QA gate for the Astro site — boots a browser, sweeps every route for console errors, screenshots at desktop/mobile across states, judges pixels for visual defects, fixes in-pattern; the runtime peer of `html-view-challenger` |
| `slide-deck-challenger` | Visual quality validator for slide-deck bundles |
| `vacuum` | Post-production filesystem cleanup and file normalization |

**Deprecated (no spec file):** `podcast-blueprint` — agent + skill retired 2026-07-26 when the classifier they wrapped moved inline; the registry above still listed it until the 2026-08-10 infra audit. Its schema models survive as `scripts/podcast/_blueprint_schema.py`, and pipeline-debt F41 (the unwired `POST /api/intake/classify`) still names it — treat those as references to the retired Layer-1 classifier, not to a live agent. `podcast-auditor` — retired 2026-06-02; use `repo-surgeon --scope podcast` instead. `docs-updater` — spec + all three mirrors deleted 2026-08-05 (was declared retired in `framework.md` back on 2026-05-28, but the files themselves were never removed until this audit caught it); its target, `docs/architecture/index.html`, has been gone since that same date. `reconcile` — retired alongside `docs-updater` on 2026-05-28 for the same reason (its worked example also targeted the deleted `docs/architecture/index.html`), but a later "production-readiness sweep" (2026-05-31) accidentally resurrected the canonical spec from its still-orphaned `.github/agents/` mirror, believing the mirror's existence meant the canonical was "missing" rather than deleted-on-purpose. Deleted again 2026-08-05, this time with `.codex/agents/reconcile.toml` cleared too and `sync_codex_agents.py` fixed to delete/fail on that kind of orphan going forward (it previously only printed a NOTE and exited 0 even under `--check`, which is how the zombie went undetected for two months).

---

## DR-014 — the stub pattern that was never built

**The decision that stands:** the canonical spec lives here, and `.github/agents/`
exists so Claude Code and Copilot can discover it.

**The part that was never implemented:** those discovery entries were meant to be
≤15-line stubs pointing back here. They are full mirrored copies instead, and have
been since the decision was taken. The drift risk that motivated the stub was closed
a different way — by generating the copies (see the top of this file) rather than by
shrinking them. Recorded here only so the gap between DR-014 and the tree is not
rediscovered as a defect.

---

## Operating contract

The behavioral floor every agent enforces lives at
[docs/reference/operating-contract.md](../../docs/reference/operating-contract.md).
Agents read this file at invocation time; they never inline its full text.

---

## Installation

```bash
bash scripts/install-claude-skills.sh
```

The script reads from this directory and installs/updates the agent definitions into
`.claude/agents/<name>.md` at runtime. `.claude/` is gitignored (per-machine state);
this directory is the durable tracked source. Never edit `.claude/agents/` directly —
the next install will overwrite it.
