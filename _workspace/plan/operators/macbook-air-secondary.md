---
schema_version: 1
machine_id: macbook-air-secondary
role: secondary
description: Secondary machine for podcast-pipeline work; currently driving kitab-al-riyad
hostname_hint: Asifs-MacBook-Air.local
operator: Asif Hussain (asifhussain60@gmail.com)
worktree_layout:
  - path: /Users/asifhussain/PROJECTS/journal
    branch: book/kitab-al-riyad
current_branch: book/kitab-al-riyad
current_book: kitab-al-riyad
current_book_dir: content/podcast/library/books/kitab-al-riyad
authoritative_state_path: content/podcast/library/books/kitab-al-riyad/_system/orchestrator-state.json
status_tag: HALTED-AT-0F-AWAITING-0G-GO
current_phase: "0f"
current_phase_status_summary: |
  Phases 0a–0f complete. KaR's series-plan.md written and committed at the 0f
  human-review gate (commit 90a7fa6). Subsequent human-review actions also done:
  Episode 2 removed (manuscript-history bookkeeping with minimal listener value),
  11 of 14 episode contracts moved from default deep_dive → debate format to
  match al-Kirmani's actual al-Islah/al-Nusra rhetorical structure (commit
  5352d61). Framework upgrades shipped so future books get content-aware Phase 0d
  classification + richer Phase 0f series-plan template automatically (commit
  ad80b5a). Air merged book/kitab-al-riyad → develop (commit e122fa0) and pushed.
  Next gate: Asif's go-ahead to advance KaR to Phase 0g (per-episode authoring of
  14 episode scripts; estimated cost $14-42, runtime 7-14 hours wall clock).
next_action: |
  Await Asif's go-ahead to advance KaR to Phase 0g. When approved, run:
    python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad
  Phase 0g is challenger-convergence per chapter (3 outer × 5 inner = 15 passes
  max per episode). Resume-safe; surface to Asif on any per-chapter halt.
anthropic_share: 0.5
last_verified_at: 2026-05-21T10:30:00Z
last_updated: 2026-05-21
response_conventions: see _workspace/plan/response-conventions.md (BLUF format,
  AskUserQuestion ordering, halt-and-surface pattern, cross-machine awareness)
written_by: mac-studio-primary (one-time §15 exception, 2026-05-21T11:50Z, per Asif's explicit instruction to add setup/ folder cross-reference)
---

# MacBook Air (secondary) — operator index

**This file is written ONLY by `macbook-air-secondary`.** The Studio reads
it but never writes it. See [coordination-protocol.md §1](coordination-protocol.md).

> ⚠️ **WRITE EXCEPTION — 2026-05-21T11:50Z (Studio-authored, per coord-protocol §15)**
>
> The Studio created a new `setup/` documentation folder at
> [setup/](setup/) per Asif's explicit instruction (chat 2026-05-21). It contains
> per-machine config ([setup/machines.md](setup/machines.md)), the Azure stack +
> recreate procedure ([setup/azure-stack.md](setup/azure-stack.md)), a full
> blank-Mac bootstrap ([setup/recreate-from-scratch.md](setup/recreate-from-scratch.md)),
> and a runtime-compatibility matrix that records the 2026-05-21 Cowork-incompatibility
> verdict ([setup/runtime-compatibility.md](setup/runtime-compatibility.md)).
>
> **On the Air's next session, do these three things:**
>
> 1. Verify the per-Air section in [setup/machines.md](setup/machines.md) accurately
>    describes the Air (worktree path, current branch, role). The Studio populated
>    it from its best-known view of the Air. Correct anything wrong.
> 2. Add a permanent §13 (or appropriate section) to this file that mirrors the
>    `mac-studio-primary.md §14` pattern: a 3-row summary table + a pointer to
>    [setup/runtime-compatibility.md](setup/runtime-compatibility.md). This becomes
>    the canonical "setup docs exist; here's where" entry in your operator file.
> 3. Remove this WRITE EXCEPTION blockquote AND the `written_by:` frontmatter field.
>    Commit as `coord(macbook-air-secondary): re-assert ownership after 2026-05-21
>    setup-folder cross-write`.
>
> Also reconcile the two earlier Studio-authored notes below (2026-05-20 bootstrap
> + P22.markers) if you haven't already.

> NOTE — bootstrap: this file was authored from the Studio side on 2026-05-20
> to seed the coordination layer. On the Air's next session, populate the
> `hostname_hint` and `worktree_layout[].path` fields in the frontmatter
> and remove this note. Until then, treat the frontmatter as the Studio's
> best-known view, not the Air's self-report.

> NOTE — 2026-05-20 Studio-authored update (operator-authorized): The Studio
> wrote this update at Asif's explicit request (chat session
> `f0aba7bb-72f6-440f-b6c9-bf957323ec8c`) to unblock the Air after Studio
> shipped the P22.markers framework fix. This is a one-time protocol exception;
> on the Air's next session, the Air re-asserts ownership by writing the
> next frontmatter update itself per §12.

> ⚠️ **CRITICAL — P22.markers framework fix shipped 2026-05-20.**
>
> The Studio shipped commit [`5201b54`](https://github.com/asifhussain60/Journal/commit/5201b54)
> on `book/asaas-al-taveel` fixing a systematic Phase 0b page-marker stripping
> defect. The defect was discovered during asaas Phase 0b post-mortem on the
> same day: 58 of 416 `<!-- page N -->` HTML anchors were stripped across 10
> of 49 chunked refinement windows; body content preserved but page-anchoring
> metadata lost. Affects every book that ran Phase 0b before 2026-05-20T16:30Z,
> **including KaR**.
>
> Before proceeding to Phase 0e, the Air MUST:
>
> 1. Cherry-pick `5201b54` (4 files: `_authoring.py`, `audit_page_markers.py`,
>    and 2 test files) onto `book/kitab-al-riyad` — see §4 below.
> 2. Run `python3 scripts/podcast/audit_page_markers.py --book kitab-al-riyad`
>    and review the per-window breakdown.
> 3. Decide on remediation per the §4 decision tree.
>
> Without this audit, KaR's downstream phases (content-range enforcement,
> per-page citation accuracy, operator navigation) inherit the metadata
> defect silently.

---

## 0. Session start — run this first, every time

```bash
cd <Air's repo path>                # e.g., /Users/asifhussain/PROJECTS/journal
git checkout book/kitab-al-riyad

# Sync from remote
git fetch --all --prune
git pull --ff-only

# Confirm my assignment from canonical source
git show origin/develop:_workspace/plan/operators/assignments.md

# Read this file fresh from current branch
cat _workspace/plan/operators/macbook-air-secondary.md

# Get authoritative phase/status
jq '{phase, phase_status, last_completed_phase, last_error}' \
    content/podcast/library/books/kitab-al-riyad/_system/orchestrator-state.json
```

---

## 1. Identity

- **Machine**: MacBook Air
- **Role**: secondary — supplementary podcast-pipeline machine
- **Hostname**: (populate on first Air-side run)
- **Marker**: `~/.machine-id` contains `macbook-air-secondary` (must be
  created on the Air machine; not yet bootstrapped from Studio)
- **Operator**: Asif Hussain

---

## 2. Current book — Kitāb al-Riyāḍ (كتاب الرياض)

The pilot book for the podcast pipeline — the corpus that surfaced most of
the orchestrator bugs (P5.x, P6.5) currently tracked on
`feat/podcast-w1-foundation`.

---

## 3. Current state snapshot (re-verify on every session — do not trust this section)

`last_verified_at: 2026-05-20T10:30:00Z`. At that moment, on `origin/book/kitab-al-riyad`:

- **HEAD**: `ec442f7 podcast(kitab-al-riyad): per-book scaffolding + 2 title tightenings (no LLM)`
- **phase**: `0e`
- **phase_status**: `pending` (next phase ready to start)
- **last_completed_phase**: `0d`
- **last_error**: `null`

Recent commit story:
```
ec442f7  per-book scaffolding + 2 title tightenings (no LLM)               ← HEAD
e8163a2  fix(podcast/scripts): accept optional letter suffix in chapter filename regex
76adac5  Phase 0d complete — ch13 (Bāb 10) + state flipped to 0e
bdc7a04  Phase 0d advance — Bāb 9 complete (ch12b + 2 contracts)
517b70d  Phase 0d advance — bābs 4-8 complete + ch11a partial of bāb 9
b59b4d8  Phase 0c phonetic complete + Phase 0d partial (4/10 chapters segmented)
29e7f85  phase 0c phonetic pass (chunked)
09899d9  operator transcript review — approved with content-range 52–232 + bāb/§ naming
4fafc05  add §6 abwāb/fusūl translation collision + §7 content range to operator-review
f4e7970  halt after Phase 0b for operator transcript review
```

The Air has driven 0c (Arabic phonetic), 0d (chapter segmentation; 13
chapters with contracts), plus `_system/registry.md` / `enrichment-whitelist.md` /
`mangle-map.md` / `meta-prose-tells.md` populated. All three validators pass clean.

**Why no-longer-HOLDING (2026-05-20T17:30Z)**: operator-imposed pause lifted
once Studio's asaas Phase 0b post-mortem completed and the P22.markers
framework fix landed. KaR's framework dependency (page-marker preservation)
is now resolved — the Air can resume, but must first audit and decide on
KaR's existing Phase 0b output (see ⚠️ note above + §4 plan).

---

## 4. Resume action plan (updated 2026-05-20 — P22.markers prerequisite added)

The Air is at the **0d→0e boundary** with one prerequisite: audit KaR's
Phase 0b page-marker preservation (per the ⚠️ note above), then decide on
remediation, THEN proceed to 0e.

### 4.1 — Session start (§0 protocol)

```bash
cd <Air's repo path>                # e.g., /Users/asifhussain/PROJECTS/journal
git checkout book/kitab-al-riyad

# Sync from remote (picks up Studio's P22.markers framework commit + this update)
git fetch --all --prune
git pull --ff-only

# Authoritative phase/status
jq '{phase, phase_status, last_completed_phase, last_error}' \
    content/podcast/library/books/kitab-al-riyad/_system/orchestrator-state.json
```

### 4.2 — Cherry-pick the P22.markers framework fix + this coord update

Studio committed two relevant commits on `book/asaas-al-taveel`:

1. `5201b54` — the P22.markers framework fix (4 files, pure framework code)
2. `0844e1e` — this Studio-authored coord-doc update (1 file —
   the Air's own operator file at `_workspace/plan/operators/macbook-air-secondary.md`)

Both cherry-pick cleanly onto `book/kitab-al-riyad`. The 2nd one brings
this file's updates into the Air's local working tree, so future `cat`
on this path returns the up-to-date instructions (today the Air operator
is reading these instructions from `origin/book/asaas-al-taveel` via
`git show` because that's where Studio wrote them):

```bash
# Confirm both commits exist on origin
git log --oneline -10 origin/book/asaas-al-taveel | grep -E "5201b54|0844e1e"

# Cherry-pick both onto KaR (in chronological order: framework, then coord)
git cherry-pick 5201b54 0844e1e

# Sanity-check the 5 files landed (4 framework + 1 coord)
git diff HEAD~2 HEAD --stat
# Should show:
#   scripts/podcast/_authoring.py                                 | ~70 lines (+51/-19)
#   scripts/podcast/audit_page_markers.py                         | ~213 lines (NEW)
#   scripts/podcast/tests/test_audit_page_markers.py              | ~180 lines (NEW)
#   scripts/podcast/tests/test_phase_0b_preserves_page_markers.py | ~140 lines (NEW)
#   _workspace/plan/operators/macbook-air-secondary.md            | ~190 lines (+190/-24)

# Verify the regression fixture passes (sanity-check the merge didn't break it)
python3 -m unittest scripts.podcast.tests.test_phase_0b_preserves_page_markers -v
# Expected: 8/8 pass
python3 -m unittest scripts.podcast.tests.test_audit_page_markers -v
# Expected: 22/22 pass
```

If `git cherry-pick 0844e1e` produces a conflict (because the Air has
also edited its own file in parallel since 2026-05-20T10:30Z), resolve
manually — Studio's view of frontmatter is captured under
`current_phase_status_summary` and `next_action`, but the Air's own
self-report takes precedence on any field describing the Air's machine
state (hostname, paths). Then `git cherry-pick --continue`.

### 4.3 — Audit KaR Phase 0b page markers

```bash
python3 scripts/podcast/audit_page_markers.py --book kitab-al-riyad
```

Three outcomes:

- **Exit 0 (clean):** All 254 raw page markers preserved in
  `refined-english.md`. No remediation needed. Proceed to §4.5.
- **Exit 1 (defective):** Per-window breakdown table will list which
  chunked refinement windows stripped, hallucinated, or duplicated
  markers. Go to §4.4.
- **Exit 2 (prereq missing):** Either `raw-extract.md` or
  `refined-english.md` is absent. Should not happen — KaR's 0a and 0b
  both shipped. Investigate before proceeding.

### 4.4 — Remediate (if §4.3 exits 1)

Decision tree based on audit results:

| Defect scope | Recommended action |
|---|---|
| ≤2 windows lost markers, no hallucinations | **Accept the defect.** Document the affected pages in `_system/registry.md`. Proceed to §4.5. Per-page citation accuracy degraded for those pages only; no body content lost. |
| 3–10 windows defective (similar to asaas pattern) | **Re-run affected windows** against the fixed prompt. Delete `_chunks/0b/win-NNN.out.md` for each defective window, then re-run `--resume kitab-al-riyad`. Cost: about $0.50 per window. Re-audit afterward. |
| Hallucinated markers present | **Hard halt — must remediate.** Hallucinated markers cause Loop N citation drift downstream. Identify the affected window via the audit breakdown, delete its `.out.md`, re-run. |
| >10 windows defective | **Re-run all of Phase 0b** with the fixed prompt. Cost: about $5–8. Most expensive option but cleanest baseline. |

To re-run a specific window:

```bash
# Identify the defective window from the audit output (e.g., win-003)
rm content/podcast/library/books/kitab-al-riyad/_system/source/text/_chunks/0b/win-003.out.md

# Resume — the orchestrator picks up only the missing .out.md files
python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad

# Re-audit
python3 scripts/podcast/audit_page_markers.py --book kitab-al-riyad
# Repeat until exit 0
```

### 4.5 — Verify pre-0e artifacts intact

```bash
python3 scripts/podcast/check_chapter_set.py content/podcast/library/books/kitab-al-riyad --format text
python3 scripts/podcast/check_lineage.py
python3 scripts/podcast/validate_registry.py --registry content/podcast/library/books/kitab-al-riyad/_system/registry.md
```

These must pass clean before Phase 0e.

### 4.6 — Resume into Phase 0e

```bash
python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad
```

Phase 0e is chunked `claude -p` per-chapter; expect 1200s shell-out cycles
same as 0d. Multiple `--resume` rounds expected. KaR has 13 chapters, so
13 enrichment passes total.

### 4.7 — After Phase 0e

Per pipeline overview (§9): next stop is Phase 0f operator gate (persona,
tier, series_pattern review). For KaR: `series_pattern: recursive_scaffold`
already declared in `_system/registry.md`; Mentor+Student persona implied
by the audience; long-form tier already set in `state.json.config`. The 0f
gate should be a confirmation, not a fresh decision.

---

## 5. Don't touch (collision surfaces)

- **`content/podcast/library/books/asaas-al-taveel/**`** — Studio owns this
- Branch **`book/asaas-al-taveel`** — no checkout, no merge, no rebase onto
- **`mac-studio-primary.md`** — Studio writes this; I only read it
- **`coordination-protocol.md`** — read-only for all machines
- **`content/babu-memoir/**`** and **`skills-staging/journal/**`** —
  memoir, separate scope
- Shared-infra zones — see [coordination-protocol.md §6](coordination-protocol.md)

---

## 6. Concurrent peer — Mac Studio (primary)

- **Owns**: `book/asaas-al-taveel`
- **Status (last verified 2026-05-20T17:30:00Z)**: HOLDING-FOR-FRAMEWORK-FIX —
  Studio is heads-down on framework code work on `book/asaas-al-taveel`
  (P22.impl, P4.10, P6.5, P23.\*). After framework work lands, Studio
  resumes asaas Phase 0b re-run + Phase 0c.
- **HEAD (Studio's branch)**: `5201b54 podcast(P22.markers): fix Phase 0b page-marker stripping defect`
  (plus possibly more framework commits by the time Air syncs — pull fresh).
- **Anthropic quota**: With both machines on different framework-prereq
  paths, quota contention is minimal until both are running LLM-heavy phases
  simultaneously. Per §8, share is 50/50 if both go ACTIVE on LLM-spending
  work at the same time.
- Read the Studio's view via:
  ```bash
  git show origin/book/asaas-al-taveel:_workspace/plan/operators/mac-studio-primary.md
  ```

---

## 7. Known orchestrator bugs

See [coordination-protocol.md §12](coordination-protocol.md). Quick reference
of bugs Air is most likely to hit on KaR's remaining phases (0e → 0g):

1. **Phase 0b page-marker stripping (P22.markers)** — FIXED 2026-05-20 in
   commit [`5201b54`](https://github.com/asifhussain60/Journal/commit/5201b54)
   on `book/asaas-al-taveel`. Cherry-pick required per §4.2 above. KaR's
   existing 0b output may carry the defect; audit via
   `audit_page_markers.py` per §4.3 and remediate per §4.4 if so.
2. **1200s `claude -p` timeout** — expected on 0e/0g. Just resume.
3. **Stale `phase_status=running`** — flip to `failed` before `--resume`.
4. **Phase 0d source-toc fasl counts off-by-one** — already hit (Bāb 10
   declared 16 fusūl, actual 15). Tolerable; 0d is already past.
5. **Cost-ledger silent fail (P6.5)** — Studio is queued to fix this on
   the current framework work. Until then, expect `cost-ledger.jsonl` to
   be empty for KaR's remaining phases. Will retroactively reconstruct
   nothing per `P6.5.retroactive` (accepted one-time gap).

---

## 8. Quota allocation

- **Anthropic share**: 0.5 (half of monthly quota for KaR)
- **Azure**: KaR's 0a is already complete; no Azure usage on resume

If the Studio finishes asaas Phase 0b and Asif un-holds KaR Phase 0c, both
machines share Anthropic at 50/50.

---

## 9. Pipeline overview

Same as [mac-studio-primary.md §9](mac-studio-primary.md). KaR is currently at
the **0d→0e boundary** (Phase 0b, 0c, 0d already shipped; P22 gate cleared
2026-05-19 via `09899d9`). Next phase ahead: 0e enrichment → 0f operator
gate → 0g per-chapter authoring.

The Air's KaR position is parallel to Studio's asaas Phase 0c path, just
several phases ahead. Whichever machine reaches Phase 0g first surfaces
the per-chapter authoring + challenger-convergence pattern for the other
to mirror.

---

## 10. Slash commands & agents

Same as [mac-studio-primary.md §10](mac-studio-primary.md).

---

## 11. Asif's conventions

See [coordination-protocol.md §13](coordination-protocol.md).

---

## 12. Pause-and-handoff

When Air finishes a phase or hits a pause:

1. Re-read `orchestrator-state.json`.
2. Update **this file's** frontmatter only:
   `last_verified_at`, `current_phase`, `current_phase_status_summary`,
   `next_action`, `status_tag`.
3. `git commit -m "coord(macbook-air-secondary): update operator state @ phase <X>"`
4. The post-commit hook auto-pushes.
5. Write `## Project Status` back to Asif so he can decide whether to wake
   the Studio's loop or let it continue.
