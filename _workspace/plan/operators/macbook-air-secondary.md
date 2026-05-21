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
status_tag: PER-CHAPTER-RUNNING
current_phase: "per-chapter"
current_phase_status_summary: |
  Phases 0a–0f complete; Phase 0g (per-chapter authoring + challenger convergence)
  in flight under Asif's direct drive.

  Shipped this run:
  - EP10 motion-stillness-hyle-and-form — SHIP-WITH-CAUTION (commit
    [4ecafff](https://github.com/asifhussain60/Journal/commit/4ecafff), iter=3
    fix=4 P0=0 P1=2 P2=2).

  In-flight:
  - EP14 prophets-as-teachers-monotheism-and-the-ranks — orchestrator PID 68721
    started 2026-05-21T12:39Z; currently authoring framing via `claude -p`.
    The initial attempt at 12:33Z failed because `build_episode_txt.py`
    rejected episode_id `EP14b-...` (regex requires `EP##-<slug>`, digits only).
    Asif fixed in commit [562b7d5](https://github.com/asifhussain60/Journal/commit/562b7d5)
    (X3) — strip letter suffix via `ch(\d+)`. Mid-flight artifacts cleaned in
    [b5e3f5e](https://github.com/asifhussain60/Journal/commit/b5e3f5e); state.json reset.

  Six KaR chapters carry letter suffixes (ch01a, ch03a, ch04b, ch05c, ch13a, ch14b)
  so the X3 fix unblocks all of them. Twelve episodes remain after EP14.

  Known active orchestrator bug — cost-ledger silent fail with
  `AttributeError("module 'datetime' has no attribute 'UTC'")` on every
  `_run_claude_p` call. Python 3.9 vs 3.11 (`datetime.UTC` is 3.11+). Spend on
  this run NOT tracked; estimate via wall-clock + chapter count. See
  [coordination-protocol.md §12 P6.5].
next_action: |
  Monitor PID 68721; on quiesce read
  `content/podcast/library/books/kitab-al-riyad/_system/orchestrator-state.json`
  for current phase/status. Asif drives 0g manually from this point.

  Pending sync tasks deferred until the orchestrator window closes (collision
  risk during active per-chapter writes):
    (a) merge `origin/develop` → `book/kitab-al-riyad` to absorb the new
        `_workspace/plan/operators/setup/` folder + asaas-side coord updates
        + Studio §13 Azure registry;
    (b) reconcile the 2026-05-21T11:50Z WRITE EXCEPTION blockquote that arrives
        on this file via that merge (remove block + `written_by` field);
    (c) add permanent §13 in this file mirroring
        [mac-studio-primary.md §14](mac-studio-primary.md): 3-row summary table +
        pointer to `setup/runtime-compatibility.md`;
    (d) update per-Air row of `setup/machines.md` to reflect current phase
        (per-chapter, EP10 shipped, EP14 in flight).
anthropic_share: 0.5
last_verified_at: 2026-05-21T12:45:00Z
last_updated: 2026-05-21
response_conventions: see _workspace/plan/response-conventions.md (BLUF format,
  AskUserQuestion ordering, halt-and-surface pattern, cross-machine awareness)
---

# MacBook Air (secondary) — operator index

**This file is written ONLY by `macbook-air-secondary`.** The Studio reads
it but never writes it. See [coordination-protocol.md §1](coordination-protocol.md).

> **State as of 2026-05-21T12:45Z** — frontmatter `current_phase_status_summary`
> + `next_action` carry the live status. Body sections §3 and §4 below reflect
> the 2026-05-20 baseline (pre-Phase-0g) and have NOT yet been rewritten for
> the post-merge architecture (setup/ folder absorption + §13 multi-operator
> mirror are deferred — see frontmatter `next_action`). Trust frontmatter +
> `state.json` over body §3/§4 until the deferred sync commit lands.

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
