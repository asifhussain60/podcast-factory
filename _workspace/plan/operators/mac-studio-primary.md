---
schema_version: 1
machine_id: mac-studio-primary
role: primary
description: Primary machine for autonomous podcast-pipeline conversions
hostname_hint: Asifs-Mac-Studio.local
operator: Asif Hussain (asifhussain60@gmail.com)
worktree_layout:
  # NOTE: per index.md and coordination-protocol.md §9, single-worktree-per-machine
  # is the convention. The Studio currently holds three worktrees of the same repo;
  # `Journal-book-asaas` is the primary (book lane). The others are observational —
  # `Journal` (`dump` branch, 1 commit ahead of develop) and `Journal-feat-w1`
  # (`feat/operator-review-studio`, 7 commits ahead of develop — active operator-review
  # UI work). Asif decides whether to consolidate.
  - path: /Users/ahmac/Code/Journal-book-asaas
    branch: book/asaas-al-taveel
  - path: /Users/ahmac/Code/Journal-feat-w1
    branch: feat/operator-review-studio
  - path: /Users/ahmac/Code/Journal
    branch: dump
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

  SYNC 2026-05-21T11:10Z: pulled develop (now @ e7e9ac5 — Air's coord-doc cleanup
  v2 + studio-sync-prompt v3 + worktree-clarification commits 560f1b2, 083298b,
  f00776d, 774b002, 9896e3a) and merged into book/asaas-al-taveel (merge ed8c1d1,
  clean — no conflicts). Studio now sees: new _workspace/plan/operators/index.md
  dashboard, new _workspace/plan/book-queue.md pull-on-demand queue, new
  _workspace/plan/response-conventions.md BLUF spec, refactored coordination-protocol.md
  (v2 §14 concurrency + §15 WRITE EXCEPTION), new start-session.sh script. Operator
  files for both machines remain owned per §1 sole-write convention; no WRITE EXCEPTION
  applies to this file currently.

  AZURE GATE CLEARED 2026-05-21T11:30Z: operator gate (a) — Azure Text Analytics F0 +
  keychain wiring — is DONE. The Studio uses the existing `journal-language-market`
  resource (Kind: TextAnalytics, tier Free F0, region eastus, in `rg-journal-ai`).
  All three keychain entries are populated and the NER endpoint was verified live
  (HTTP 200 on a 1-sentence probe; recognized "al-Qadi al-Numan"→Person and
  "Cairo"→Location). Full Azure resource registry now lives in §13 of this file —
  future sessions read §13 to avoid re-discovering the wiring. See `infra/azure/`
  for the broader script-driven Azure stack (docintel + translator + speech already
  in use).

  Still awaiting (b) operator §§1-8 of operator-review.md. Framework code fixes
  resume once that gate clears. Air is paused per the 2026-05-21 sync; Studio is
  also paused pending Asif's explicit authorization to resume asaas Phase 0c
  (Arabic phonetic) or framework lane.
next_action: |
  Operator finishes §§1-8 of operator-review.md (the last remaining operator gate;
  gate (a) Azure setup cleared 2026-05-21 — see §13 of this file).
  Claude then drives: framework code fixes (P22.impl, P4.10, P6.5, P23 client/integration/
  tests/fallback/cost-ledger including new LanguageCreds + get_language() resolver
  in scripts/podcast/_azure.py, plus Language section in infra/azure/store-keychain-keys.sh
  and azure-config.env) on feat/podcast-w1-foundation; merge to book/asaas-al-taveel;
  Phase 0b staircase re-run; Phase 0a.5 NER pre-seed integration (now unblocked —
  Language credential is live); operator-review.md regenerated from NER;
  resume 0c → 0d → 0e → 0f → 0g (EP01 firm halt) → EP02-06.
anthropic_share: 0.5
last_verified_at: 2026-05-21T11:30:00Z
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

`last_verified_at: 2026-05-21T11:10:47Z`. At that moment:

- **book/asaas-al-taveel HEAD**: `ed8c1d1 merge develop → book/asaas-al-taveel — pick up coord-doc cleanup + worktree clarification (2026-05-21)`
- **develop HEAD**: `e7e9ac5` (merge book/kitab-al-riyad → develop — studio-sync-prompt v3, authored by Air)
- **phase**: `0b`
- **phase_status**: `halted-for-transcript-review` (refined-english.md 10329 lines)
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
5. Write a BLUF-format response per [response-conventions.md](../response-conventions.md)
   so Asif can decide whether to wake the Air's holding loop on KaR Phase 0e or keep it paused.

---

## 13. Azure resources (verified 2026-05-21)

**Do NOT re-discover this wiring on every session — read this section, then jump straight to use.**

The Studio drives Azure-backed phases (0a OCR + translation; 0a.5 NER pre-seed) against
the resource group [`rg-journal-ai`](https://portal.azure.com/#@/resource/subscriptions/3440564d-c056-4173-bec6-7af92dbece77/resourceGroups/rg-journal-ai/overview)
in subscription `Journal AI — primary` (ID `3440564d-c056-4173-bec6-7af92dbece77`),
region `eastus`. Resource names + non-secret config live in
[infra/azure/azure-config.env](../../../infra/azure/azure-config.env).

### Resources in use

| Resource | Type / SKU | Used by phase | Endpoint | Verified |
|---|---|---|---|---|
| `journal-docintel` | Document Intelligence | 0a (OCR) | (in azure-config.env) | in use since 2026-05-19 (Phase 0a on asaas + KaR) |
| `journal-translator` | Translator, S1 | 0a (AR→EN) | (in azure-config.env) | in use since 2026-05-19 |
| `journal-language-market` | Language, Kind `TextAnalytics`, tier Free F0 | 0a.5 NER pre-seed (pending framework integration) | `https://journal-language-market.cognitiveservices.azure.com/` | 2026-05-21: HTTP 200; correctly tagged "al-Qadi al-Numan"→Person, "Cairo"→Location |
| `journalpodcaststorage` | Storage account | (ancillary; not pipeline-critical) | — | exists; not currently called |

### Keychain entries on the Studio

Convention from [infra/azure/store-keychain-keys.sh](../../../infra/azure/store-keychain-keys.sh):
`azure-<app>-<resource>-<field>` with `<app>` = `journal`. Resolution priority in
[scripts/podcast/_azure.py](../../../scripts/podcast/_azure.py) `_resolve()`: env var
wins (for CI), Keychain is the local-Mac fallback.

| Service name | Type | Value summary |
|---|---|---|
| `azure-journal-docintel-endpoint` | public | (pre-existing) |
| `azure-journal-docintel-key1` | secret | (pre-existing) |
| `azure-journal-docintel-region` | public | `eastus` |
| `azure-journal-translator-endpoint-text` | public | (pre-existing) |
| `azure-journal-translator-key1` | secret | (pre-existing) |
| `azure-journal-translator-region` | public | `eastus` |
| `azure-journal-language-endpoint` | public | `https://journal-language-market.cognitiveservices.azure.com/` |
| `azure-journal-language-region` | public | `eastus` |
| `azure-journal-language-key1` | secret | 84 chars (newer Base64 format; stashed 2026-05-21) |

### Quick verification (no key ever echoed)

```bash
# Run from anywhere on the Studio:
ENDPOINT=$(security find-generic-password -s azure-journal-language-endpoint -w)
KEY=$(security find-generic-password -s azure-journal-language-key1 -w)
curl -sS -o /dev/null -w "HTTP %{http_code}\n" \
    -X POST "${ENDPOINT}language/:analyze-text?api-version=2023-04-01" \
    -H "Ocp-Apim-Subscription-Key: ${KEY}" \
    -H "Content-Type: application/json" \
    -d '{"kind":"EntityRecognition","analysisInput":{"documents":[{"id":"1","language":"en","text":"Cairo."}]}}'
unset KEY
# Expect: HTTP 200
```

If this prints `HTTP 200`, all three Azure resources are reachable from the Studio's
credentials and you can proceed to any phase that needs them.

### Framework lane TODO (deferred to feat/podcast-w1-foundation)

The Language credential is in the keychain but the framework doesn't read it yet. P23 includes:

- Extend [scripts/podcast/_azure.py](../../../scripts/podcast/_azure.py) with
  `LanguageCreds` dataclass + `get_language()` resolver (mirror of `get_docintel()`/`get_translator()`).
- Extend [infra/azure/store-keychain-keys.sh](../../../infra/azure/store-keychain-keys.sh)
  with a Language section so a fresh Mac can `bootstrap` without manual `security` commands.
- Add `LANGUAGE_NAME="journal-language-market"` + `ENABLE_LANGUAGE="true"` to
  [infra/azure/azure-config.env](../../../infra/azure/azure-config.env).
- Wire `get_language()` into Phase 0a.5 NER pre-seed (proper-noun pre-population for the
  refined-English → operator-review.md pipeline).

### Operator-gate status (updated 2026-05-21)

- Gate (a) Azure Text Analytics F0 + keychain wiring: ✅ DONE 2026-05-21
- Gate (b) §§1-8 of [operator-review.md](../../../content/podcast/library/books/asaas-al-taveel/operator-review.md): pending operator
- Framework lane (P22.impl, P4.10, P6.5, P23): pending operator's go after gate (b)
- Phase 0b STAIRCASE re-run: pending framework lane
- Phase 0a.5 NER pre-seed integration: pending framework lane (credential is ready)
- Phase 0c (Arabic phonetic): pending all the above

---

## 14. Multi-operator runtime compatibility (verified 2026-05-21)

**Use Claude Code (this) for the podcast pipeline. Do NOT propose other Anthropic UIs as drop-in replacements without re-testing.** Capability probes against alternatives:

| UI | Verdict | Reason |
|---|---|---|
| **Claude Code in VS Code** | ✅ FULLY (canonical) | Live Mac shell, Keychain access, `claude -p` shell-out works, long-running orchestrator supervision, file edit + git push, skill system. This is what mac-studio-primary uses. |
| **Claude Code desktop app (the "Code" tab of the unified Anthropic Mac app)** | ✅ Expected FULLY (not directly probed but same model, same tool surface) | Same harness as VS Code form factor; only differences are IDE integration signals (`<ide_opened_file>`, inline diff review). Coordination work is form-factor-agnostic. |
| **Cowork (the "Cowork" tab of the unified Anthropic Mac app — async project workspace)** | 🔴 NOT AT ALL | Probed 2026-05-21 via 13-step diagnostic. Architectural blockers, not configurable — see below. |
| **GitHub Copilot Chat in VS Code** | ❓ NOT PROBED | Likely similar architectural issues (no `claude -p` auth, different LLM-call model). Would need equivalent diagnostic before use. |

### Cowork-specific findings (do not re-discover)

Cowork's runtime is an **isolated Linux aarch64 sandbox VM**, NOT the Mac host. Its desktop-app UI runs on the Mac, but each task's `bash` executes in a fresh ephemeral container with a partial repo snapshot mounted. Hard blockers:

1. **`pwd` is `/sessions/<random-slug>`**, `USER` is sandbox-named (not `ahmac`), `TERM_PROGRAM` + `CLAUDECODE` are empty.
2. **No `security` binary** → no macOS Keychain → no Azure credential resolution → Phase 0a/0a.5 calls are impossible.
3. **`/usr/local/bin/claude` v2.1.142 exists in the sandbox but returns "Not logged in"** — cannot inherit the Mac's Claude Code authentication. Phases 0b/0c/0d/0e/0g shell out to `claude -p` from Python; this is a hard blocker.
4. **Per-call sandbox lifecycle** — each bash call is independent, ~45s cap, no env carryover between calls, no mechanism to supervise a 1.5–10h orchestrator across turns. `nohup` works within one call but the process dies at VM teardown.
5. **Only the `dump` worktree (`/Users/ahmac/Code/Journal`) is mounted by default** — `book/asaas-al-taveel` is invisible to Cowork even read-only.
6. **Sandbox Python is 3.10**, below the 3.11 floor flagged in [coordination-protocol.md §12](coordination-protocol.md) (cost-ledger silently fails).
7. **Separate memory store** — Cowork's memory lives under `…/spaces/<id>/memory/`, separate from Claude Code's `~/.claude/projects/-Users-ahmac-Code-Journal/memory/`. No continuity.

### What Cowork CAN reasonably do here

- Adjacent content work against whatever branch is mounted (currently `dump`): drafting prompt revisions, reviewing shipped transcripts, formatting deliverables.
- One-off snapshot analyses of book output after a phase ships and gets merged to `dump` or `develop`.
- NOT live coordination, NOT orchestrator driving, NOT keychain-dependent tasks.

### If you want a second operator on this Mac

Spawn a **second Claude Code session** in a separate terminal / VS Code window on a **different worktree** (e.g., a read-only review session on [/Users/ahmac/Code/Journal-feat-w1](file:///Users/ahmac/Code/Journal-feat-w1) running on `feat/operator-review-studio`). NOT Cowork. The two Claude Code sessions can both:
- Read Mac Keychain
- Shell out to `claude -p` with the Mac's auth
- Supervise long-running processes
- Share the `~/.claude/projects/.../memory/` memory store

Per [coordination-protocol.md §1](coordination-protocol.md), both sessions would still write only to their own operator file — second-Claude-Code sessions on the same `machine_id` would coordinate via working-directory/branch separation, not separate operator files.

### Capability probe (re-runnable)

The full 13-step probe prompt that produced the 2026-05-21 verdict is preserved in
session history; the abbreviated version is: "from inside the target UI, run `pwd`,
`echo $TERM_PROGRAM`, `claude -p 'PONG'`, `security find-generic-password -s azure-journal-language-endpoint -w`,
`python3 --version`, `git rev-parse --abbrev-ref HEAD`, and verify all five succeed
on the Mac host, not a sandbox." Any UI that fails any of those five is unsuitable
for the pipeline.
