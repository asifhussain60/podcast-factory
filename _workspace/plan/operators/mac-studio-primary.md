---
schema_version: 1
machine_id: mac-studio-primary
role: primary
description: Primary machine for autonomous podcast-pipeline conversions
hostname_hint: Asifs-Mac-Studio.local
operator: Asif Hussain (asifhussain60@gmail.com)
worktree_layout:
  - path: /Users/ahmac/Code/Journal
    branch: main
  - path: /Users/ahmac/Code/Journal-feat-w1
    branch: feat/podcast-w1-foundation
  - path: /Users/ahmac/Code/Journal-book-asaas
    branch: book/asaas-al-taveel
current_branch: book/asaas-al-taveel
current_book: asaas-al-taveel
current_book_dir: content/podcast/library/books/asaas-al-taveel
authoritative_state_path: content/podcast/library/books/asaas-al-taveel/_system/orchestrator-state.json
status_tag: HOLDING-FOR-OPERATOR-GATES
current_phase: "0b"
current_phase_status_summary: |
  Phase 0b complete 2026-05-20T13:38:21Z (refined-english.md 10329 lines / 759 KB).
  Audit revealed Phase 0b prompt-template defect: 58 of 416 page markers stripped across
  7 of 49 chunked windows (no content loss; metadata only). Plan revised to "complete
  Phase 0 perfectly on the hardest book before tackling remaining tasks" with budget
  envelope raised to $130 hard cap (from $50 default) and SHIP-READY per-chapter
  challenger verdict required. Acceptance criteria extended with 45 new rows in
  acceptance-criteria.md (P22.markers ×11, P23 ×13, P9.5 SHIP-READY ×14, STAIRCASE ×7).

  MERGE TO DEVELOP COMPLETE 2026-05-21: book/asaas-al-taveel merged into develop
  (merge commit 4597a72) — Studio's Phase 0a–0b work + framework cherry-picks
  (P22.markers fix 5201b54, two coord-doc commits) now landed. No conflicts during
  merge (the Air's macbook-air-secondary.md updates and Studio's mac-studio-primary.md
  updates did not collide). Gate-4 verification: 30 tests OK (test_phase_0b_preserves_page_markers
  + test_audit_page_markers), Phase 0f import clean. The Air symmetrically merged
  book/kitab-al-riyad earlier the same day (commit e122fa0).

  Awaiting (a) operator Azure setup (Text Analytics F0 resource + env vars per P23.azure-setup)
  and (b) operator §§1-8 of operator-review.md. Framework code fixes resume once both gate.
next_action: |
  Operator (1) creates Azure Text Analytics F0 resource per P23.azure-setup, P23.azure-tier-doc-intel,
  P23.azure-tier-translator — see docs/podcast/azure-setup.md (to be authored as part of P23.docs);
  (2) finishes operator-review.md §§1-8 review.
  Claude then drives: framework code fixes (P22.impl, P4.10, P6.5, P23 client/integration/
  tests/fallback/cost-ledger) on feat/podcast-w1-foundation; merge to book/asaas-al-taveel;
  Phase 0b staircase re-run; Phase 0a.5 NER pre-seed integration; operator-review.md regenerated
  from NER; resume 0c → 0d → 0e → 0f → 0g (EP01 firm halt) → EP02-06.
anthropic_share: 0.5
last_verified_at: 2026-05-21T00:00:00Z
last_updated: 2026-05-21
---

# Mac Studio (primary) — operator index

**This file is written ONLY by `mac-studio-primary`.** The Air reads it but
never writes it. See [coordination-protocol.md §1](coordination-protocol.md).

---

## 0. Session start — run this first, every time

```bash
cd /Users/ahmac/Code/Journal-book-asaas  # the asaas worktree

# Sync from remote (does not touch other worktrees)
git fetch --all --prune
git pull --ff-only

# Confirm my assignment from canonical source
git show origin/develop:_workspace/plan/operators/assignments.md

# Read this file fresh from current branch
cat _workspace/plan/operators/mac-studio-primary.md

# Get authoritative phase/status — never trust the frontmatter above for decisions
jq '{phase, phase_status, last_completed_phase, last_error}' \
    content/podcast/library/books/asaas-al-taveel/_system/orchestrator-state.json
```

If `phase_status=running` and no orchestrator process is alive, the lock
is stale. See §4.

---

## 1. Identity

- **Machine**: Mac Studio
- **Role**: primary — designated for autonomous Azure-backed podcast
  conversions (per memory `project_primary_mac.md`, 2026-05-18).
- **Hostname**: `Asifs-Mac-Studio.local`
- **Marker**: `~/.machine-id` contains `mac-studio-primary`
- **Operator**: Asif Hussain

This machine's job is to **drive a book through the podcast pipeline
end-to-end autonomously**, stopping only at genuine operator gates.

---

## 2. Current book — Asaas al-Taʾwīl (أساس التأويل)

- **Author**: al-Qāḍī al-Nuʿmān (d. 974 CE), Fatimid jurist
- **Editor**: ʿĀrif Tāmir, 1960 Beirut edition
- **Source**: 416-page scanned image-only Arabic PDF
- **What it is**: foundational Fatimid esoteric exegesis (*taʾwīl*) of the
  prophetic narratives in the Qurʾān, organized around the *seven nāṭiqs*
  (Adam, Nūḥ, Ibrāhīm, Mūsā, ʿĪsā, Muḥammad, and the awaited Qāʾim) and
  the *asās* + *ḥujjas* under each. The seventh chapter (on the Qāʾim) is
  deliberately incomplete — al-Nuʿmān stopped because the Qāʾim has not
  yet come.
- **Why this book**: the pipeline's hardest test case — image-only Arabic
  OCR + recursive scaffold + heavy numeric/symbolic surface (7 nāṭiqs,
  12 ḥujjas, abjad ciphers). Plan reference: **P9.5 (Wave 3 corpus)**.

---

## 3. Current state snapshot (re-verify on every session — do not trust this section)

`last_verified_at: 2026-05-21T00:00:00Z`. At that moment:

- **book/asaas-al-taveel HEAD**: `5dae77c coord(macbook-air-secondary): amend §4.2 — also cherry-pick this coord commit`
- **develop HEAD**: `4597a72` (merge commit — book/asaas-al-taveel merged into develop today)
- **phase**: `0b`
- **phase_status**: `complete` (refined-english.md 10329 lines)
- **last_completed_phase**: `0b` (refined English; awaiting P22 operator transcript review)
- **last_error**: `null`

Recent commit story on book/asaas-al-taveel (unchanged from 2026-05-20):
```
5dae77c  coord(macbook-air-secondary): amend §4.2 — also cherry-pick this coord commit  ← HEAD
0844e1e  coord(macbook-air-secondary): unblock Air for KaR Phase 0e + P22.markers prereq
5201b54  podcast(P22.markers): fix Phase 0b page-marker stripping defect
699f115  plan: extend acceptance criteria for asaas SHIP-READY Phase 0 push
b144076  podcast(asaas-al-taveel): correct §2 defect diagnosis — page-marker stripping, not content loss
5eb8b5b  coord(mac-studio-primary): update operator state @ phase 0b → P22 gate
39564f1  podcast(asaas-al-taveel): halt after Phase 0b for operator transcript review
114fc63  podcast(asaas-al-taveel): phase 0b English refinement (chunked)
```

The narrative: phase 0a failed once (transient Azure Translator
`ConnectionRefused`); reset via `--retry-phase 0a` and succeeded on retry.
Phase 0b chunked English refinement completed (10329 lines), halted at the
P22 operator transcript-review gate per `halt after Phase 0b`. P22.markers
prompt-template defect fixed in-branch (5201b54) and cherry-picked to develop
by the Air on day 1. As of 2026-05-21 the full asaas branch is merged into
develop (no conflicts) — the Studio's Phase 0a–0b work is now part of develop's
canonical state alongside the Air's KaR work (merge commit e122fa0 earlier
the same day).

---

## 4. Resume action plan

Run in `/Users/ahmac/Code/Journal-book-asaas`.

```bash
# 4.1  Session-start protocol (§0 above)
# 4.2  Verify no orchestrator process is alive on this machine
pgrep -fa orchestrate_book.py    # should return nothing

# 4.3  If phase_status is still 'running', flip to 'failed'
jq '.phase_status = "failed" | .phases."0b".status = "failed"' \
    content/podcast/library/books/asaas-al-taveel/_system/orchestrator-state.json \
    > /tmp/o.json && mv /tmp/o.json \
    content/podcast/library/books/asaas-al-taveel/_system/orchestrator-state.json

# 4.4  Commit the lock reset
git add content/podcast/library/books/asaas-al-taveel/_system/orchestrator-state.json
git commit -m "podcast(asaas-al-taveel): clear stale 0b running lock"

# 4.5  Resume
python3 scripts/podcast/orchestrate_book.py --resume asaas-al-taveel
```

Expect phase 0b (English refinement, chunked `claude -p`) to die after
~4–5 work units due to the 1200s shell-out timeout. Just `--resume` again.
KaR's 0b took ~1.5h of wall-clock total.

---

## 5. Don't touch (collision surfaces)

- **`content/podcast/library/books/kitab-al-riyad/**`** — Air owns this
- Branch **`book/kitab-al-riyad`** — no checkout, no merge, no rebase onto
- **`macbook-air-secondary.md`** — Air writes this; I only read it
- **`coordination-protocol.md`** — read-only for all machines
- **`content/babu-memoir/**`** and **`skills-staging/journal/**`** —
  memoir, separate scope
- Shared-infra zones — see [coordination-protocol.md §6](coordination-protocol.md)

---

## 6. Concurrent peer — MacBook Air (secondary)

- **Owns**: `book/kitab-al-riyad`
- **Status (last verified 2026-05-19T19:06:50Z)**: HOLDING at Phase 0c
  (halted at P22 operator transcript review gate — KaR phase 0b refined-
  English output awaits Asif's review)
- **HEAD**: `f4e7970 podcast(kitab-al-riyad): halt after Phase 0b for operator transcript review`
- **Does not compete with Studio**: Air is idle on Anthropic quota; Studio
  has it to itself for asaas 0b–0e.
- Read the Air's view via:
  ```bash
  git show origin/develop:_workspace/plan/operators/macbook-air-secondary.md
  ```

---

## 7. Known orchestrator bugs

See [coordination-protocol.md §12](coordination-protocol.md). Quick reference
of bugs Studio is most likely to hit on asaas:

1. **1200s `claude -p` timeout** — expected during 0b/0c/0d/0e. Just resume.
2. **Stale `phase_status=running`** — the one I'm sitting on now (§4 fix).
3. **Azure Translator `ConnectionRefused`** — already hit on 0a; use
   `--retry-phase 0a`. Persistent failures → Azure portal.
4. **Cost-ledger `datetime.UTC` silent fail** (P6.5) — ignore.

---

## 8. Quota allocation

- **Anthropic share**: 0.5 (half of monthly quota for asaas)
- **Azure**: Studio drives 0a only for asaas (0a is already complete; no
  Azure usage until next book)

If the Air becomes ACTIVE on KaR simultaneously, both machines share
Anthropic at 50/50. If the Air stays HOLDING, Studio can spend freely.

---

## 9. Pipeline overview (what we're driving toward)

```
0a   Azure OCR + initial translation              → _system/source/text/raw-extract.md
0b   English refinement (chunked claude -p)       → _system/source/text/refined-english.md
P22  Operator transcript review (HUMAN)           → operator-review.md + content-range.md
0c   Arabic phonetic pass (chunked)               → _system/source/text/_phonetics.md
0d   Chapter segmentation                         → chapters/chNN-<slug>.txt + chapter-contracts/*
0e   Enrichment (bāb/fasl → concept-glossary)
0f   Operator gate (persona, tier, series, episodes)
0g   Per-chapter authoring                        → _system/episode-drafts/EP##-<slug>/{framing, …}
per-chapter  build_episode_txt.py (deterministic) → episodes/EP##-<slug>.txt
HUMAN  upload chapters/ as NotebookLM source; paste episodes/ into CUSTOMIZE; generate audio
HUMAN  drop transcript at transcripts/EP##-<slug>.transcript.txt
trainer  post-publish learning
merge    book → develop → main
```

Studio's next gate after asaas Phase 0b finishes is **P22 (operator
transcript review)** — same gate the Air is sitting at for KaR.

---

## 10. Slash commands & agents

| Command                | What it does                                                  | When                       |
|------------------------|---------------------------------------------------------------|----------------------------|
| `/podcast`             | full orchestrator skill — drives all phases                   | advance the pipeline       |
| `/extract-chapter`     | single-chapter → NotebookLM bundle                             | one-off, not mid-pipeline  |
| `/podcast-challenger`  | semantic audit (citations, phonetics, framing integrity)       | gate before NotebookLM upload (Phase per-chapter+) |
| `/init`, `/review`, `/security-review`, `/simplify`, `/verify` | standard Claude Code skills | as needed |

The `podcast-challenger` agent writes `_system/challenger-report.md` with
verdict `SHIP-READY` / `SHIP-WITH-CAUTION` / `BLOCKED`. Required gate in
`/podcast` Phase 4 before human-facing handoff.

---

## 11. Asif's conventions (apply in every response)

See [coordination-protocol.md §13](coordination-protocol.md). Briefly:

1. Every response ends with `## Project Status` (Work Completed + Work Pending mandatory).
2. AskUserQuestion: recommended option first, labeled "(Recommended)".
3. Asif IS Babu (memoir context only).
4. Terse responses, file:line refs, confirmation before destructive actions.

---

## 12. Pause-and-handoff

When Studio finishes a phase or hits a pause:

1. Re-read `orchestrator-state.json` (the truth).
2. Update **this file's** frontmatter only:
   `last_verified_at`, `current_phase`, `current_phase_status_summary`,
   `next_action`, `status_tag`.
3. `git commit -m "coord(mac-studio-primary): update operator state @ phase <X>"`
4. The post-commit hook auto-pushes.
5. Write `## Project Status` back to Asif so he can decide whether to wake
   the Air's holding loop on KaR Phase 0e or keep it paused.
