# git-hooks — what runs, when, and what it blocks

Five tracked hooks. They are **not** active in a fresh clone: `.git/hooks/` is
per-machine and untracked, so nothing here fires until they are installed.

```bash
bash scripts/install-git-hooks.sh
```

That script copies **every** file in this directory into `.git/hooks/` and makes it
executable. Idempotent — re-run it whenever a file here changes, because the copies
are copies, not symlinks, and will otherwise keep running the old version.

> A second installer, `infra/git-hooks/install.sh`, existed until 2026-08-10 and
> symlinked **only** `pre-commit`. A machine set up with it silently had no
> develop-sync hooks at all. It was deleted; `scripts/install-git-hooks.sh` is the
> one and only installer.

---

## The two jobs these hooks do

They are unrelated to each other, and conflating them is how the wrong one gets
disabled:

- **`pre-commit` is a quality gate.** It blocks a commit that would break a
  documented contract. It is allowed to fail the operation.
- **`post-commit`, `post-merge`, `post-checkout` keep localhost in step with
  `develop`.** They are advisory and can never fail the git operation they follow.

---

## pre-commit — the blocking gate

Runs on every commit and refuses the commit on any of these. Each check is scoped to
the *staged* files, so an untouched violation elsewhere in the repo does not block
unrelated work.

| Check | Blocks when |
|---|---|
| DR-009 version stamps | A staged file has `Version: <digit>` at the start of a line |
| DR-009 versioned filenames | A staged `*v[0-9]*.md` / `*v[0-9]*.yaml` outside `_archive/` |
| Ruff lint + format | Staged Python fails `ruff check` or has format drift |
| DR-005 line count | A staged `scripts/podcast/*.py` (excluding tests) exceeds its cap — see `check-dr005.py` and the `dr005-grandfather.txt` exemption list |
| AGENTS.md sync | `AGENTS.md` has drifted from `CLAUDE.md` |
| Agent-mirror parity | A canonical spec in `infra/claude-agents/` disagrees with its generated `.github/agents/` or `.codex/agents/` copy — fix with `bash scripts/podcast/sync-agent-wrappers.sh` |
| Dead doc links | A normative doc links to a path that does not exist |
| repo-surgeon probe | `scripts/repo_surgeon_probe.py` reports a P0 or P1 |
| eslint | Errors (not warnings) on staged Astro Site files |
| prettier | Format drift on staged Astro Site files — blocking, deliberately |
| Astro Site tests | `npm run test` in `plan-dashboard/` fails (~1.5s, so it runs every time) |

The Node-side checks skip themselves when `plan-dashboard/node_modules` is absent, so
a clone that has never run `npm install` can still commit.

**Bypass is `--no-verify`, and it is a Tier 2 action** — the hook says so itself on
every failure. It needs explicit operator authorization, not a judgement call.

## check-dr005.py + dr005-grandfather.txt

The line-count gate and its exemption list. Files listed in the grandfather file were
over the cap when the rule landed and are permitted to stay that way; nothing new may
join them. The list is tracked so the exemption is reviewable rather than implicit.

---

## post-commit, post-merge, post-checkout — the develop↔localhost invariant

All three call the same script, [`sync-develop.sh`](sync-develop.sh), because "did
that land on `develop`?" is one guard and not three. Each one no-ops immediately
unless the current branch is `develop`. `post-checkout` additionally ignores
single-file checkouts, which cannot move the branch.

When `develop`'s local ref moves — a commit, a pull, a merge, or `deploy_listener.sh`
sweeping branches — the script does exactly two things:

1. Regenerates the Astro Site's snapshot JSONs (`npm run snapshot`).
2. Applies the Podcast Factory Library's **local** D1 migrations.

Those are the only two things that do not self-update: everything else is a file the
dev servers already watch. **It deliberately does not start or restart either dev
server** — Vite and React Router hot-reload on their own, and a restart forced from a
git hook would fight however the server was actually launched.

**A failure here is printed and swallowed.** A snapshot regen or a migration must
never be able to block a commit.

### The rolling diff is expected, not a bug

`dashboard-snapshot.json` carries a rolling window of recent commits, so regenerating
it right after a commit produces a diff that includes that very commit. Committing
that diff produces a fresh one-behind diff, forever. Leave it uncommitted; it gets
picked up naturally with the next real work.

### Production is not covered by any of this

There is deliberately no hook watching `main`. `scripts/podcast/deploy_listener.sh`
pushes `main` and deploys the Worker as one script, so "`main` moved" and "production
was deployed" are the same event by construction. A hook that deployed on any other
reason `main` moved would bypass the local-sign-off gate.

---

## Verifying the install

```bash
ls -l .git/hooks/ | grep -E 'pre-commit|post-'   # four entries, all executable
git commit --allow-empty -m "probe"              # pre-commit runs; sync prints on develop
```
