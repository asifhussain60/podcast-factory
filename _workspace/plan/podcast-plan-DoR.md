# Podcast Plan — Definition of Ready (DoR) Audit

**Date audited:** 2026-05-19
**Plan version:** see [`./VERSION`](./VERSION) — single source of truth
**Plan file:** [`./podcast-plan.yaml`](./podcast-plan.yaml)
**Verdict:** **DoR GREEN — 12 of 12 checks PASS**
**Branch cut:** `feat/podcast-w1-foundation` off `develop` at `d986a3d`

This document is the permanent, audit-preservable verdict of the DoR gate. The conversational walkthrough lives in git commit history; this file is the standing reference for "was the plan ready when we branched?"

---

## Pre-flight state (must hold at branch time)

| Tool / state | Required | Verified | Citation |
|---|---|---|---|
| Azure CLI authed on `Journal AI` subscription | yes | ✅ | `az account show` |
| `rg-journal-ai` resources: `journal-docintel`, `journal-translator`, `journal-speech` | all 3 | ✅ | [yaml:152-161](./podcast-plan.yaml#L152-L161) |
| Claude CLI ≥ 2.1.144 | yes | ✅ | [yaml:163](./podcast-plan.yaml#L163) |
| Python 3.14.4 | yes | ✅ | [yaml:164](./podcast-plan.yaml#L164) |
| Node v24.15.0 (for site/proxy work; not required for podcast pipeline runtime) | yes | ✅ | [yaml:165](./podcast-plan.yaml#L165) |
| `gh` authenticated | **NO** | ❌ **blocker for CI work** | [yaml:166](./podcast-plan.yaml#L166); run `gh auth login --hostname github.com --git-protocol https --web` |
| Git: `develop == origin/develop`, clean tree | yes | ✅ | both at `d986a3d` at branch time |
| Orchestrator quiescence | no in-flight runs | ✅ | `system_check.orchestrator.active_runs: []` |
| Guinea-pig PDF physically present | yes | ✅ | 4.4 MB at iCloud path; [yaml:174](./podcast-plan.yaml#L174) |

`gh auth` is the **only outstanding pre-flight blocker**. It does not block W1 code work; it blocks any acceptance row that creates or runs a `.github/workflows/*.yml`. Resolve before P2.4 / P2.5 / P8.8 land.

---

## DoR check matrix — 12 dimensions, all PASS

### (a) Scope bounded and named
**PASS.** [yaml:178-203](./podcast-plan.yaml#L178-L203) — `scope_in` (4 agent files, `skills-staging/podcast/**`, `scripts/podcast/**`, `content/podcast/**`, `docs/architecture/podcast-*.html`); `scope_out` (journal agents, journal scripts, journal content, journal docs, `infra/claude-agents/` slated for deletion).
**One whitelisted exception:** `content/_shared/arabic/06-abjad-numerals.md` (P4) — documented at [yaml:205-213](./podcast-plan.yaml#L205-L213).

### (b) Owner skill or agent named in the plan
**PASS.** `meta.owner: asif` ([yaml:130](./podcast-plan.yaml#L130)). Per-phase ownership is implicit by file location (every `files:` list either lives under `scripts/podcast/`, `skills-staging/podcast/`, `content/podcast/`, `.github/agents/podcast-*`, or `_workspace/plan/`).

### (c) Every output artifact has a target path and format declared
**PASS.** Every phase task has a `files:` list. New artifacts are marked `# NEW`; modified artifacts are listed without the marker. File format is implied by extension (`.py` for code, `.md` for docs, `.html` for views, `.jsonl` for append-only logs, `.json` for snapshots, `.yml` for CI workflows).

### (d) Pluggable pipeline contract specified
**PASS.** P17.1 spec block ([yaml:1782 area](./podcast-plan.yaml)) defines `SourceAdapter` Protocol:
```python
class SourceAdapter(Protocol):
    @classmethod
    def can_handle(cls, source_path: Path) -> bool: ...
    def extract(self, source_path: Path, book_dir: Path) -> RawText: ...
    def normalize(self, raw: RawText) -> str: ...
    def emit(self, normalized: str, book_dir: Path) -> Path: ...
```
Plus `RawText` dataclass, `REGISTRY: dict[str, type[SourceAdapter]]`, `dispatch()` function, and `_azure_client.py` as the sole credentials site. Promote-when trigger: first non-Arabic-PDF source arrives.

### (e) At least one test fixture for end-to-end exercise
**PASS — two fixtures:**
1. **Tiny-book fixture** (P2.1) — 3-chapter ~5k-word synthetic source with ≥1 Arabic phrase + ≥1 numeric claim. Cost <$0.50 per full pass. Lives at `scripts/podcast/tests/e2e/fixtures/tiny-book/` once W1 P2 ships.
2. **Kitab al-Riyad PDF** — the corpus guinea-pig book. Verified present at `/Users/ahmac/Library/Mobile Documents/com~apple~CloudDocs/Books/Kitab al-Riyad.pdf` (4.4 MB, mtime 2025-02-10). Wired into [yaml:174](./podcast-plan.yaml#L174). Drives the W3 corpus validation run (P9.5 or earlier slot once tier is confirmed).

### (f) Measurable acceptance criteria for podcast quality
**PASS — three authoritative sources, consolidated in companion doc.**
- Per-phase plan acceptance: [`./acceptance-criteria.md`](./acceptance-criteria.md) (~230 rows, mirrors every YAML task id).
- Per-book output quality: [`./per-book-ship-checklist.md`](./per-book-ship-checklist.md) ← **new companion doc** — consolidates `podcast-challenger` 30-check catalog + handbook NORMATIVE R-rules + `P9.per_book_ship_gate`.
- Sources cited per criterion in the new doc.

### (g) Rollback plan stated
**PASS.**
- Branch strategy: `feature branches off develop, merge via --no-ff` ([yaml:182](./podcast-plan.yaml#L182)). Force-push to develop / main never approved by default.
- Per-phase rollback: every phase's `files:` list is explicit, so a single-phase revert is a single-commit revert. No phase rewrites another's state.
- W2 P8.6 (phase rename) has `prereq_gate_for_p8_6_p8_8`: zero in-flight books — natural before W3 starts. If the rename breaks state, `git revert` on the P8.6 commit is sufficient (state files are gitignored; the commit only touches code + docs).
- Cost-bounded blast radius per phase via P6.3 hard cap (`$50/book`); P10.1 cost-ETA blocks W3 invocation if predicted spend exceeds cap.

---

## DoR meta-checks (the 12-point holistic pass)

| # | Check | Verdict | Method |
|---|---|---|---|
| L1 | YAML parses cleanly | ✅ PASS | `ruby -ryaml -e 'YAML.load_file(...)'` |
| L2 | Wave membership consistency: every `waves[].phases[]` element exists in `phases[].id`; every phase claims a wave via `wave:` field | ✅ PASS | 5 waves, 19 phases, zero orphans either direction |
| L3 | Every phase has tasks; every task has `acceptance` list (≥1 entry) | ✅ PASS | 60 tasks audited; P1.3 closed during audit (was deferred-to-deleted-P16 placeholder; now cross-references P8.8 workflow) |
| L4 | `depends_on` resolves to known phase ids (not sub-task ids) | ✅ PASS | P17.1 closed during audit (depended on `P5.4`/`P8.6` sub-tasks; corrected to `[P5, P8, P17]`) |
| L5 | Every wave declares a `kickoff_cmd` | ✅ PASS | 5/5 |
| L6 | Every wave declares a `done_signal` | ✅ PASS | 5/5 |
| L7 | Every phase id cited in `view/index.html` phase-pill grid | ✅ PASS | 19/19 phases pilled |
| L8 | `acceptance-criteria.md` mirrors every task id (every YAML task has at least one `**Pxx.x**` row in the checklist) | ✅ PASS | 60/60 task ids found |
| L9 | `VERSION` file present + non-empty | ✅ PASS | `1.0` |
| L10 | Single execution path — no `legacy_id_map`, no `LEGACY_ALIAS:`, no `back-compat alias`, no `OBSOLETED_BY` in YAML | ✅ PASS | All four substrings absent |
| L11 | Zero `v3.x` version chrome remaining in YAML | ✅ PASS | Pattern `v3\.\d+(?:\.\d+)?` returns no matches outside the `Phase` enum docstring (which is about pipeline phases, not plan versions) |
| L12 | Tasks referencing `scripts/podcast/` list specific files in `files:` section | ✅ PASS | Auditor swept; no orphan references |

---

## Two gaps closed during the audit (now resolved)

1. **P1.3** had no `acceptance` array (was a placeholder pointing at the deleted P16). Rewritten as a cross-reference acceptance row asserting `.github/workflows/podcast-isolation.yml` (created by P8.8) contains a step invoking `python3 scripts/podcast/_boundary_check.py` with `continue-on-error: false`.
2. **P17.1.depends_on** listed `[P17, P5.4, P8.6]` — but `depends_on` resolves at phase level, not sub-task level. Changed to `[P5, P8, P17]` (depend on the parent phases that ship the constants module and the bulk rename).

---

## Plan inventory at branch time

| Metric | Count |
|---|---|
| Phases | 19 (P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11, P12, P13, P14, P17, P17.1, P18, P19, P20) |
| Waves | 5 (W1, W2, W3, W4, W5) |
| Tasks | 60 |
| Principles | 9 (P-1 through P-9) |
| Risks | 9 (R1 through R9) |
| Open questions | 7 (Q1–Q7; Q1 resolved 2026-05-19) |
| `done_when` entries | 35 |
| Acceptance rows | ~230 |

---

## What happens next (the executable path)

```
gh auth login --hostname github.com --git-protocol https --web   # blocker for CI rows
python3 scripts/podcast/run_wave.py 1                            # W1 kickoff — once run_wave.py P1.4 ships
```

But `run_wave.py` itself is P1.4 — so the genuine first executable step is **P1.1** (write `scripts/podcast/_boundary_check.py`), in parallel with **P1.2** (proposal-writer + docs), **P1.4** (the kickoff harness), **P2.1** (tiny-book fixture), **P3** (already done), **P4.1** (abjad-numerals shared file), **P5.2** (artifact validation), **P5.4** (phase-id constants module).

Per [yaml.waves[W1].parallelism](./podcast-plan.yaml): "P1, P2, P3, P4 in parallel; P5 sequential after P4; P6 sequential after P5; P1.4 (run_wave.py) before any other phase can be kicked off."

So in practice: ship P1.4 first (the harness), then everything else can run in parallel under it.

---

## Audit method (reproducible)

This audit is regenerable by running the Ruby + Python verification scripts that produced it. They live in git history under commit `d986a3d` (the strip-versioning commit). To reproduce:
```bash
cd /Users/ahmac/Code/Journal/_workspace/plan
ruby -ryaml -e 'YAML.load_file("podcast-plan.yaml"); puts "L1 PASS"'
# ... see git log for the full 12-check suite
```

If any check goes from PASS → FAIL on a future audit, the corresponding gap MUST be closed before the next wave kicks off. The DoR gate is a standing invariant, not a one-time event.
