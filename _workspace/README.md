# `_workspace/` — tracked planning + setup + procedures

The repo's meta zone. Plan documents, response conventions, bootstrap runbooks, operational procedures. **No runtime code, no book content.** Runtime code lives under [`scripts/`](../scripts/); book content lives under [`content/`](../content/).

## Layout

| Path | Purpose |
|---|---|
| [`plan/`](plan/) | Canonical planning surface. See [plan/README.md](plan/README.md) for the nested structure: `architecture.md` (timeless design + 13 ADRs), `refactor/` (the active 22-step roadmap), `conventions/` (response template + authoring rules), `debt/` (live F-item backlog), `operations/` (per-book ship checklist), `reader/`, `research/`, `view/`. |
| [`runbooks/`](runbooks/) | Procedures used at intervals — [publish.md](runbooks/publish.md), [watchdog.md](runbooks/watchdog.md), [e2e-book.md](runbooks/e2e-book.md), [claude-code-bootstrap-prompt.md](runbooks/claude-code-bootstrap-prompt.md), [podcast-factory.code-workspace](runbooks/podcast-factory.code-workspace). |
| [`setup/`](setup/) | One-time setup: [bootstrap.md](setup/bootstrap.md) for new Macs; [azure-stack.md](setup/azure-stack.md) for the full Azure resource reference. |
| [`proposals/`](proposals/) | One-off design proposals awaiting decision. Currently: `operator-review-ai-features.html` (AI features for the operator-review surface). |
| `audit/`, `logs/` | **Gitignored.** On-disk only — auditor outputs (`audit/`) and orchestrator runtime logs (`logs/`). Never committed; safe to delete locally. |

## Standing doctrine

- **No file versions** anywhere in this repo. The git history IS the version log. See [DR-009 in plan/architecture.md](plan/architecture.md#decision-records-adrs).
- **No root-level sprawl in `_workspace/`** — only `README.md` and a small set of typed subdirectories.
- **Single-machine model** (since 2026-05-23). The earlier multi-machine coordination model (operator files, machine-id detection, book-queue mutex) is retired. The session-starter is [`scripts/start-session.sh`](../scripts/start-session.sh).
- **Branch propagation** — `_workspace/` propagates via the standard merge flow (`<prefix>/<slug>` → `develop` → `main`). Per [DR-003](plan/architecture.md#decision-records-adrs), each piece of content runs on its own typed branch off `develop`.

## What used to be here (deleted 2026-05-26)

Folder consolidation removed 9 sprawl entries (see commit [4c92b2b](https://github.com/asifhussain60/podcast-factory/commit/4c92b2b)):

- **Tracked deletes** — `_archive/` (28 files), `audit-reports/` (3 dated reports), `chats/` (3 prompts; retired studio-* multi-machine artifacts), `kashkole-corpus/` (2,648 files / 98M rollout extracts), `lectures/` (8 files; canonical copy at `content/drafts/LECTURES/`), `tmp/` (2 one-shot files).
- **On-disk deletes** — `raw/` (743M source PDFs; originals on Drive), `scratch/` (challenger work-in-progress), `orchestrator-logs/` (empty).

Git history preserves every byte. Recover any file with `git show 4c92b2b~1:_workspace/<path>`.
