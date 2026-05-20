# `_workspace/` — operator workspace

The tracked execution-plan + coordination zone. Everything in here is meta —
plans, runbooks, machine coordination, archived chat dumps. No runtime code.
No book content. Runtime code lives under `scripts/`; book content lives
under `content/`.

## Layout

| Path                   | Purpose                                                                                   |
|------------------------|-------------------------------------------------------------------------------------------|
| `operators/`           | Cross-machine coordination — assignment table, protocol, per-machine resume files.       |
| `plan/`                | Canonical podcast pipeline plan (YAML + DoR + acceptance criteria + research + view).    |
| `runbooks/`            | One-time bootstrap / activation procedures (e.g., new-Mac Azure setup).                  |
| `_archive/`            | Historical material kept for context. Read-only.                                         |

## What "no root-level sprawl" means here

- `_workspace/` itself contains only `README.md` and four subdirectories — no
  loose files at this level.
- Each subdirectory has its own `README.md` orienting its contents.
- `plan/` retains its existing flat layout because it is referenced by dozens
  of scripts and docs that hardcode paths; refactoring it has high
  blast-radius and is tracked as a separate task. Its `README.md` indexes the
  loose files.

## Branch propagation

This directory is mostly **branch-scoped**:

- `_workspace/plan/podcast-plan.yaml` — canonical only on
  `feat/podcast-w1-foundation`. Other branches may have a stale copy via
  merge but should not be edited there.
- `_workspace/operators/**` — propagates to every branch (read-write on
  `develop` + book branches per `operators/coordination-protocol.md`).
- `_workspace/runbooks/**` — propagates everywhere; rarely changes.
- `_workspace/_archive/**` — propagates everywhere; never changes.

See `operators/coordination-protocol.md` §9 for the full branch policy.
