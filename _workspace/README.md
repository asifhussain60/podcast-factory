# `_workspace/` — operator workspace

The tracked execution-plan + coordination zone. Everything in here is meta —
plans, runbooks, machine coordination, archived chat dumps. No runtime code.
No book content. Runtime code lives under `scripts/`; book content lives
under `content/`.

## Layout

| Path                       | Purpose                                                                                   |
|----------------------------|-------------------------------------------------------------------------------------------|
| `plan/`                    | Canonical podcast pipeline plan (YAML + DoR + acceptance criteria + research + view) AND cross-machine coord. |
| `plan/operators/`          | Cross-machine coordination — operator files, protocol, queue, session-starter script.    |
| `plan/book-queue.md`       | Pull-on-demand work queue with claim/completion protocols.                               |
| `plan/response-conventions.md` | Shared BLUF response format across all Claude sessions on all machines.              |
| `chats/`                   | Persistent cross-machine prompts (cowork instructions, sync prompts).                    |
| `runbooks/`                | One-time bootstrap / activation procedures (e.g., new-Mac Azure setup).                  |
| `_archive/`                | Historical material kept for context. Read-only.                                         |
| `audit/`                   | (gitignored) Local-only audit snapshots and post-rerun comparison files.                 |
| `orchestrator-logs/`       | (gitignored) Local-only orchestrator stdout/stderr.                                      |

## Why operators/ sits under plan/, not at top level

Historical: the coordination protocol was authored with operator files
alongside the plan. Many cross-references hardcode `_workspace/plan/operators/`.
The *content* is cross-machine coordination, not plan content, but the *path*
is stable. The path-move to `_workspace/operators/` would touch every
reference and is not worth the churn unless we promote `_workspace/plan/`
itself.

## What "no root-level sprawl" means here

- `_workspace/` itself contains only `README.md` and a small set of
  subdirectories — no loose files at this level.
- Each subdirectory has its own `README.md` orienting its contents.

## Branch propagation

This directory propagates across branches via the standard merge flow
(book branch → develop → main):

- `_workspace/plan/podcast-plan.yaml` — canonical only on
  `feat/podcast-w1-foundation`. Other branches may carry a stale copy via
  merge but should not be edited there.
- `_workspace/plan/operators/**` — propagates to every branch. Each machine
  writes only its own operator file (per `coordination-protocol.md` §1).
- `_workspace/plan/book-queue.md` — propagates to every branch; written by
  any machine via the claim-mutex protocol on develop.
- `_workspace/plan/response-conventions.md` — Asif edits; machines read.
- `_workspace/runbooks/**` — propagates everywhere; rarely changes.
- `_workspace/_archive/**` — propagates everywhere; never changes.
- `_workspace/chats/**` — propagates everywhere; coord prompts saved here for
  later replay (e.g., onboarding a new machine).

See `plan/operators/coordination-protocol.md` §9 for the full branch policy.
