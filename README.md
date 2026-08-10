# podcast-factory

A pipeline that turns scholarly books — most of them Arabic — into two finished
deliverables: a **NotebookLM-driven podcast series** and a **printed reading edition**.
Source PDF in, audio episodes and a typeset PDF out, with human review gates at the
points where judgment actually matters.

The repo also contains the **Podcast Factory Astro Site** (directory `plan-dashboard/`),
the web surface used to review, edit, and compose the work in flight.

## Where things live

| Path | What it holds |
|---|---|
| `content/<Bucket>/<slug>/` | Every per-book artifact. `<Bucket>` is `Islamic`, `Technical`, `Fiction`, or `Guides`. Draft vs published is a **status field**, not a folder |
| `scripts/podcast/` | The pipeline — phases, authoring, validation, publishing |
| `plan-dashboard/` | The Astro site: library, studio, book composer, reader |
| `infra/claude-agents/` | Canonical agent specs. Every other copy is generated — never hand-edit one |
| `skills-staging/` | Skills installed into the Claude runtime by `make install-skills` |
| `_workspace/` | Planning and review surface (working memory, not product) |
| `_learning/` | Findings ledger and fixtures the quality gates learn from |
| `docs/` | Standards, references, runbooks, assessments, postmortems |

## Getting started

```bash
source .venv/bin/activate
bash scripts/start-session.sh
```

The session script fetches, puts you on `develop`, and prints the books in flight
along with the next-action commands for each.

## Verifying a change

```bash
make lint                                    # ruff + format + the file-size gate
python3 -m pytest -q                         # all three test trees
python3 scripts/podcast/_boundary_check.py   # this repo never writes to the sibling journal repo
cd plan-dashboard && npm run lint && npm run check && npm test && npm run lint:views
```

Git hooks enforce a subset of these on every commit — install them once with
`bash scripts/install-git-hooks.sh`. What each hook does:
[infra/git-hooks/README.md](infra/git-hooks/README.md).

## Read next

- **[CLAUDE.md](CLAUDE.md)** — how to work in this repo: branch policy, authorization
  tiers, standing operator rules. **The authority.** This README deliberately does not
  restate any of it.
- **[framework.md](framework.md)** — the pipeline framework spec.
- **[docs/standards/](docs/standards/)** — the quality standards the gates enforce.
- **[_workspace/plan/architecture.md](_workspace/plan/architecture.md)** — architecture
  and the decision records behind it.

## A note on the `_` prefix

It means three different things depending on where you see it, and all three are
load-bearing:

- **`_workspace/`, `_learning/`** at the top level — working surface, not the product.
- **`_shared/`, `_archive/`, `_system/`** inside `content/` — plumbing, not a content
  item. The path resolver skips `_`-prefixed names to tell books from machinery.
- **`_name.py`** in `scripts/podcast/` — a private helper, not a command you run.
