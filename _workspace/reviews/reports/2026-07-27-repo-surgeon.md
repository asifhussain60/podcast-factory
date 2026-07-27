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

## Part 2 — findings from the repaired auditor

7 P1, 0 P0. No findings suppressed by waiver; no stale contract entries.

### Book print-quality standard is missing three requirement ids — P1

`scripts/podcast/_book_render_checks.py` emits seven `BR-*` checks. Three cite
requirement ids that `docs/standards/book-print-quality.md` does not define:

| Cited by code | In standard |
|---|---|
| `BR-CROSSWALK-MISSING` | absent |
| `BR-PLACEHOLDER` | absent |
| `BR-RUNNING-HEAD` | absent |

This is exactly the drift `AU-V5` exists to catch, and the old rule missed it by
hardcoding the original four ids. The probe now derives the list from the code.

**Fix:** add the three requirements to the standard, or retire the checks. A finding
citing a requirement nobody can look up is unactionable for whoever receives it.

### The ship checklist references a legacy id scheme the plan no longer defines — P1

`_workspace/plan/operations/per-book-ship-checklist.md` cross-references 19 ids the
current plan does not define: `B6, F1–F6, G2–G6, M4, N4, N5, P1.1, P1.2, P6.1, R7`. The
plan has no `meta.legacy_id_map` to translate them, so every one of those traceability
links is broken.

**Fix:** add `meta.legacy_id_map` to the plan, or update the checklist's annotations to
current ids. This is one root cause, not 19 defects.

### Two dangling wave references — P1

- Wave `D` declares `depends_on: [A1]`; there is no wave `A1`.
- Wave `G` (family `waves_ghj`) declares `parallel_with: [F]`; there is no wave `F`.

### Five wave ids are defined in more than one family — P1

`G, H, I, J, K` each appear in two wave families, so any `depends_on` reference to them is
ambiguous — including the two dangling ones above. The previous catalog never checked
this. It is the likeliest reason the dangling references went unnoticed: dependency
resolution was never well-defined.

**Fix:** namespace the ids per family, or rename the duplicates. Worth doing before
adding another wave family.

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

The probe is not in the contract's `verify:` list and not in the pre-commit hook. Its
baseline is the 7 P1s above — all pre-existing, none introduced by this refactor — so
gating commits on it would block every commit on someone else's backlog. Add it once the
baseline is zero. The reasoning is recorded in `.repo-audit/profile.yaml` beside the
verify block so the next audit does not have to re-derive it.
