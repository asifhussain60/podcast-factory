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
current_phase: "0e"
current_phase_status_summary: phases 0a–0d complete; 0e (enrichment) pending; Air is operator-held to give Studio sole Anthropic quota during asaas Phase 0b
next_action: await Asif's signal to resume; then --resume 0e (enrichment pass — bāb/fasl → concept-glossary)
anthropic_share: 0.5
last_verified_at: 2026-05-20T10:30:00Z
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

**Why HOLDING**: operator-imposed pause so the Studio has sole Anthropic
quota for asaas Phase 0b. Not blocked by any pipeline gate.

---

## 4. Resume action plan

The Air is paused at the **0d→0e boundary** awaiting Asif's signal. When
the Studio's asaas Phase 0b completes (or Asif explicitly un-holds the Air),
the next step is:

```bash
# Verify pre-0e artifacts are intact (13 chapters + 13 contracts)
python3 scripts/podcast/check_chapter_set.py content/podcast/library/books/kitab-al-riyad --format text
python3 scripts/podcast/check_lineage.py
python3 scripts/podcast/validate_registry.py --registry content/podcast/library/books/kitab-al-riyad/_system/registry.md

# Resume into Phase 0e (enrichment pass — bāb/fasl → concept-glossary)
python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad
```

Phase 0e is chunked `claude -p` per-chapter; expect 1200s shell-out cycles
same as 0d. Multiple `--resume` rounds expected.

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
of bugs Air is most likely to hit on KaR's remaining phases (0e → 0g):

1. **1200s `claude -p` timeout** — expected on 0e/0g. Just resume.
2. **Stale `phase_status=running`** — flip to `failed` before `--resume`.
3. **Phase 0d source-toc fasl counts off-by-one** — already hit (Bāb 10
   declared 16 fusūl, actual 15). Tolerable; 0d is already past.
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
