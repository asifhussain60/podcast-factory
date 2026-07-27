# repo-surgeon audit — 2026-07-27

First run of the refactored skill. The audit instrument itself was the subject of the
refactor, so this report has two halves: what was wrong with the auditor, and what the
repaired auditor then found in the repo.

Probe: `python3 scripts/repo_surgeon_probe.py` (deterministic; two runs on this tree
produce byte-identical output).

---

## Part 1 — the auditor was auditing a repo that no longer exists

Of the previous catalog's 38 rules, **21 were dead, inert, or aimed at surfaces deleted in
the 2026-05-22 repo split**, and one manufactured false findings on every run. The
duplicated generic engine was the half that rotted, because the project facts were
hardcoded inside the skill instead of read from the tracked contract.

| Class | Count | Detail |
|---|---|---|
| Rules auditing deleted directories | 14 | Pass 2 C1–C5/C8, Pass 3 A3/A4, Pass 4 B1/B3/B5/B6/B7 — `site/`, `server/`, `shared/`, `wrangler.toml`, journal-repo residue |
| Plan rules reading absent keys | 5 | L3 (`intelligence_sources`), L4 (`meta.scope_in`/`scope_out`), L7/L9 (`_workspace/plan/view/`), L8 (`meta.legacy_cleanup_basenames`) |
| Rules asserting a nonexistent contract | 1 | AU-V3 — `book.visuals-index/v1` appears nowhere in `plan-dashboard/`; the renderer reads `visual-layout.json` |
| False-finding generators | 2 | L7 emitted **35 false P2s per run** (every wave id "missing" from a deleted directory); L10 emitted **30 findings for one root cause** by scanning whole lines, catching checklist row ids and the P0–P3 severity grammar |
| Unfollowable instructions | 3 | Bootstrap reads 1–3 pointed at `reference/`; the files are under `docs/reference/` |
| Self-contradictions | 2 | Run-log path given as both `_workspace/logs/` and the deleted `server/logs/`; root allow-list blessed two surfaces `CLAUDE.md` bans while omitting `.repo-audit/` — so the audit contract read as clutter |
| Dead delegation targets | 3 | `ui-reviewer`, `css-theme-sync`, `journal-orchestrator` — zero on disk |

It was simultaneously **blind to all nine gates the repo actually enforces** (the contract's
verify list, six fixture-pinned mirrors, the DR-005 ratchet, agent-mirror sync,
generated-instruction parity, doc links, snapshots, view lint, runtime smoke) and had no
notion of waivers, so settled rulings were re-litigated every run.

### What changed

- Generic auditing **delegated** to the `repo-audit` skill; the duplicated copy deleted.
- Project facts **read from `.repo-audit/profile.yaml`**, never restated. The contract is
  validated before it is trusted, so a stale entry surfaces as a finding.
- Dead rules removed rather than left inert. `L10` rewritten to aggregate.
- `L2-DUP`, the gate-integrity group, and the standing-obligation table added.
- `scripts/repo_surgeon_probe.py` added so the catalog can fail. Each new check was
  verified by breaking what it guards and confirming a non-zero exit.
- `SK-DEADREF` added: the audit's own references are now checked. Nothing did that before,
  which is why the rot survived two months.

---

### Root cause of the rot, found while working the findings

The five dead plan rules did not decay gradually — they died in one commit. `78ce80e`
("consolidate `_workspace/plan` folder — nested structure + 24 file deletions") deleted
`_workspace/plan/podcast-plan.yaml` and moved planning to
`_workspace/plan/refactor/plan.yaml`. The deleted file has top-level `phases`,
`intelligence_sources` and `async_safety`; the surviving one has none of them.

Those are **exactly** the keys L3, L4, L6, L7 and L9 read. The moment the consolidation
landed, all five stopped matching anything and started passing vacuously, and `L7` — which
resolves a glob — began reporting every wave id as missing. Nothing failed, so nothing was
noticed. The recoverable copy is at `78ce80e~1:_workspace/plan/podcast-plan.yaml`.

This is the mechanism worth remembering: **a rule that reads a key by name reports success
when the key disappears.** The probe now asserts its own targets exist, which is the only
form of that check that degrades safely.

---

## Part 2 — findings from the repaired auditor

First run reported 7 P1. **Final state after Part 3: zero P0, zero P1, zero P2 — one P3 advisory.**
Three were real and are fixed; three were defects in the probe itself and are fixed; one is a
known, handled condition correctly re-severitied to advisory. No findings suppressed by
waiver; no stale contract entries.

> Sections below are the FIRST-pass findings, kept for the record. Where Part 3 supersedes
> one, the heading says so — the original text is left intact rather than rewritten, because
> what the audit first believed is part of what this report is for.

### CLOSED — Book print-quality standard was missing three requirement ids — P1

`scripts/podcast/_book_render_checks.py` emits seven `BR-*` checks. Three cite
requirement ids that `docs/standards/book-print-quality.md` does not define:

| Cited by code | In standard |
|---|---|
| `BR-CROSSWALK-MISSING` | absent |
| `BR-PLACEHOLDER` | absent |
| `BR-RUNNING-HEAD` | absent |

This is exactly the drift `AU-V5` exists to catch, and the old rule missed it by
hardcoding the original four ids. The probe now derives the list from the code.

**Fixed 2026-07-27.** Added `REQ-BR-004` (running head names the page's own chapter,
MUST/P1, under Pagination) and a new *Text integrity + apparatus* section carrying
`REQ-BR-030` (no unsubstituted `__TOKEN__` reaches print, MUST/P0) and `REQ-BR-031` (a
book with `source-crosswalk.json` prints its crosswalk page, MUST/P0). Each cites its
probe function by name. `--scope podcast` now exits 0.

### CLOSED — one of the two "dangling wave references" was a defect in the probe — P1

Wave `D` declares `depends_on: [A1]`. `A1` is a **step** of wave `A`, so the reference is
legitimate; the check resolved only against wave ids and reported it as dangling. Fixed
2026-07-27: `L2` now resolves against wave ids **and** step ids.

Recorded rather than quietly corrected, because it is the same false-positive class this
refactor exists to remove, and it was found the same way — by checking the data instead of
trusting the rule.

### SUPERSEDED by Part 3 — this was also a probe defect, not a plan defect

Wave `G` (family `waves_ghj`) declares `parallel_with: [F]`. There is no wave `F` and no
step `F`; the `waves` family skips the letter entirely (`A B C D E G H I J K L M N CP`).
Most likely `F` was folded into `waves_ghj` when that family was created, and the
reference outlived it.

**Wrong.** Wave `F` ("Archetype Completion") is alive under the top-level
`excluded_by_design` key, which matches no `waves*` pattern, so the probe never saw it. The
reference was always valid. See Part 3.

### RE-SEVERITIED in Part 3 to P3 advisory — a known, handled condition

`G, H, I, J, K` each appear in both `waves` and `waves_ghj`, so a `depends_on` naming one
cannot be resolved to a single wave. **This is not a naming slip.** The two families hold
overlapping but different work:

| id | `waves` | `waves_ghj` |
|---|---|---|
| G | Phase Runner Improvements + Orchestrator Hardening | Narrative Homepage |
| H | Audio Intake + Noise Router + Azure Pipeline | Code-Quality Refactor |
| I | Intelligence Pipeline — Tradition-Aware KB + Source Review Gate | Intelligence Pipeline — Audio Intake, Noise Routing, Tradition-Aware KB |
| J | Local-First Lookups + Dual-Interface Source Library Server | Source Library — Dual-Interface Server and Live Editor Integration |
| K | Knowledge Quality Pass — Terms, Quotes, Anti-Repetition | Quality Scoring + Pipeline Hardening |

Rows `I` and `J` describe substantially the same programme twice, which suggests
`waves_ghj` may **supersede** those `waves` entries — but nothing states so. No plan
document, README, or architecture note mentions `waves_ghj` at all; its only self-
description is a comment header, *"Wave G — Narrative Homepage (and beyond)"*.

**Needs the operator:** deciding which family is canonical is an authoring judgement about
what work is still live, not hygiene. Renaming either set without that decision would
freeze the wrong answer into every downstream reference.

### SUPERSEDED by Part 3 — the rule was reading the wrong document

19 ids: `B6, F1-F6, G2-G6, M4, N4, N5, P1.1, P1.2, P6.1, R7`. Provenance established:

| Ids | Where they resolve |
|---|---|
| `P1.1`, `P1.2`, `P6.1`, `R7` | The **deleted** `podcast-plan.yaml`, recoverable at `78ce80e~1`. `P1.1` = "audit script confirming zero cross-boundary writes" (still cited by `_boundary_check.py`'s docstring, which also names the deleted file); `R7` = the learning-loop-degradation risk |
| `B6, F1-F6, G2-G6, M4, N4, N5` | **No single source.** Scattered across unrelated documents with different meanings |

The second row is why a `legacy_id_map` cannot be authored by inference. `G4` alone means
three different things in this repo — a ship gate ("build-clean P0=0") in
`capabilities-manifest.yml`, a risk row in `intelligence/locked-decisions.md`, and a
checklist row id in the checklist itself. `F6` is a section heading in
`editor-refactor-plan.md` in one place and a cross-reference in another. The checklist's
own bold row ids also collide with its italic cross-references, so the id space is
overloaded in both directions.

**Deliberately not written.** A map guessed at 19 judgement calls would make broken
traceability *look* resolved, which is worse than the honest failure it replaces — a
partial map would also drop the finding from 19 ids to 15 and read as progress while the
ambiguity survived untouched. Each id needs a human ruling on which document it meant.

---

## Part 3 — second pass, after the probe's own bugs were fixed

Re-running the audit against the DATA rather than trusting the rules turned three of the
four remaining findings into probe defects. All are fixed; the id resolution is now
document-wide and source-correct.

### The probe was under-scanning in three ways

| Was reported | Truth | Fix |
|---|---|---|
| `waves.D` depends on `A1` — dangling | `A1` is a **step** of wave A | `L2` resolves against wave ids AND step ids |
| `waves_ghj.G` references `F` — dangling | Wave `F` ("Archetype Completion") is alive under the top-level `excluded_by_design` key, which matches no `waves*` pattern | `L2` resolves against **every id in the document** (`all_plan_ids`) |
| 18 checklist ids "the plan does not define" | They are **podcast-challenger check-catalog ids** (catalog runs A1..W6) — the checklist header says so. The rule was reading the wrong document | `L10` resolves against the check catalog, then the plan, then `R-*` rule names |

The wave-letter collision was also mis-severitied. It is a known, handled condition: both
snapshot generators resolve it by preferring the entry that carries steps, a rule pinned by
`tests/test_snapshot_regenerator_parity.py`. No reference crosses a family, so nothing is
ambiguous today. `L2-DUP` now fires **P1 only for a genuinely cross-family reference** and
**P3 advisory** otherwise.

### A near-miss worth recording

The `waves` G-K entries were first read as empty stubs and were one step from being
proposed for deletion. They are not stubs — they carry `execution_status: completed_*` and
`execution_notes` describing what shipped. Deleting them would have destroyed the execution
ledger for five completed waves. They have zero `steps` because the steps are DONE, which
is exactly why the snapshot rule keys on steps. Reading the entries before acting is the
only thing that caught it.

### What the corrected audit then found — and fixed

**The per-book ship checklist had 26 dead links.** This is an ACTIVE operational document
("Read by: podcast-challenger agent, the human reviewer at ship time"), and every one of
its three declared authoritative sources was unreachable. Two causes, both from `78ce80e`:

- The file moved into `operations/` and its `../../` prefixes were never re-depthed to
  `../../../`, so four links resolved into `_workspace/` instead of the repo root. This is
  the "patch references before finalizing a move" rule being skipped.
- It still cited `content/podcast/.skill/handbook/` and `content/_shared/arabic/`, both
  retired in the 2026-05-23 restructure, plus the deleted `podcast-plan.yaml`.

All 26 repaired against the authorities that actually exist. The retirement map was already
written down in `skills-staging/podcast/SKILL.md` and `scripts/podcast/learn_propose.py` —
the checklist simply never received it.

**The doc-link gate could not have caught this.** `_workspace/` is excluded on purpose: it
is a working surface of session notes whose paths were correct when written, and scanning
it (144 dead links across 52 files) would drown the gate. But `operations/` is not that —
it holds live documents. `_workspace/plan/operations/*.md` and `docs/standards/*.md` are
now in scope: 39 files checked before, 48 now. Verified by breaking a link and confirming a
non-zero exit.

**Four source files pointed at the retired Arabic tree**, one with the comment
`# still exists`. `learn_propose.py` fed that constant into the provenance strings for six
challenger checks, so a proposal cited an authority deleted two months earlier.
`scaffold_book.py` and `audit_transcript.py` told an author and an operator to consult it.
All repointed at the per-book `_system/glossary.yml` and `_rules.py`.

**CLAUDE.md claimed the tree "stays here as INDEPENDENT copies."** Corrected in place, and
`AGENTS.md` regenerated from it. The `_boundary_check.py` whitelist entry for
`06-abjad-numerals.md` is deliberately KEPT: it is test-pinned, defensive, and permits a
write that can no longer happen — removing it would be churn without a safety gain.

### Remaining: one P3 advisory

`G, H, I, J, K` are reused across `waves` and `waves_ghj`. Nothing is broken and nothing is
ambiguous today. Resolving it means deciding whether the `waves_ghj` entries supersede the
completed `waves` records or stand beside them as different work — an authoring judgement,
and the only finding left.

---

## Gate status at time of audit

| Gate | Result |
|---|---|
| `make lint` (ruff + format + DR-005) | clean, 532 files |
| `python3 -m pytest -q` | 2179 passed, 4 skipped |
| `_boundary_check.py` | clean |
| `check_doc_links.py` | clean, 39 files |
| `sync_agent_instructions.py --check` | AGENTS.md in sync |
| `sync-agent-wrappers.sh --check` | all four mirrors in sync |
| `npm run lint:views` | clean, 0 errors 0 warnings |
| `npm run check` (astro) | 0 errors, 0 warnings, 6 hints |

## Not wired into pre-commit, deliberately

## Wiring it into pre-commit is now possible

The probe's baseline is **zero P0/P1/P2** — it exits 0. The single remaining finding is a
P3 advisory, which does not block. Both the full run and `--scope podcast` (the sweep
`CLAUDE.md` mandates after every merge into `develop`) are clean, so gating on either is
now safe. It is deliberately still NOT wired in: that is a standing-policy change and the
owner's call, not the audit's. The reasoning is recorded in `.repo-audit/profile.yaml`
beside the verify block so the next audit does not re-derive it.
