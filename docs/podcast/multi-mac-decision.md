# Multi-Mac architecture — decision

**Resolves:** Open Question Q1 in [`_workspace/plan/podcast-plan.yaml`](../../_workspace/plan/podcast-plan.yaml) (`open_questions[Q1]`).
**Status:** RESOLVED 2026-05-19.
**Authoritative.** Implementations in P12 / P13 cite this doc; deviations need an explicit PR amending it.

---

## The choice

**The podcast pipeline runs on ONE designated primary Mac.** Other Macs are SSH-tunneled read-only viewers.

```
┌──────────────────────────────┐         ┌──────────────────────────────┐
│ PRIMARY MAC                  │         │ SECONDARY MAC (viewer)       │
│ (designated 2026-05-18)      │  SSH    │                              │
│                              │ ◀═════  │  $ ssh -L 8765:127.0.0.1:8765│
│  • orchestrator (Popen)      │ tunnel  │       primary-mac.local      │
│  • cost-ledger.jsonl writer  │         │  Then open                   │
│  • FastAPI service @ 8765    │         │  http://127.0.0.1:8765/ in   │
│  • Azure credentials in      │         │  local browser.              │
│    macOS Keychain            │         │                              │
│  • _learning/ substrate      │         │  Cannot mutate.              │
│  • Per-book state files      │         │  Read-only view of           │
│                              │         │  the live primary.           │
└──────────────────────────────┘         └──────────────────────────────┘
```

## What runs where

| Component | Location | Rationale |
|---|---|---|
| `orchestrate_book.py` invocations | Primary Mac only | Holds Azure creds; writes state files |
| `run_wave.py` (launchd schedule) | Primary Mac only | Same |
| Azure Doc Intelligence / Translator / Speech calls | Primary Mac only | Creds in Keychain |
| `claude -p` invocations | Primary Mac only | Operator's auth session |
| Cost ledger, heartbeat, events.jsonl | Primary Mac filesystem | Append-only locality |
| `_learning/` substrate | Primary Mac filesystem | Single writer; trainer outcomes consistent |
| FastAPI dashboard service (P8) | Primary Mac, `127.0.0.1:8765` | Localhost-only by default |
| Browser dashboard read access | Any Mac via SSH-tunneled localhost | Read-only viewer pattern |
| Mutation API (P12) | Primary Mac only | Bearer-token from Keychain; localhost-only |
| Mutation API access from secondary | NOT SUPPORTED | If a secondary needs to mutate, SSH into the primary and run the command there |

## Why primary-only

### Rejected alternative: distributed workers / multi-host orchestrator pool

**What it would look like:** Books queued centrally; secondary Macs pull jobs and run their own orchestrate_book.py. State is shared (iCloud / git / cloud storage).

**Why rejected:**
1. **State convergence is hard.** `_learning/findings.jsonl`, `cost-ledger.jsonl`, `state.json`, and `heartbeat.json` are all append-only or single-writer files. Coordinating multiple writers requires distributed locks — a multi-week engineering surface that benefits a 1-operator workflow zero.
2. **Azure credential plumbing duplicates.** Each worker would need its own Keychain entries (or shared secret). Pre-flight checks (`test_azure_connectivity.py`) become per-host.
3. **`claude -p` auth is per-account.** The Claude Code CLI authenticates to one Anthropic account at a time. Distributing workers across Macs would silently share the same rate-limit pool with poor visibility.
4. **No throughput win.** The pipeline is bottlenecked by Azure DI poll-budget (R2) and `claude -p` serial-within-book authoring, not by per-host CPU. A second Mac would idle.

### Rejected alternative: cloud-hosted orchestrator (EC2 / GCP VM)

**Why rejected:**
1. The orchestrator is a primary-author tool, not a service. Cloud-hosting adds an attack surface (credentials in the cloud) without a usage pattern justifying it.
2. macOS Keychain is the credential store; replicating it to a Linux cloud host means re-implementing secret-handling. Out of scope.
3. The dashboard is for the operator's own use. SSH-tunneled localhost is the right Mac-native pattern.

## R3 mitigation (heartbeat hostname enforcement)

The heartbeat schema (P7.1) includes a `hostname` field. The mutation API (P12) refuses any mutation on a book whose last heartbeat was written by a different host. This catches the failure mode where a secondary Mac inadvertently runs `orchestrate_book.py` while the primary is also running (state divergence). If a future user wants to migrate the primary designation to a different Mac, the procedure is documented at the bottom of this file.

## State directory location

All per-book state lives under `_workspace/<category>/<book-slug>/_system/` on the primary Mac's local filesystem. NOT iCloud (sync conflicts), NOT shared git (binary churn).

The source PDFs CAN live in iCloud (e.g., `~/Library/Mobile Documents/com~apple~CloudDocs/Books/`) since they're read-once at Phase 04-ocr-translate; the OCR'd text + all downstream artifacts are local to the primary.

## Auth model

- **Localhost-bound bearer token from macOS Keychain.** The FastAPI service binds to `127.0.0.1`, not `0.0.0.0`. The token is generated once at service-install time and stored in Keychain; rotation is a Keychain operation, not a service restart.
- **SSH-tunneled access from secondary Macs uses the operator's SSH key.** The bearer token still gates the API, but it's a single shared secret between the operator's primary + their SSH-authorized secondaries.

## Migration procedure (if the primary designation moves)

1. Stop the launchd agent on the current primary: `launchctl unload ~/Library/LaunchAgents/com.journal.podcast-w1.plist`
2. Verify no in-flight runs: `python3 scripts/podcast/orchestrator_status.py --all --json | jq '[.books[] | select(.phase_status=="running")] | length'` → must return 0.
3. Migrate Keychain entries (`infra/azure/store-keychain-keys.sh`) on the new primary.
4. Migrate `content/drafts/` directory on the new primary (`rsync -av --partial`).
5. Update `_workspace/plan/podcast-plan.yaml` `meta.primary_mac` doc reference (this file).
6. Install + load the launchd agent on the new primary.
7. Update `~/.ssh/config` on secondaries to point at the new primary's hostname.

## Implications for P12 / P13

- **P12 mutation API:** binds `127.0.0.1` only. Auth via bearer token from Keychain. Refuses mutations on books whose last heartbeat was from a different host (R3).
- **P13 SQLite cross-book index:** lives at `_workspace/podcast.db` on the primary's filesystem; gitignored. Read-only cache rebuilt from canonical JSON state.

## Cross-references

- `_workspace/plan/podcast-plan.yaml` `open_questions[Q1]` — the question this doc resolves.
- `_workspace/plan/podcast-plan.yaml` `risks[R3]` — the multi-host state-divergence risk this design mitigates.
- `_workspace/runbooks/primary-mac-activation.md` — the operator's setup record for the current primary Mac.
