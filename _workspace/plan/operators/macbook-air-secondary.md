---
schema_version: 1
machine_id: macbook-air-secondary
role: secondary
description: Secondary machine for podcast-pipeline work; currently driving kitab-al-riyad
hostname_hint: (Air hostname — populate on first run from the Air)
operator: Asif Hussain (asifhussain60@gmail.com)
worktree_layout:
  - path: (TBD — the Air's repo path, e.g., /Users/asifhussain/PROJECTS/journal)
    branch: book/kitab-al-riyad
current_branch: book/kitab-al-riyad
current_book: kitab-al-riyad
current_book_dir: content/podcast/library/books/kitab-al-riyad
authoritative_state_path: content/podcast/library/books/kitab-al-riyad/_system/orchestrator-state.json
status_tag: HOLDING
current_phase: "0c"
current_phase_status_summary: phase 0b complete; halted at P22 for operator transcript review of refined-english.md
next_action: wait for Asif to complete P22 transcript review, then --resume 0c (Arabic phonetic pass)
anthropic_share: 0.5
last_verified_at: 2026-05-19T19:06:50Z
last_updated: 2026-05-20
---

# MacBook Air (secondary) — operator index

**This file is written ONLY by `macbook-air-secondary`.** The Studio reads
it but never writes it. See [coordination-protocol.md §1](coordination-protocol.md).

> NOTE — bootstrap: this file was authored from the Studio side on 2026-05-20
> to seed the coordination layer. On the Air's next session, populate the
> `hostname_hint` and `worktree_layout[].path` fields in the frontmatter
> and remove this note. Until then, treat the frontmatter as the Studio's
> best-known view, not the Air's self-report.

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

`last_verified_at: 2026-05-19T19:06:50Z`. At that moment:

- **HEAD**: `f4e7970 podcast(kitab-al-riyad): halt after Phase 0b for operator transcript review`
- **phase**: `0c`
- **phase_status**: `running` (intentionally — held at P22 operator gate)
- **last_completed_phase**: `0b` (completed 2026-05-19T19:06:50Z)
- **last_error**: `null`

Recent commit story:
```
f4e7970  halt after Phase 0b for operator transcript review            ← HEAD
543e530  phase 0b English refinement (chunked)
c5c87a4  chore: ignore _workspace/logs/ (orchestrator runtime logs)
32c2688  feat(podcast/P6.1-integration): wire cost-ledger into _authoring + _chunking
5eafdaa  feat(podcast/P5.2)+chore(plan): harden artifact check + close remaining blockers
c12ecd7  fix(podcast/P5.1): --permission-mode acceptEdits on claude -p invocations
```

---

## 4. Resume action plan

Waiting on **Asif's P22 transcript review** of:

- `content/podcast/library/books/kitab-al-riyad/_system/source/text/refined-english.md`
- (when complete) `_system/operator-review.md` + `_system/content-range.md`

Once Asif marks P22 complete (writes the review artifact + signals
go-ahead), the Air's next step is:

```bash
# Verify P22 artifacts exist
ls content/podcast/library/books/kitab-al-riyad/_system/operator-review.md
ls content/podcast/library/books/kitab-al-riyad/_system/content-range.md

# Resume into Phase 0c (Arabic phonetic pass)
python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad
```

Phase 0c is chunked `claude -p`; expect 1200s shell-out cycles same as 0b.

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
- **Status (last verified 2026-05-20T10:00:00Z)**: ACTIVE — Phase 0b
  resuming after stale-lock reset
- **HEAD**: `fa8c902 podcast(asaas-al-taveel): checkpoint phase 0b stale 'running' lock (SIGKILL)`
- **Competes for Anthropic quota** when both machines are ACTIVE. Air's
  HOLDING state means Studio currently has Anthropic to itself.
- Read the Studio's view via:
  ```bash
  git show origin/develop:_workspace/plan/operators/mac-studio-primary.md
  ```

---

## 7. Known orchestrator bugs

See [coordination-protocol.md §12](coordination-protocol.md). Quick reference
of bugs Air is most likely to hit on KaR's remaining phases (0c → 0g):

1. **1200s `claude -p` timeout** — expected on 0c/0d/0e. Just resume.
2. **Stale `phase_status=running`** — flip to `failed` before `--resume`.
3. **Phase 0d source-toc fasl counts off-by-one** — KaR already hit this
   (Bāb 10 declared 16 fusūl, actual 15). Tolerable.
4. **Cost-ledger silent fail** (P6.5) — ignore.

---

## 8. Quota allocation

- **Anthropic share**: 0.5 (half of monthly quota for KaR)
- **Azure**: KaR's 0a is already complete; no Azure usage on resume

If the Studio finishes asaas Phase 0b and Asif un-holds KaR Phase 0c, both
machines share Anthropic at 50/50.

---

## 9. Pipeline overview

Same as [mac-studio-primary.md §9](mac-studio-primary.md). KaR is currently at
the **P22 gate** between phases 0b and 0c.

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
